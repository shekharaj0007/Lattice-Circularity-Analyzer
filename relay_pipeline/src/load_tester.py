"""Load testing framework for the pipeline."""
import time
import threading
from typing import List, Dict, Callable
from queue import Queue
import pandas as pd
from datetime import datetime


class LoadScenario:
    """Define a load testing scenario."""
    
    @staticmethod
    def steady_load(duration_seconds: int = 60, rate_per_minute: int = 10):
        """Steady load: constant request rate."""
        return {
            "name": "Steady Load",
            "duration": duration_seconds,
            "rate": rate_per_minute,
            "pattern": "steady",
            "description": f"{rate_per_minute} requests/min for {duration_seconds}s"
        }
    
    @staticmethod
    def burst_load(num_bursts: int = 3, requests_per_burst: int = 10, 
                   burst_interval: int = 30):
        """Burst load: periodic spikes of requests."""
        return {
            "name": "Burst Load",
            "num_bursts": num_bursts,
            "requests_per_burst": requests_per_burst,
            "burst_interval": burst_interval,
            "pattern": "burst",
            "description": f"{num_bursts} bursts of {requests_per_burst} requests, {burst_interval}s apart"
        }
    
    @staticmethod
    def sustained_overload(duration_seconds: int = 120, rate_per_minute: int = 40):
        """Sustained overload: rate above capacity."""
        return {
            "name": "Sustained Overload",
            "duration": duration_seconds,
            "rate": rate_per_minute,
            "pattern": "overload",
            "description": f"{rate_per_minute} requests/min (above limit) for {duration_seconds}s"
        }
    
    @staticmethod
    def ramp_up(duration_seconds: int = 60, start_rate: int = 5, end_rate: int = 30):
        """Ramp up: gradually increasing load."""
        return {
            "name": "Ramp Up",
            "duration": duration_seconds,
            "start_rate": start_rate,
            "end_rate": end_rate,
            "pattern": "ramp",
            "description": f"Ramp from {start_rate} to {end_rate} requests/min over {duration_seconds}s"
        }


