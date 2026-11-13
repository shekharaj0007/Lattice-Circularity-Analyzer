"""Groq API client with instrumentation."""
import os
import time
from typing import Dict, List, Optional
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()


class InstrumentedGroqClient:
    """Groq client with detailed instrumentation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
        
        # Instrumentation
        self.call_count = 0
        self.total_tokens = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_latency = 0.0
        self.latencies = []
        self.errors = []
        self.call_log = []
    
    def chat_completion(self, messages: List[Dict], 
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       stream: bool = False) -> Dict:
        """
        Make a chat completion request with instrumentation.
        
        Returns dict with:
        - content: response text
        - usage: token usage
        - latency: request latency
        - success: whether request succeeded
        - error: error message if failed
        """
        start_time = time.time()
        self.call_count += 1
        
        call_record = {
            "call_id": self.call_count,
            "timestamp": start_time,
            "model": self.model,
            "message_count": len(messages),
            "stream": stream
        }
        
        try:
            if stream:
                result = self._streaming_completion(messages, temperature, max_tokens, start_time, call_record)
            else:
                result = self._standard_completion(messages, temperature, max_tokens, start_time, call_record)
            
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)
            
            self.errors.append({
                "call_id": self.call_count,
                "timestamp": start_time,
                "error": error_msg,
                "latency": latency
            })
            
            call_record.update({
                "success": False,
                "error": error_msg,
                "latency": latency
            })
            self.call_log.append(call_record)
            
            return {
                "content": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "latency": latency,
                "success": False,
                "error": error_msg
            }
    
    def _standard_completion(self, messages, temperature, max_tokens, start_time, call_record):
        """Non-streaming completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        latency = time.time() - start_time
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        content = response.choices[0].message.content
        
        # Update metrics
        self.total_tokens += usage["total_tokens"]
        self.total_prompt_tokens += usage["prompt_tokens"]
        self.total_completion_tokens += usage["completion_tokens"]
        self.total_latency += latency
        self.latencies.append(latency)
        
        call_record.update({
            "success": True,
            "latency": latency,
            "usage": usage,
            "response_length": len(content)
        })
        self.call_log.append(call_record)
        
        return {
            "content": content,
            "usage": usage,
            "latency": latency,
            "success": True
        }
    
    def _streaming_completion(self, messages, temperature, max_tokens, start_time, call_record):
        """Streaming completion with token timing."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        content = ""
        first_token_time = None
        token_times = []
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token_time = time.time()
                if first_token_time is None:
                    first_token_time = token_time
                    call_record["time_to_first_token"] = token_time - start_time
                else:
                    token_times.append(token_time - (token_times[-1] if token_times else first_token_time))
                
                content += chunk.choices[0].delta.content
        
        latency = time.time() - start_time
        
        # Estimate tokens (rough approximation)
        estimated_tokens = len(content.split()) * 1.3
        usage = {
            "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
            "completion_tokens": int(estimated_tokens),
            "total_tokens": int(sum(len(m.get("content", "").split()) for m in messages) + estimated_tokens)
        }
        
        self.total_tokens += usage["total_tokens"]
        self.total_latency += latency
        self.latencies.append(latency)
        
        call_record.update({
            "success": True,
            "latency": latency,
            "usage": usage,
            "response_length": len(content),
            "token_count": len(token_times),
            "avg_token_latency": sum(token_times) / len(token_times) if token_times else 0
        })
        self.call_log.append(call_record)
        
        return {
            "content": content,
            "usage": usage,
            "latency": latency,
            "success": True,
            "ttft": call_record.get("time_to_first_token", 0)
        }
    
    def get_stats(self) -> Dict:
        """Get client statistics."""
        import numpy as np
        
        latencies_array = np.array(self.latencies) if self.latencies else np.array([0])
        
        return {
            "total_calls": self.call_count,
            "successful_calls": self.call_count - len(self.errors),
            "failed_calls": len(self.errors),
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_latency": self.total_latency,
            "avg_latency": self.total_latency / self.call_count if self.call_count > 0 else 0,
            "min_latency": float(np.min(latencies_array)),
            "max_latency": float(np.max(latencies_array)),
            "p50_latency": float(np.percentile(latencies_array, 50)),
            "p95_latency": float(np.percentile(latencies_array, 95)),
            "p99_latency": float(np.percentile(latencies_array, 99)),
            "error_rate": len(self.errors) / self.call_count if self.call_count > 0 else 0
        }
    
    def save_call_log(self, filepath: str):
        """Save detailed call log."""
        with open(filepath, 'w') as f:
            json.dump({
                "stats": self.get_stats(),
                "calls": self.call_log,
                "errors": self.errors
            }, f, indent=2)


if __name__ == "__main__":
    # Test client
    client = InstrumentedGroqClient()
    
    result = client.chat_completion([
        {"role": "user", "content": "What is a transformer model?"}
    ])
    
    print(f"Success: {result['success']}")
    print(f"Latency: {result['latency']:.3f}s")
    print(f"Tokens: {result['usage']['total_tokens']}")
    print(f"Response: {result['content'][:100]}...")
    print("\nStats:", client.get_stats())
