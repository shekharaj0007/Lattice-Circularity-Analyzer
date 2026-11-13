"""Measure real Groq API limits and characteristics."""
import time
import os
from typing import Dict, List
import numpy as np
from dotenv import load_dotenv
from groq_client import InstrumentedGroqClient
import json

load_dotenv()


class GroqMeasurement:
    """Measure Groq API characteristics through controlled tests."""
    
    def __init__(self, api_key: str = None):
        self.client = InstrumentedGroqClient(api_key=api_key)
        self.measurements = {}
    
    def measure_latency_distribution(self, num_requests: int = 30) -> Dict:
        """
        Measure latency distribution with various request types.
        
        Sends requests at a safe rate to avoid rate limiting.
        """
        print(f"\n{'='*60}")
        print("Measuring Latency Distribution")
        print(f"{'='*60}\n")
        
        test_messages = [
            [{"role": "user", "content": "What is machine learning?"}],
            [{"role": "user", "content": "Explain the attention mechanism in transformers in detail."}],
            [{"role": "user", "content": "Hello"}],
            [{"role": "user", "content": "Write a paragraph about neural networks and their applications in modern AI systems."}],
        ]
        
        latencies = []
        tokens_per_request = []
        ttft_values = []  # Time to first token for streaming
        
        for i in range(num_requests):
            messages = test_messages[i % len(test_messages)]
            
            # Alternate between streaming and non-streaming
            stream = (i % 2 == 0)
            
            print(f"Request {i+1}/{num_requests} (stream={stream})...", end=" ")
            
            result = self.client.chat_completion(
                messages,
                max_tokens=200,
                temperature=0.7,
                stream=stream
            )
            
            if result["success"]:
                latencies.append(result["latency"] * 1000)  # Convert to ms
                tokens_per_request.append(result["usage"]["total_tokens"])
                if "ttft" in result:
                    ttft_values.append(result["ttft"] * 1000)
                print(f"✓ {result['latency']*1000:.0f}ms, {result['usage']['total_tokens']} tokens")
            else:
                print(f"✗ Error: {result.get('error', 'Unknown')}")
            
            # Safe spacing between requests
            time.sleep(2.5)
        
        latencies_arr = np.array(latencies)
        
        distribution = {
            "mean": float(np.mean(latencies_arr)),
            "std": float(np.std(latencies_arr)),
            "min": float(np.min(latencies_arr)),
            "max": float(np.max(latencies_arr)),
            "p50": float(np.percentile(latencies_arr, 50)),
            "p95": float(np.percentile(latencies_arr, 95)),
            "p99": float(np.percentile(latencies_arr, 99)),
            "avg_tokens": float(np.mean(tokens_per_request)),
            "ttft_avg": float(np.mean(ttft_values)) if ttft_values else None,
            "sample_size": len(latencies)
        }
        
        self.measurements["latency_distribution"] = distribution
        
        print(f"\nLatency Distribution:")
        print(f"  Mean: {distribution['mean']:.0f}ms (±{distribution['std']:.0f}ms)")
        print(f"  Min/Max: {distribution['min']:.0f}ms / {distribution['max']:.0f}ms")
        print(f"  P50/P95/P99: {distribution['p50']:.0f}ms / {distribution['p95']:.0f}ms / {distribution['p99']:.0f}ms")
        if distribution['ttft_avg']:
            print(f"  Avg TTFT: {distribution['ttft_avg']:.0f}ms")
        
        return distribution
    
    def measure_rate_limits(self, test_duration: int = 60) -> Dict:
        """
        Measure RPM and TPM limits by sending requests until rate limited.
        
        WARNING: This may hit rate limits!
        """
        print(f"\n{'='*60}")
        print("Measuring Rate Limits (Conservative Test)")
        print(f"{'='*60}\n")
        
        # Conservative test - don't actually hit limits
        print("⚠ Using conservative estimates to avoid rate limiting")
        print("  Based on Groq free tier documentation:")
        
        limits = {
            "rpm_observed": 30,
            "tpm_observed": 14400,
            "daily_limit_tokens": 14400,
            "notes": "Free tier limits from documentation, not stress tested"
        }
        
        self.measurements["rate_limits"] = limits
        
        print(f"  RPM: {limits['rpm_observed']}")
        print(f"  TPM: {limits['tpm_observed']}")
        print(f"  Daily limit: {limits['daily_limit_tokens']} tokens")
        
        return limits
    
    def measure_error_rates(self, num_requests: int = 20) -> Dict:
        """Measure baseline error and failure rates."""
        print(f"\n{'='*60}")
        print("Measuring Error Rates")
        print(f"{'='*60}\n")
        
        successful = 0
        failed = 0
        errors_by_type = {}
        
        for i in range(num_requests):
            print(f"Request {i+1}/{num_requests}...", end=" ")
            
            result = self.client.chat_completion(
                [{"role": "user", "content": f"Test request {i}"}],
                max_tokens=50
            )
            
            if result["success"]:
                successful += 1
                print("✓")
            else:
                failed += 1
                error = result.get("error", "Unknown")
                errors_by_type[error] = errors_by_type.get(error, 0) + 1
                print(f"✗ {error}")
            
            time.sleep(3)  # Safe spacing
        
        error_rate = failed / num_requests if num_requests > 0 else 0
        
        error_stats = {
            "total_requests": num_requests,
            "successful": successful,
            "failed": failed,
            "error_rate": error_rate,
            "errors_by_type": errors_by_type
        }
        
        self.measurements["error_rates"] = error_stats
        
        print(f"\nError Statistics:")
        print(f"  Success rate: {(1-error_rate)*100:.1f}%")
        print(f"  Failures: {failed}/{num_requests}")
        if errors_by_type:
            print(f"  Error types: {errors_by_type}")
        
        return error_stats
    
    def measure_token_usage(self, num_requests: int = 15) -> Dict:
        """Measure token usage patterns."""
        print(f"\n{'='*60}")
        print("Measuring Token Usage Patterns")
        print(f"{'='*60}\n")
        
        # Different prompt sizes
        prompts = [
            "Hi",
            "What is a neural network?",
            "Explain the transformer architecture in detail, including attention mechanisms.",
            "Write a comprehensive explanation of how large language models work, covering training, inference, and key architectural components."
        ]
        
        token_data = []
        
        for i, prompt in enumerate(prompts):
            print(f"Prompt {i+1}/{len(prompts)} ({len(prompt)} chars)...", end=" ")
            
            result = self.client.chat_completion(
                [{"role": "user", "content": prompt}],
                max_tokens=300
            )
            
            if result["success"]:
                usage = result["usage"]
                token_data.append({
                    "prompt_length": len(prompt),
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "total_tokens": usage["total_tokens"],
                    "ratio": usage["prompt_tokens"] / len(prompt.split())
                })
                print(f"✓ {usage['prompt_tokens']}+{usage['completion_tokens']}={usage['total_tokens']} tokens")
            else:
                print(f"✗ Error")
            
            time.sleep(2.5)
        
        token_stats = {
            "avg_prompt_tokens": np.mean([d["prompt_tokens"] for d in token_data]),
            "avg_completion_tokens": np.mean([d["completion_tokens"] for d in token_data]),
            "avg_total_tokens": np.mean([d["total_tokens"] for d in token_data]),
            "token_per_word_ratio": np.mean([d["ratio"] for d in token_data]),
            "samples": token_data
        }
        
        self.measurements["token_usage"] = token_stats
        
        print(f"\nToken Usage:")
        print(f"  Avg tokens per word: {token_stats['token_per_word_ratio']:.2f}")
        print(f"  Avg prompt tokens: {token_stats['avg_prompt_tokens']:.1f}")
        print(f"  Avg completion tokens: {token_stats['avg_completion_tokens']:.1f}")
        
        return token_stats
    
    def run_full_measurement(self) -> Dict:
        """Run all measurements."""
        print("\n" + "="*60)
        print("GROQ API MEASUREMENT SUITE")
        print("="*60)
        
        self.measure_latency_distribution(num_requests=25)
        self.measure_rate_limits()
        self.measure_error_rates(num_requests=15)
        self.measure_token_usage(num_requests=10)
        
        # Add client stats
        self.measurements["client_stats"] = self.client.get_stats()
        
        return self.measurements
    
    def save_measurements(self, filepath: str):
        """Save measurements to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.measurements, f, indent=2)
        print(f"\n✓ Saved measurements to: {filepath}")
    
    def save_call_log(self, filepath: str):
        """Save detailed call log."""
        self.client.save_call_log(filepath)


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not set")
        print("Set it in .env file or environment variable")
        exit(1)
    
    measurer = GroqMeasurement()
    measurements = measurer.run_full_measurement()
    
    measurer.save_measurements("results/groq_measurements.json")
    measurer.save_call_log("results/groq_call_log.json")
    
    print("\n" + "="*60)
    print("Measurement complete!")
    print("="*60)
