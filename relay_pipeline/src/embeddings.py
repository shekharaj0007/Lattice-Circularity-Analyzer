"""Local embedding generation using sentence-transformers."""
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import time


class EmbeddingEngine:
    """Generate embeddings using local sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Models:
        - all-MiniLM-L6-v2: Fast, 384 dims, good general purpose
        - all-mpnet-base-v2: Better quality, 768 dims, slower
        """
        self.model_name = model_name
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"✓ Model loaded: {model_name}")
    
    def embed_chunks(self, chunks: List[Dict], batch_size: int = 32) -> List[Dict]:
        """Generate embeddings for chunks."""
        texts = [c["text"] for c in chunks]
        
        start_time = time.time()
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        duration = time.time() - start_time
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i]
        
        print(f"Generated {len(chunks)} embeddings in {duration:.2f}s "
              f"({len(chunks)/duration:.1f} chunks/sec)")
        
        return chunks
    
    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a query."""
        return self.model.encode([query], convert_to_numpy=True)[0]
    
    def compute_similarity(self, query_embedding: np.ndarray, 
                          chunk_embeddings: List[np.ndarray]) -> List[float]:
        """Compute cosine similarity between query and chunks."""
        # Normalize
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        similarities = []
        for chunk_emb in chunk_embeddings:
            chunk_norm = chunk_emb / np.linalg.norm(chunk_emb)
            sim = np.dot(query_norm, chunk_norm)
            similarities.append(float(sim))
        
        return similarities
    
    def retrieve_top_k(self, query: str, chunks: List[Dict], 
                       k: int = 5, rerank: bool = False) -> List[Dict]:
        """Retrieve top-k most similar chunks."""
        query_emb = self.embed_query(query)
        chunk_embs = [c["embedding"] for c in chunks]
        
        similarities = self.compute_similarity(query_emb, chunk_embs)
        
        # Add similarity scores
        for i, chunk in enumerate(chunks):
            chunk["similarity"] = similarities[i]
        
        # Sort by similarity
        ranked_chunks = sorted(chunks, key=lambda x: x["similarity"], reverse=True)
        
        top_k = ranked_chunks[:k]
        
        if rerank:
            # Simple re-ranking: prefer longer, more complete chunks
            for chunk in top_k:
                chunk["rerank_score"] = (
                    chunk["similarity"] * 0.7 + 
                    min(chunk["char_count"] / 500, 1.0) * 0.3
                )
            top_k = sorted(top_k, key=lambda x: x["rerank_score"], reverse=True)
        
        return top_k


if __name__ == "__main__":
    # Test embedding
    engine = EmbeddingEngine()
    
    test_chunks = [
        {"id": 0, "text": "Attention mechanisms are key to transformer models.", "char_count": 50},
        {"id": 1, "text": "Deep learning requires large datasets.", "char_count": 40},
        {"id": 2, "text": "The transformer architecture uses self-attention.", "char_count": 48},
    ]
    
    chunks_with_emb = engine.embed_chunks(test_chunks)
    
    query = "How do transformers work?"
    results = engine.retrieve_top_k(query, chunks_with_emb, k=2)
    
    print(f"\nQuery: {query}")
    for r in results:
        print(f"  Score: {r['similarity']:.3f} - {r['text'][:50]}")