class LoadTester:
    """Execute load tests on the pipeline."""
    
    def __init__(self, pipeline_factory: Callable, questions: List[Dict]):
        """
        Args:
            pipeline_factory: Function that creates a new pipeline instance
            questions: List of test questions
        """
        self.pipeline_factory = pipeline_factory
        self.questions = questions
        self.results = []
        self.errors = []
    
    def run_scenario(self, scenario: Dict) -> Dict:
        """Run a load testing scenario."""
        print(f"\n{'='*60}")
        print(f"Running: {scenario['name']}")
        print(f"Pattern: {scenario['description']}")
        print(f"{'='*60}\n")
        
        pattern = scenario["pattern"]
        
        if pattern == "steady":
            return self._run_steady(scenario)
        elif pattern == "burst":
            return self._run_burst(scenario)
        elif pattern == "overload":
            return self._run_overload(scenario)
        elif pattern == "ramp":
            return self._run_ramp(scenario)
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
    
    def _run_steady(self, scenario: Dict) -> Dict:
        """Run steady load scenario."""
        pipeline = self.pipeline_factory()
        start_time = time.time()
        end_time = start_time + scenario["duration"]
        
        request_count = 0
        interval = 60.0 / scenario["rate"]  # seconds between requests
        
        results = []
        
        while time.time() < end_time:
            question = self.questions[request_count % len(self.questions)]
            
            result = pipeline.process_query(question["question"], query_id=request_count)
            result["scenario"] = scenario["name"]
            result["timestamp"] = time.time() - start_time
            results.append(result)
            
            request_count += 1
            
            # Wait for next request
            next_request_time = start_time + (request_count * interval)
            sleep_time = next_request_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        return self._summarize_results(scenario, results, pipeline)
    
    def _run_burst(self, scenario: Dict) -> Dict:
        """Run burst load scenario."""
        pipeline = self.pipeline_factory()
        start_time = time.time()
        
        results = []
        request_count = 0
        
        for burst_num in range(scenario["num_bursts"]):
            print(f"  Burst {burst_num + 1}/{scenario['num_bursts']}...")
            
            # Send burst of requests
            burst_results = []
            for i in range(scenario["requests_per_burst"]):
                question = self.questions[request_count % len(self.questions)]
                
                result = pipeline.process_query(question["question"], query_id=request_count)
                result["scenario"] = scenario["name"]
                result["timestamp"] = time.time() - start_time
                result["burst_num"] = burst_num
                burst_results.append(result)
                
                request_count += 1
            
            results.extend(burst_results)
            
            # Wait for next burst
            if burst_num < scenario["num_bursts"] - 1:
                time.sleep(scenario["burst_interval"])
        
        return self._summarize_results(scenario, results, pipeline)
    
    def _run_overload(self, scenario: Dict) -> Dict:
        """Run sustained overload scenario."""
        # Similar to steady but at higher rate
        return self._run_steady(scenario)
    
    def _run_ramp(self, scenario: Dict) -> Dict:
        """Run ramp-up scenario."""
        pipeline = self.pipeline_factory()
        start_time = time.time()
        end_time = start_time + scenario["duration"]
        
        results = []
        request_count = 0
        
        start_rate = scenario["start_rate"]
        end_rate = scenario["end_rate"]
        duration = scenario["duration"]
        
        while time.time() < end_time:
            elapsed = time.time() - start_time
            progress = elapsed / duration
            
            # Current rate interpolated linearly
            current_rate = start_rate + (end_rate - start_rate) * progress
            interval = 60.0 / current_rate
            
            question = self.questions[request_count % len(self.questions)]
            
            result = pipeline.process_query(question["question"], query_id=request_count)
            result["scenario"] = scenario["name"]
            result["timestamp"] = elapsed
            result["current_rate"] = current_rate
            results.append(result)
            
            request_count += 1
            
            # Wait for next request
            next_request_time = time.time() + interval
            sleep_time = next_request_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        return self._summarize_results(scenario, results, pipeline)
    
    def _summarize_results(self, scenario: Dict, results: List[Dict], 
                          pipeline) -> Dict:
        """Summarize scenario results."""
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        budget_refused = [r for r in failed if "budget" in r.get("error", "").lower()]
        verified = [r for r in successful if r.get("verified", False)]
        
        total_time = results[-1]["timestamp"] if results else 0
        
        summary = {
            "scenario": scenario["name"],
            "pattern": scenario.get("pattern"),
            "total_requests": len(results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "budget_refusals": len(budget_refused),
            "verified_answers": len(verified),
            "success_rate": len(successful) / len(results) if results else 0,
            "verification_rate": len(verified) / len(successful) if successful else 0,
            "total_duration": total_time,
            "throughput": len(results) / total_time if total_time > 0 else 0,
            "avg_latency": sum(r.get("timings", {}).get("total", 0) for r in successful) / len(successful) if successful else 0,
            "pipeline_stats": pipeline.get_stats(),
            "results": results
        }
        
        print(f"\n{scenario['name']} Results:")
        print(f"  Requests: {len(results)} ({len(successful)} successful, {len(failed)} failed)")
        print(f"  Budget refusals: {len(budget_refused)}")
        print(f"  Success rate: {summary['success_rate']*100:.1f}%")
        print(f"  Verification rate: {summary['verification_rate']*100:.1f}%")
        print(f"  Avg latency: {summary['avg_latency']:.2f}s")
        print(f"  Throughput: {summary['throughput']:.2f} req/s")
        
        return summary
    
    def save_results_csv(self, scenario_results: List[Dict], filepath: str):
        """Save detailed results to CSV."""
        rows = []
        
        for scenario_result in scenario_results:
            for result in scenario_result["results"]:
                row = {
                    "scenario": scenario_result["scenario"],
                    "query_id": result.get("query_id", -1),
                    "timestamp": result.get("timestamp", 0),
                    "success": result.get("success", False),
                    "verified": result.get("verified", False),
                    "total_latency": result.get("timings", {}).get("total", 0),
                    "intent_latency": result.get("timings", {}).get("intent", 0),
                    "retrieval_latency": result.get("timings", {}).get("retrieval", 0),
                    "generation_latency": result.get("timings", {}).get("generation", 0),
                    "verification_latency": result.get("timings", {}).get("verification", 0),
                    "tokens_used": result.get("tokens_used", 0),
                    "retry_needed": result.get("retry_needed", False),
                    "error": result.get("error", ""),
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        print(f"\n✓ Saved detailed results to: {filepath}")
        
        return df


if __name__ == "__main__":
    print("Load testing scenarios available:")
    
    scenarios = [
        LoadScenario.steady_load(),
        LoadScenario.burst_load(),
        LoadScenario.sustained_overload(),
        LoadScenario.ramp_up()
    ]
    
    for s in scenarios:
        print(f"  - {s['name']}: {s['description']}")
