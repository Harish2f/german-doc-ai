"""
RAGAS Evaluation Script for GermanDocAI
Evaluates RAG pipeline quality on BaFin Annual Report 2024

Metrics:
- Faithfulness: answer only contains info from retrieved chunks
- Answer Relevancy: answer addresses the question
- Context Precision: retrieved chunks are relevant to the question
"""

import os
import asyncio
import json
import httpx
from datetime import datetime

# Configuration
BASE_URL = os.getenv("GERMANDOCAI_URL", "https://germandocai.lemonpond-bd30645e.germanywestcentral.azurecontainerapps.io")
API_KEY = os.getenv("GERMANDOCAI_API_KEY", "dev-secret-key")
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# Test questions about BaFin Annual Report 2024
TEST_QUESTIONS = [
    "What were the primary supervisory risks identified by BaFin in 2024?",
    "How did BaFin address cyber risks in 2024 under DORA?",
    "What are the key implications of MiCAR for cryptoasset service providers?",
    "How did BaFin use AI systems to detect market manipulation?",
    "What measures did BaFin take against money laundering in 2024?",
    "How did BaFin assess risks from commercial real estate corrections?",
    "What enforcement actions did BaFin impose in the banking sector in 2024?",
    "How did BaFin supervise ESG disclosures under SFDR?",
    "What role did geopolitical tensions play in BaFin supervisory priorities?",
    "How did BaFin prepare for Digital Operational Resilience Act implementation?",
]


async def query_rag_pipeline(question: str) -> dict:
    """Query the RAG pipeline and return answer and contexts."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/ask/",
            headers=HEADERS,
            json={
                "query": question,
                "doc_types": ["bafin"],
                "top_k": 5,
                "user_id": "ragas-eval",
            },
        )
        response.raise_for_status()
        return response.json()


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Simple faithfulness check — what fraction of answer sentences
    can be grounded in the retrieved contexts.
    
    Note: Full RAGAS faithfulness uses an LLM judge.
    This is a keyword-overlap approximation.
    """
    if not contexts or not answer:
        return 0.0

    combined_context = " ".join(contexts).lower()
    sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 20]

    if not sentences:
        return 0.0

    grounded = 0
    for sentence in sentences:
        words = set(sentence.lower().split())
        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "of", "to", "and", "that", "for"}
        content_words = words - stop_words
        if len(content_words) == 0:
            continue
        matches = sum(1 for w in content_words if w in combined_context)
        if matches / len(content_words) > 0.5:
            grounded += 1

    return round(grounded / len(sentences), 3)


def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    Simple answer relevancy — keyword overlap between question and answer.
    
    Note: Full RAGAS uses an LLM to generate synthetic questions from the answer
    and measures similarity to the original question.
    """
    if not answer:
        return 0.0

    question_words = set(question.lower().split())
    answer_words = set(answer.lower().split())
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "of", "to", "and", "that", "for", "what", "how", "did"}
    q_content = question_words - stop_words
    a_content = answer_words - stop_words

    if not q_content:
        return 0.0

    overlap = q_content & a_content
    return round(len(overlap) / len(q_content), 3)


def compute_context_precision(question: str, contexts: list[str]) -> float:
    """
    Simple context precision — fraction of retrieved chunks relevant to question.
    
    Note: Full RAGAS uses an LLM judge per chunk.
    """
    if not contexts:
        return 0.0

    question_words = set(question.lower().split())
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "of", "to", "and", "that", "for", "what", "how"}
    q_content = question_words - stop_words

    relevant = 0
    for ctx in contexts:
        ctx_words = set(ctx.lower().split())
        overlap = q_content & ctx_words
        if len(overlap) / max(len(q_content), 1) > 0.3:
            relevant += 1

    return round(relevant / len(contexts), 3)


async def evaluate():
    """Run RAGAS evaluation on all test questions."""
    print(f"\nGermanDocAI RAGAS Evaluation")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Questions: {len(TEST_QUESTIONS)}")
    print("=" * 60)

    results = []
    total_faithfulness = 0.0
    total_relevancy = 0.0
    total_precision = 0.0

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(TEST_QUESTIONS)}] {question[:60]}...")

        try:
            response = await query_rag_pipeline(question)
            answer = response.get("answer", "")
            chunks = response.get("chunks", [])
            contexts = [c["text"] for c in chunks]

            faithfulness = compute_faithfulness(answer, contexts)
            relevancy = compute_answer_relevancy(question, answer)
            precision = compute_context_precision(question, contexts)

            total_faithfulness += faithfulness
            total_relevancy += relevancy
            total_precision += precision

            result = {
                "question": question,
                "answer": answer[:200],
                "chunks_retrieved": len(chunks),
                "faithfulness": faithfulness,
                "answer_relevancy": relevancy,
                "context_precision": precision,
            }
            results.append(result)

            print(f"  Chunks: {len(chunks)} | Faithfulness: {faithfulness} | Relevancy: {relevancy} | Precision: {precision}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"question": question, "error": str(e)})

    n = len([r for r in results if "error" not in r])
    print("\n" + "=" * 60)
    print("RAGAS EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Questions evaluated: {n}/{len(TEST_QUESTIONS)}")
    print(f"Avg Faithfulness:     {total_faithfulness/max(n,1):.3f}")
    print(f"Avg Answer Relevancy: {total_relevancy/max(n,1):.3f}")
    print(f"Avg Context Precision:{total_precision/max(n,1):.3f}")
    print(f"Overall Score:        {(total_faithfulness + total_relevancy + total_precision)/(3*max(n,1)):.3f}")
    print("=" * 60)

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": "gpt-4o",
        "embedding_model": "jina-v3",
        "doc_types": ["bafin"],
        "summary": {
            "questions_evaluated": n,
            "avg_faithfulness": round(total_faithfulness/max(n,1), 3),
            "avg_answer_relevancy": round(total_relevancy/max(n,1), 3),
            "avg_context_precision": round(total_precision/max(n,1), 3),
            "overall_score": round((total_faithfulness + total_relevancy + total_precision)/(3*max(n,1)), 3),
        },
        "results": results,
    }

    with open("scripts/ragas_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to scripts/ragas_results.json")
    return output


if __name__ == "__main__":
    asyncio.run(evaluate())