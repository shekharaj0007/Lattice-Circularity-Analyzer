"""Main 4-stage RAG pipeline with instrumentation."""
import time
from typing import Dict, List, Optional
import json
from .groq_client import InstrumentedGroqClient
from .embeddings import EmbeddingEngine
from .rate_limiter import RateLimiter, TokenBudgetTracker
from .citations import CitationExtractor
from .evidence_gate import EvidenceGate


class Pipeline:
    """
    4-stage pipeline with evidence gate: Intent → Retrieval → [Evidence Gate] → Generation → Verification
    
    Evidence gate skips generation when evidence is weak, saving tokens.
    Citations verified deterministically for correctness.
    """
    
    # Prompt size caps (tokens)
    MAX_PROMPT_TOKENS = 4000
    MAX_CONTEXT_CHARS = 3000  # Approximate token limit for context
    
    def __init__(self, 
                 groq_client: InstrumentedGroqClient,
                 embedding_engine: EmbeddingEngine,
                 rate_limiter: RateLimiter,
                 budget_tracker: TokenBudgetTracker,
                 chunks: List[Dict],
                 top_k: int = 5,
                 rerank: bool = False,
                 max_retries: int = 1,
                 intent_client: Optional[InstrumentedGroqClient] = None,
                 generation_client: Optional[InstrumentedGroqClient] = None,
                 verification_client: Optional[InstrumentedGroqClient] = None,
                 evidence_gate_enabled: bool = True,
                 citation_verification_enabled: bool = True):
        """
        Initialize pipeline with strategic model sizing and correctness features.
        
        Args:
            groq_client: Default client (used as fallback)
            embedding_engine: Local embeddings
            rate_limiter: Rate limiting
            budget_tracker: Token budget tracking
            chunks: Document chunks
            top_k: Number of chunks to retrieve
            rerank: Enable re-ranking
            max_retries: Max retry attempts (2 verify failures = refusal)
            intent_client: Small/fast model for intent classification (optional)
            generation_client: Large/capable model for generation (optional)
            verification_client: Small/fast model for verification (optional)
            evidence_gate_enabled: Enable evidence gate (skip generation when evidence weak)
            citation_verification_enabled: Enable citation verification
        """
        # Default client (fallback)
        self.groq = groq_client
        
        # Stage-specific clients (use dedicated or fall back to default)
        self.intent_client = intent_client or groq_client
        self.generation_client = generation_client or groq_client
        self.verification_client = verification_client or groq_client
        
        self.embeddings = embedding_engine
        self.rate_limiter = rate_limiter
        self.budget_tracker = budget_tracker
        self.chunks = chunks
        self.top_k = top_k
        self.rerank = rerank
        self.max_retries = max_retries
        
        # Correctness features
        self.evidence_gate_enabled = evidence_gate_enabled
        self.citation_verification_enabled = citation_verification_enabled
        self.evidence_gate = EvidenceGate()
        self.citation_extractor = CitationExtractor()
        
        # Track which models are used for each stage
        self.model_config = {
            "intent": self.intent_client.model,
            "generation": self.generation_client.model,
            "verification": self.verification_client.model
        }
        
        # Pipeline metrics
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.budget_refusals = 0
        self.retry_count = 0
        self.evidence_gate_refusals = 0  # Early refusals (no generation)
        self.citation_failures = 0  # Failed citation verification
        self.stage_timings = {
            "intent": [],
            "retrieval": [],
            "evidence_gate": [],
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
            
            # Stage 2.5: Evidence Gate (skip generation if evidence weak)
            if self.evidence_gate_enabled:
                evidence_start = time.time()
                should_proceed, reason, evidence_meta = self.evidence_gate.assess_evidence(
                    retrieval_result["context"], query
                )
                evidence_latency = time.time() - evidence_start
                self.stage_timings["evidence_gate"].append(evidence_latency)
                
                log_entry["stages"]["evidence_gate"] = {
                    "latency": evidence_latency,
                    "decision": evidence_meta["decision"],
                    "reason": reason,
                    **evidence_meta
                }
                
                if not should_proceed:
                    # Early refusal - save tokens by not generating
                    self.evidence_gate_refusals += 1
                    self.failed_queries += 1
                    log_entry["refusal_reason"] = "weak_evidence"
                    log_entry["tokens_saved"] = 400  # Estimated generation cost
                    self.query_log.append(log_entry)
                    
                    return {
                        "success": False,  # Refusals never count as success
                        "refusal": True,
                        "refusal_reason": reason,
                        "evidence_metadata": evidence_meta,
                        "query_id": query_id,
                        "timings": {
                            "intent": intent_result["latency"],
                            "retrieval": retrieval_result["latency"],
                            "evidence_gate": evidence_latency,
                            "total": time.time() - start_time
                        }
                    }
            
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
            
            # Retry logic with two-strike rule
            verification_attempts = 1
            if not verification_result["verified"] and self.max_retries > 0:
                self.retry_count += 1
                verification_attempts += 1
                
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
                    
                    # Two-strike rule: two verify failures = refusal
                    if not verification_result["verified"]:
                        self.failed_queries += 1
                        self.citation_failures += 1
                        log_entry["refusal_reason"] = "two_verify_failures"
                        self.query_log.append(log_entry)
                        
                        return {
                            "success": False,  # Refusals never count as success
                            "refusal": True,
                            "refusal_reason": "Answer failed verification twice. Cannot provide verified answer.",
                            "verification_attempts": verification_attempts,
                            "issues": verification_result["issues"],
                            "query_id": query_id,
                            "timings": {
                                "intent": intent_result["latency"],
                                "retrieval": retrieval_result["latency"],
                                "generation": generation_result["latency"],
                                "verification": verification_result["latency"],
                                "total": time.time() - start_time
                            }
                        }
            
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
        
        # Use small/fast model for intent classification
        result = self.intent_client.chat_completion(messages, max_tokens=50, temperature=0.3)
        
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
        """Stage 3: Generate answer from context with prompt size caps."""
        start_time = time.time()
        
        # Build context string with size cap
        context_parts = []
        context_char_count = 0
        
        for i, chunk in enumerate(context[:5]):  # Max 5 chunks
            chunk_text = chunk['text'][:500]  # Max 500 chars per chunk
            
            # Check if adding this chunk would exceed limit
            if context_char_count + len(chunk_text) > self.MAX_CONTEXT_CHARS:
                # Truncate to fit
                remaining = self.MAX_CONTEXT_CHARS - context_char_count
                if remaining > 100:  # Only add if substantial space left
                    chunk_text = chunk_text[:remaining]
                    context_parts.append(f"[Chunk c{chunk['id']}]: {chunk_text}...")
                break
            
            context_parts.append(f"[Chunk c{chunk['id']}]: {chunk_text}")
            context_char_count += len(chunk_text)
        
        context_str = "\n\n".join(context_parts)
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_prompt_tokens = len(context_str) // 4 + len(query) // 4 + 100
        estimated_tokens = estimated_prompt_tokens + 400  # + max_tokens
        
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=estimated_tokens)
        if wait_time > 0:
            time.sleep(wait_time)
        
        system_prompt = """You are a helpful assistant. Answer based ONLY on the provided context.
Include citations in format: [Paper vN, p.PAGE, chunk cID]
Example: The transformer uses attention [Attention Is All You Need v7, p.3, chunk c1].
If context doesn't answer the question, say so."""
        
        # Enforce prompt size cap
        user_content = f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"
        if len(system_prompt) + len(user_content) > self.MAX_PROMPT_TOKENS * 4:  # Approximate
            # Truncate context further
            max_context_len = self.MAX_PROMPT_TOKENS * 4 - len(system_prompt) - len(query) - 200
            context_str = context_str[:max_context_len]
            user_content = f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Use large/capable model for generation (the hard task)
        result = self.generation_client.chat_completion(messages, max_tokens=400, temperature=0.7)
        
        latency = time.time() - start_time
        self.stage_timings["generation"].append(latency)
        
        return {
            "success": result["success"],
            "answer": result.get("content", ""),
            "latency": latency,
            "tokens": result["usage"]["total_tokens"]
        }
    
    def _stage_verification(self, query: str, answer: str, context: List[Dict]) -> Dict:
        """Stage 4: Verify answer quality with citation checking."""
        start_time = time.time()
        
        issues = []
        verified = False
        score = 5
        
        # First: Deterministic citation verification (fast, reliable)
        if self.citation_verification_enabled:
            citations = self.citation_extractor.extract_citations(answer)
            
            if citations:
                citations_valid, citation_issues = self.citation_extractor.verify_citations(
                    answer, citations, context
                )
                
                if not citations_valid:
                    issues.extend(citation_issues)
                    verified = False
                    score = 3
                else:
                    # Citations valid, check for fabricated quotes
                    quotes_valid, quote_issue = self.citation_extractor.verify_no_fabrication(
                        answer, context
                    )
                    if not quotes_valid:
                        issues.append(quote_issue)
                        verified = False
                        score = 4
                    else:
                        # All deterministic checks passed
                        verified = True
                        score = 8
            else:
                # No citations found
                issues.append("No citations found in answer")
                verified = False
                score = 4
        
        # Second: LLM-based verification (for additional quality checks)
        # Wait for rate limit
        wait_time = self.rate_limiter.acquire(estimated_tokens=200)
        if wait_time > 0:
            time.sleep(wait_time)
        
        messages = [
            {"role": "system", "content": "You are a verification assistant. Check: (1) Relevance to question, (2) Completeness. Rate quality 1-10. Respond: SCORE: X\nRELEVANT: YES/NO\nISSUES: (list any)"},
            {"role": "user", "content": f"Question: {query}\n\nAnswer: {answer}\n\nVerification:"}
        ]
        
        # Use small/fast model for verification (simple checking task)
        result = self.verification_client.chat_completion(messages, max_tokens=200, temperature=0.3)
        
        latency = time.time() - start_time
        self.stage_timings["verification"].append(latency)
        
        # Parse LLM verification
        llm_score = 5
        if result["success"]:
            content = result["content"]
            if "SCORE:" in content:
                try:
                    llm_score = int(content.split("SCORE:")[1].split()[0])
                except:
                    pass
            
            if "RELEVANT: NO" in content:
                issues.append("Answer not relevant to question")
                verified = False
            
            if "ISSUES:" in content:
                llm_issues = content.split("ISSUES:")[1].strip()
                if llm_issues and llm_issues not in ["None", "none", "N/A"]:
                    issues.append(llm_issues)
        
        # Combine scores (citation check weighted more heavily)
        if self.citation_verification_enabled and verified:
            # Citations passed, incorporate LLM relevance check
            if llm_score < 6:
                verified = False
                score = min(score, llm_score)
        
        return {
            "success": result["success"],
            "verified": verified,
            "score": score,
            "issues": issues,
            "latency": latency,
            "tokens": result["usage"]["total_tokens"],
            "raw_response": result.get("content", ""),
            "citations_checked": self.citation_verification_enabled
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
        
        # Use large/capable model for retry generation (still a hard task)
        result = self.generation_client.chat_completion(messages, max_tokens=400, temperature=0.7)
        
        latency = time.time() - start_time
        
        return {
            "success": result["success"],
            "answer": result.get("content", ""),
            "latency": latency,
            "tokens": result["usage"]["total_tokens"]
        }
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics with correctness features."""
        import numpy as np
        
        stats = {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "budget_refusals": self.budget_refusals,
            "evidence_gate_refusals": self.evidence_gate_refusals,
            "citation_failures": self.citation_failures,
            "retry_count": self.retry_count,
            "success_rate": self.successful_queries / self.total_queries if self.total_queries > 0 else 0,
            "model_config": self.model_config,  # Track which models used
            "features": {
                "evidence_gate_enabled": self.evidence_gate_enabled,
                "citation_verification_enabled": self.citation_verification_enabled
            }
        }
        
        # Add evidence gate stats
        if self.evidence_gate_enabled:
            stats["evidence_gate_stats"] = self.evidence_gate.get_stats()
        
        # Add citation stats
        if self.citation_verification_enabled:
            stats["citation_stats"] = self.citation_extractor.get_stats()
        
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
