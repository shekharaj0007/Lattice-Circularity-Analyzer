"""Main 4-stage RAG pipeline with instrumentation."""
import time
from typing import Dict, List, Optional
import json
from .groq_client import InstrumentedGroqClient
from .embeddings import EmbeddingEngine
from .rate_limiter import RateLimiter, TokenBudgetTracker


class Pipeline:
    """4-stage pipeline: Intent → Retrieval → Generation → Verification."""
    
    def __init__(self, 
                 groq_client: InstrumentedGroqClient,
                 embedding_engine: EmbeddingEngine,
                 rate_limiter: RateLimiter,
                 budget_tracker: TokenBudgetTracker,
                 chunks: List[Dict],
                 top_k: int = 5,
                 rerank: bool = False,
                 max_retries: int = 1):
        self.groq = groq_client
        self.embeddings = embedding_engine
        self.rate_limiter = rate_limiter
        self.budget_tracker = budget_tracker
        self.chunks = chunks
        self.top_k = top_k
        self.rerank = rerank
        self.max_retries = max_retries
        
        # Pipeline metrics
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.budget_refusals = 0
        self.retry_count = 0
        self.stage_timings = {
            "intent": [],
            "retrieval": [],
            "generation": [],
            "verification": []
        }
        self.query_log = []
    
    def process_query(self, query: str, query_id: Optional[int] = None) -> Dict:
        """
        Process a query through all pipeline stages.
        
        Returns:
        - success: bool
        - answer: str
        - context: retrieved chunks
        - verified: bool
        - retry_needed: bool
        - timings: stage timings
        - tokens_used: total tokens
        """
        self.total_queries += 1
        if query_id is None:
            query_id = self.total_queries
        
        start_time = time.time()
        
        log_entry = {
            "query_id": query_id,
            "query": query,
            "timestamp": start_time,
            "stages": {}
        }
        
        try:
            # Check budget before starting
            can_proceed, budget_msg = self.budget_tracker.can_proceed(estimated_tokens=500)
            if not can_proceed:
                self.budget_refusals += 1
                self.failed_queries += 1
                return {
                    "success": False,
                    "error": "Budget limit exceeded",
                    "budget_message": budget_msg,
                    "query_id": query_id
                }
            
            # Stage 1: Intent Classification
            intent_result = self._stage_intent(query)
            log_entry["stages"]["intent"] = intent_result
            
            if not intent_result["success"]:
                self.failed_queries += 1
                return {
                    "success": False,
                    "error": "Intent classification failed",
                    "query_id": query_id
                }
            
            # Stage 2: Retrieval
            retrieval_result = self._stage_retrieval(query, intent_result["intent_type"])
            log_entry["stages"]["retrieval"] = retrieval_result
            
            # Stage 3: Generation
            generation_result = self._stage_generation(query, retrieval_result["context"])
            log_entry["stages"]["generation"] = generation_result
            
            if not generation_result["success"]:
                self.failed_queries += 1
                return {
                    "success": False,
                    "error": "Generation failed",
                    "query_id": query_id
                }
            
            # Stage 4: Verification
            verification_result = self._stage_verification(
                query, 
                generation_result["answer"],
                retrieval_result["context"]
            )
            log_entry["stages"]["verification"] = verification_result
            
            # Retry logic
            if not verification_result["verified"] and self.max_retries > 0:
                self.retry_count += 1
                retry_result = self._retry_generation(
                    query,
                    retrieval_result["context"],
                    generation_result["answer"],
                    verification_result["issues"]
                )
                log_entry["stages"]["retry"] = retry_result
                
                if retry_result["success"]:
                    generation_result = retry_result
                    # Re-verify
                    verification_result = self._stage_verification(
                        query,
                        retry_result["answer"],
                        retrieval_result["context"]
                    )
                    log_entry["stages"]["verification_retry"] = verification_result
            
            # Update budget with actual tokens
            total_tokens = sum(
                stage.get("tokens", 0) 
                for stage in log_entry["stages"].values()
            )
            self.budget_tracker.add_usage(total_tokens)
            
            total_time = time.time() - start_time
            log_entry["total_time"] = total_time
            log_entry["total_tokens"] = total_tokens
            log_entry["final_verified"] = verification_result["verified"]
            
            self.query_log.append(log_entry)
            self.successful_queries += 1
            
            return {
                "success": True,
                "answer": generation_result["answer"],
                "context": retrieval_result["context"],
                "intent": intent_result["intent_type"],
                "verified": verification_result["verified"],
                "verification_score": verification_result.get("score", 0),
                "retry_needed": log_entry["stages"].get("retry") is not None,
                "timings": {
                    "intent": intent_result["latency"],
                    "retrieval": retrieval_result["latency"],
                    "generation": generation_result["latency"],
                    "verification": verification_result["latency"],
                    "total": total_time
                },
                "tokens_used": total_tokens,
                "query_id": query_id
            }
            
        except Exception as e:
            self.failed_queries += 1
            log_entry["error"] = str(e)
            log_entry["total_time"] = time.time() - start_time
            self.query_log.append(log_entry)
            
            return {
                "success": False,
                "error": str(e),
                "query_id": query_id
            }
    
    def _stage_intent(self, query: str) -> Dict:
        """Stage 1: Classify query intent."""
        start_time = time.time()
        
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=100)
        if wait_time > 0:
            time.sleep(wait_time)
        
        messages = [
            {"role": "system", "content": "Classify the user's query intent. Choose one: FACTUAL (asking for facts), CONCEPTUAL (asking for explanations), COMPARATIVE (comparing things), PROCEDURAL (how-to)."},
            {"role": "user", "content": f"Query: {query}\n\nIntent:"}
        ]
        
        result = self.groq.chat_completion(messages, max_tokens=50, temperature=0.3)
        
        latency = time.time() - start_time
        self.stage_timings["intent"].append(latency)
        
        # Parse intent
        intent_type = "CONCEPTUAL"  # default
        if result["success"]:
            content = result["content"].strip().upper()
            for intent in ["FACTUAL", "CONCEPTUAL", "COMPARATIVE", "PROCEDURAL"]:
                if intent in content:
                    intent_type = intent
                    break
        
        return {
            "success": result["success"],
            "intent_type": intent_type,
            "latency": latency,
            "tokens": result["usage"]["total_tokens"],
            "raw_response": result.get("content", "")
        }
    
    def _stage_retrieval(self, query: str, intent_type: str) -> Dict:
        """Stage 2: Retrieve relevant context."""
        start_time = time.time()
        
        # Adjust retrieval based on intent
        k = self.top_k
        if intent_type == "CONCEPTUAL":
            k = min(self.top_k + 2, len(self.chunks))  # Get more context for explanations
        
        relevant_chunks = self.embeddings.retrieve_top_k(
            query, 
            self.chunks, 
            k=k,
            rerank=self.rerank
        )
        
        latency = time.time() - start_time
        self.stage_timings["retrieval"].append(latency)
        
        return {
            "success": True,
            "context": relevant_chunks,
            "latency": latency,
            "chunks_retrieved": len(relevant_chunks),
            "tokens": 0  # Local operation
        }
    
    def _stage_generation(self, query: str, context: List[Dict]) -> Dict:
        """Stage 3: Generate answer from context."""
        start_time = time.time()
        
        # Build context string
        context_str = "\n\n".join([
            f"[Source {i+1}]: {chunk['text'][:500]}" 
            for i, chunk in enumerate(context[:5])
        ])
        
        # Estimate tokens
        estimated_tokens = len(context_str.split()) + len(query.split()) + 300
        
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=estimated_tokens)
        if wait_time > 0:
            time.sleep(wait_time)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer the question based on the provided context. Be concise and accurate. If the context doesn't contain enough information, say so."},
            {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"}
        ]
        
        result = self.groq.chat_completion(messages, max_tokens=400, temperature=0.7)
        
        latency = time.time() - start_time
        self.stage_timings["generation"].append(latency)
        
        return {
            "success": result["success"],
            "answer": result.get("content", ""),
            "latency": latency,
            "tokens": result["usage"]["total_tokens"]
        }
    
    def _stage_verification(self, query: str, answer: str, context: List[Dict]) -> Dict:
        """Stage 4: Verify answer quality."""
        start_time = time.time()
        
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=200)
        if wait_time > 0:
            time.sleep(wait_time)
        
        messages = [
            {"role": "system", "content": "You are a verification assistant. Rate the answer's quality on a scale of 1-10. Check: (1) Relevance to question, (2) Accuracy based on context, (3) Completeness. Respond with: SCORE: X\nVERIFIED: YES/NO\nISSUES: (list any issues)"},
            {"role": "user", "content": f"Question: {query}\n\nAnswer: {answer}\n\nVerification:"}
        ]
        
        result = self.groq.chat_completion(messages, max_tokens=200, temperature=0.3)
        
        latency = time.time() - start_time
        self.stage_timings["verification"].append(latency)
        
        # Parse verification
        verified = False
        score = 5
        issues = []
        
        if result["success"]:
            content = result["content"]
            if "SCORE:" in content:
                try:
                    score = int(content.split("SCORE:")[1].split()[0])
                except:
                    pass
            
            if "VERIFIED: YES" in content or score >= 7:
                verified = True
            
            if "ISSUES:" in content:
                issues = [content.split("ISSUES:")[1].strip()]
        
        return {
            "success": result["success"],
            "verified": verified,
            "score": score,
            "issues": issues,
            "latency": latency,
            "tokens": result["usage"]["total_tokens"],
            "raw_response": result.get("content", "")
        }
    
    def _retry_generation(self, query: str, context: List[Dict], 
                          previous_answer: str, issues: List[str]) -> Dict:
        """Retry generation with feedback."""
        start_time = time.time()
        
        context_str = "\n\n".join([
            f"[Source {i+1}]: {chunk['text'][:500]}" 
            for i, chunk in enumerate(context[:5])
        ])
        
        issues_str = "\n".join(issues) if issues else "The answer needs improvement."
        
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=400)
        if wait_time > 0:
            time.sleep(wait_time)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. The previous answer had issues. Provide an improved answer based on the context."},
            {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {query}\n\nPrevious Answer: {previous_answer}\n\nIssues: {issues_str}\n\nImproved Answer:"}
        ]
        
        result = self.groq.chat_completion(messages, max_tokens=400, temperature=0.7)
        
        latency = time.time() - start_time
        
        return {
            "success": result["success"],
            "answer": result.get("content", ""),
            "latency": latency,
            "tokens": result["usage"]["total_tokens"]
        }
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        import numpy as np
        
        stats = {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "budget_refusals": self.budget_refusals,
            "retry_count": self.retry_count,
            "success_rate": self.successful_queries / self.total_queries if self.total_queries > 0 else 0,
        }
        
        # Stage timing statistics
        for stage, timings in self.stage_timings.items():
            if timings:
                arr = np.array(timings)
                stats[f"{stage}_avg_latency"] = float(np.mean(arr))
                stats[f"{stage}_p95_latency"] = float(np.percentile(arr, 95))
        
        return stats
    
    def save_query_log(self, filepath: str):
        """Save detailed query log."""
        with open(filepath, 'w') as f:
            json.dump({
                "stats": self.get_stats(),
                "queries": self.query_log
            }, f, indent=2)
