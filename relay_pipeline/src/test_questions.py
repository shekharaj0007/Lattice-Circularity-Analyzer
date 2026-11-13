"""Test questions for evaluating pipeline quality."""
from typing import Dict, List

TEST_QUESTIONS = [
    # Attention Is All You Need
    {
        "id": 1,
        "question": "What is the self-attention mechanism in transformers?",
        "paper": "Attention Is All You Need",
        "type": "CONCEPTUAL",
        "expected_topics": ["attention", "queries", "keys", "values", "mechanism"]
    },
    {
        "id": 2,
        "question": "How many layers does the transformer model have?",
        "paper": "Attention Is All You Need",
        "type": "FACTUAL",
        "expected_topics": ["layers", "encoder", "decoder", "architecture"]
    },
    {
        "id": 3,
        "question": "What is positional encoding used for in transformers?",
        "paper": "Attention Is All You Need",
        "type": "CONCEPTUAL",
        "expected_topics": ["positional", "encoding", "sequence", "order"]
    },
    {
        "id": 4,
        "question": "Compare multi-head attention with single-head attention.",
        "paper": "Attention Is All You Need",
        "type": "COMPARATIVE",
        "expected_topics": ["multi-head", "attention", "parallel", "subspaces"]
    },
    {
        "id": 5,
        "question": "What datasets were used to evaluate the transformer model?",
        "paper": "Attention Is All You Need",
        "type": "FACTUAL",
        "expected_topics": ["WMT", "dataset", "translation", "English", "German"]
    },
    
    # Moshi paper
    {
        "id": 6,
        "question": "What is Moshi and what problem does it solve?",
        "paper": "Moshi",
        "type": "CONCEPTUAL",
        "expected_topics": ["speech", "text", "foundation model", "dialogue", "real-time"]
    },
    {
        "id": 7,
        "question": "How does Moshi handle real-time dialogue?",
        "paper": "Moshi",
        "type": "PROCEDURAL",
        "expected_topics": ["streaming", "latency", "real-time", "processing"]
    },
    {
        "id": 8,
        "question": "What are the key components of the Moshi architecture?",
        "paper": "Moshi",
        "type": "FACTUAL",
        "expected_topics": ["architecture", "components", "speech", "text", "model"]
    },
    {
        "id": 9,
        "question": "What datasets were used to train Moshi?",
        "paper": "Moshi",
        "type": "FACTUAL",
        "expected_topics": ["training", "dataset", "speech", "data"]
    },
    {
        "id": 10,
        "question": "How does Moshi compare to traditional speech-to-text systems?",
        "paper": "Moshi",
        "type": "COMPARATIVE",
        "expected_topics": ["speech-to-text", "comparison", "advantages", "traditional"]
    },
    
    # Dynamic Chunking paper
    {
        "id": 11,
        "question": "What is dynamic chunking in sequence modeling?",
        "paper": "Dynamic Chunking",
        "type": "CONCEPTUAL",
        "expected_topics": ["chunking", "dynamic", "sequence", "modeling", "hierarchical"]
    },
    {
        "id": 12,
        "question": "What problem does dynamic chunking solve?",
        "paper": "Dynamic Chunking",
        "type": "CONCEPTUAL",
        "expected_topics": ["problem", "sequence", "long-range", "efficiency"]
    },
    {
        "id": 13,
        "question": "How does hierarchical modeling work in this approach?",
        "paper": "Dynamic Chunking",
        "type": "PROCEDURAL",
        "expected_topics": ["hierarchical", "levels", "processing", "chunks"]
    },
    {
        "id": 14,
        "question": "What are the computational benefits of dynamic chunking?",
        "paper": "Dynamic Chunking",
        "type": "FACTUAL",
        "expected_topics": ["computational", "efficiency", "benefits", "speed"]
    },
    {
        "id": 15,
        "question": "Compare static and dynamic chunking approaches.",
        "paper": "Dynamic Chunking",
        "type": "COMPARATIVE",
        "expected_topics": ["static", "dynamic", "comparison", "advantages"]
    },
    
    # Cross-paper questions
    {
        "id": 16,
        "question": "How do attention mechanisms relate to sequence modeling?",
        "paper": "Multiple",
        "type": "CONCEPTUAL",
        "expected_topics": ["attention", "sequence", "modeling", "relationship"]
    },
    {
        "id": 17,
        "question": "What are the main challenges in processing long sequences?",
        "paper": "Multiple",
        "type": "CONCEPTUAL",
        "expected_topics": ["long", "sequences", "challenges", "computational"]
    },
    {
        "id": 18,
        "question": "How do modern models handle temporal or sequential information?",
        "paper": "Multiple",
        "type": "CONCEPTUAL",
        "expected_topics": ["temporal", "sequential", "information", "models"]
    },
]


def get_questions_by_type(question_type: str = None):
    """Get questions filtered by type."""
    if question_type is None:
        return TEST_QUESTIONS
    return [q for q in TEST_QUESTIONS if q["type"] == question_type]


def get_questions_by_paper(paper_name: str):
    """Get questions for a specific paper."""
    return [q for q in TEST_QUESTIONS if paper_name.lower() in q["paper"].lower()]


def evaluate_answer_quality(answer: str, expected_topics: list, verified: bool) -> Dict:
    """
    Simple evaluation of answer quality.
    
    Returns:
        - topic_coverage: fraction of expected topics mentioned
        - answer_length: character count
        - verified: from pipeline verification
        - quality_score: 0-1 score
    """
    answer_lower = answer.lower()
    
    topics_found = sum(1 for topic in expected_topics if topic.lower() in answer_lower)
    topic_coverage = topics_found / len(expected_topics) if expected_topics else 0
    
    # Quality heuristics
    quality_score = 0
    
    # Topic coverage (40%)
    quality_score += topic_coverage * 0.4
    
    # Verification (30%)
    if verified:
        quality_score += 0.3
    
    # Answer length (20% - prefer substantial answers)
    length_score = min(len(answer) / 500, 1.0)  # 500 chars = full score
    quality_score += length_score * 0.2
    
    # Not empty (10%)
    if len(answer) > 50:
        quality_score += 0.1
    
    return {
        "topic_coverage": topic_coverage,
        "topics_found": topics_found,
        "topics_expected": len(expected_topics),
        "answer_length": len(answer),
        "verified": verified,
        "quality_score": quality_score
    }


if __name__ == "__main__":
    print(f"Total test questions: {len(TEST_QUESTIONS)}")
    
    for qtype in ["FACTUAL", "CONCEPTUAL", "COMPARATIVE", "PROCEDURAL"]:
        questions = get_questions_by_type(qtype)
        print(f"  {qtype}: {len(questions)}")
    
    print("\nSample questions:")
    for q in TEST_QUESTIONS[:3]:
        print(f"  Q{q['id']}: {q['question']}")
