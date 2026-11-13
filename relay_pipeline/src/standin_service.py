"""Stand-in service that simulates Groq API behavior."""
import time
import random
import numpy as np
from typing import Dict, List, Optional
import threading
from collections import deque


class StandinGroqService:
    """Simulates Groq API with realistic latency, rate limits, and failures."""
    
    def __init__(self,
                 rpm_limit: int = 30,
                 tpm_limit: int = 14400,
                 latency_distribution: Dict[str, float] = None,
                 failure_rate: float = 0.02,
                 load_degradation: bool = True):
        """
        Initialize stand-in service.
        
        Args:
            rpm_limit: Requests per minute limit
            tpm_limit: Tokens per minute limit
            latency_distribution: {"mean": ms, "std": ms, "p95": ms, "p99": ms}
            failure_rate: Probability of request failure
            load_degradation: Whether latency increases with load
        """
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.failure_rate = failure_rate
        self.load_degradation = load_degradation
        
        # Default latency distribution (calibrated from real measurements)
        self.latency_dist = latency_distribution or {
            "mean": 850,  # ms
            "std": 250,   # ms
            "min": 300,
            "max": 3000
        }
        
        # Rate limiting
        self.request_times = deque()
        self.token_usage = deque()
        self.lock = threading.Lock()
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limit_errors = 0
        self.latencies = []
    
    def chat_completion(self, messages: List[Dict],
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       stream: bool = False) -> Dict:
        """
        Simulate a chat completion request.
        
        Returns same format as real Groq client.
        """
        start_time = time.time()
        self.total_requests += 1
        
        # Estimate tokens
        prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 1.3
        completion_tokens = random.randint(50, min(max_tokens, 300))
        total_tokens = int(prompt_tokens + completion_tokens)
        
        # Check rate limits
        with self.lock:
            rate_limit_error = self._check_rate_limits(total_tokens)
        
        if rate_limit_error:
            self.rate_limit_errors += 1
            self.failed_requests += 1
            return {
                "content": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "latency": time.time() - start_time,
                "success": False,
                "error": rate_limit_error
            }
        
        # Simulate random failures
        if random.random() < self.failure_rate:
            self.failed_requests += 1
            error_types = [
                "Rate limit exceeded",
                "Service temporarily unavailable",
                "Timeout error",
                "Invalid request"
            ]
            return {
                "content": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "latency": time.time() - start_time,
                "success": False,
                "error": random.choice(error_types)
            }
        
        # Simulate latency
        latency = self._simulate_latency()
        
        # Simulate streaming if requested
        if stream:
            latency = self._simulate_streaming(completion_tokens)
        else:
            time.sleep(latency / 1000)  # Convert ms to seconds
        
        # Generate mock response
        content = self._generate_mock_response(messages, completion_tokens)
        
        actual_latency = time.time() - start_time
        
        # Record metrics
        with self.lock:
            self.request_times.append(time.time())
            self.token_usage.append((time.time(), total_tokens))
            self.latencies.append(actual_latency * 1000)  # ms
        
        self.successful_requests += 1
        
        return {
            "content": content,
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "latency": actual_latency,
            "success": True
        }
    
    def _check_rate_limits(self, tokens: int) -> Optional[str]:
        """Check if rate limits would be exceeded."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        while self.token_usage and self.token_usage[0][0] < minute_ago:
            self.token_usage.popleft()
        
        # Check RPM
        if len(self.request_times) >= self.rpm_limit:
            return f"Rate limit exceeded: {self.rpm_limit} RPM"
        
        # Check TPM
        recent_tokens = sum(tok for _, tok in self.token_usage)
        if recent_tokens + tokens > self.tpm_limit:
            return f"Token limit exceeded: {self.tpm_limit} TPM"
        
        return None
    
    def _simulate_latency(self) -> float:
        """Simulate realistic latency in milliseconds."""
        # Base latency from distribution
        latency = np.random.normal(
            self.latency_dist["mean"],
            self.latency_dist["std"]
        )
        
        # Clip to reasonable bounds
        latency = np.clip(
            latency,
            self.latency_dist["min"],
            self.latency_dist["max"]
        )
        
        # Apply load degradation
        if self.load_degradation:
            current_load = len(self.request_times) / self.rpm_limit
            if current_load > 0.7:
                # 20-50% slowdown at high load
                degradation = 1.0 + (current_load - 0.7) * random.uniform(0.2, 0.5)
                latency *= degradation
        
        return latency
    
    def _simulate_streaming(self, num_tokens: int) -> float:
        """Simulate streaming with token-by-token delays."""
        # Time to first token
        ttft = random.uniform(200, 500)  # ms
        time.sleep(ttft / 1000)
        
        # Token generation with variance
        token_times = []
        for _ in range(num_tokens):
            token_latency = random.uniform(10, 50)  # ms per token
            time.sleep(token_latency / 1000)
            token_times.append(token_latency)
        
        return ttft + sum(token_times)
    
    def _generate_mock_response(self, messages: List[Dict], length: int) -> str:
        """Generate a mock response."""
        templates = [
            "Based on the context, {topic}. This is important because {reason}. Additionally, {detail}.",
            "The answer to this question involves {topic}. Research shows that {evidence}. In conclusion, {summary}.",
            "To understand this, we need to consider {aspect1} and {aspect2}. The key insight is {insight}.",
        ]
        
        # Try to extract topic from last message
        last_msg = messages[-1].get("content", "")
        words = last_msg.split()
        topic = " ".join(words[:5]) if len(words) > 5 else "the topic"
        
        response = random.choice(templates).format(
            topic=topic,
            reason="it demonstrates key principles",
            detail="there are several factors to consider",
            evidence="multiple studies support this view",
            summary="the evidence is compelling",
            aspect1="the theoretical framework",
            aspect2="practical applications",
            insight="these elements work together"
        )
        
        # Pad to approximate length
        words_needed = length - len(response.split())
        if words_needed > 0:
            padding = " Furthermore, this relates to additional considerations." * (words_needed // 6 + 1)
            response += padding[:words_needed * 5]
        
        return response[:length * 5]  # Rough char count
    
    def calibrate(self, real_measurements: Dict):
        """Calibrate stand-in with real measurements."""
        if "latency_dist" in real_measurements:
            self.latency_dist = real_measurements["latency_dist"]
        
        if "failure_rate" in real_measurements:
            self.failure_rate = real_measurements["failure_rate"]
        
        if "rpm_limit" in real_measurements:
            self.rpm_limit = real_measurements["rpm_limit"]
        
        if "tpm_limit" in real_measurements:
            self.tpm_limit = real_measurements["tpm_limit"]
        
        print(f"✓ Stand-in calibrated with real measurements")
        print(f"  Latency: {self.latency_dist['mean']:.0f}ms (±{self.latency_dist['std']:.0f}ms)")
        print(f"  Failure rate: {self.failure_rate*100:.2f}%")
        print(f"  Limits: {self.rpm_limit} RPM, {self.tpm_limit} TPM")
    
    def get_stats(self) -> Dict:
        """Get service statistics."""
        import numpy as np
        
        latencies_array = np.array(self.latencies) if self.latencies else np.array([0])
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limit_errors": self.rate_limit_errors,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "avg_latency_ms": float(np.mean(latencies_array)),
            "p50_latency_ms": float(np.percentile(latencies_array, 50)),
            "p95_latency_ms": float(np.percentile(latencies_array, 95)),
            "p99_latency_ms": float(np.percentile(latencies_array, 99)),
        }


if __name__ == "__main__":
    # Test stand-in
    service = StandinGroqService()
    
    print("Testing stand-in service...")
    for i in range(10):
        result = service.chat_completion([
            {"role": "user", "content": "Test question"}
        ])
        print(f"Request {i+1}: {result['success']}, {result['latency']*1000:.0f}ms, {result['usage']['total_tokens']} tokens")
    
    print("\nStats:", service.get_stats())
