import asyncio
import os
import time
import math
from typing import List, Dict

import config
from search.repository import QuoteSearchRepository
from search.service import SearchService
from search.reranker import AsyncRerankerProvider, LocalFastEmbedReranker
from ingestion.embedding.local import LocalFastEmbedProvider, AsyncEmbeddingProvider
from ingestion.vector.qdrant import QdrantStore
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.models import Fic, Chapter, Paragraph
import statistics

# --- EVALUATION FIXTURE ---
# We use version-resilient labels: chapter number and a distinctive text substring.
# Grade 3 = direct answer, 2 = strongly relevant, 1 = related context, 0 = irrelevant
EVAL_FIXTURE = [
    {
        "query": "Regulus destroying the horcrux",
        "expected_substrings": [
            {
                "chapter_number": 81,
                "text": "charged Kreacher with destroying it",
                "grade": 3,
            },
            {
                "chapter_number": 125,
                "text": "Regulus ran into the forest as well before Pettigrew could target him",
                "grade": 1,
            },
        ],
    },
    {
        "query": "Harry was disowned",
        "expected_substrings": [
            {
                "chapter_number": 126,
                "text": "Harry would automatically become a Black if he were disowned as a Potter.",
                "grade": 3,
            },
            {"chapter_number": 42, "text": "reuniting with our family?", "grade": 2},
        ],
    },
]


async def resolve_fixtures(session, fic_id: str, version_id: str) -> List[Dict]:
    resolved_fixtures = []

    for item in EVAL_FIXTURE:
        resolved_labels = []
        for label in item["expected_substrings"]:
            ch_num = label["chapter_number"]
            text_sub = label["text"]

            stmt = (
                select(Paragraph)
                .join(Chapter, Paragraph.chapter_id == Chapter.id)
                .where(
                    Chapter.version_id == version_id, Chapter.chapter_number == ch_num
                )
            )
            res = await session.execute(stmt)
            all_paras = res.scalars().all()

            matching_paras = [
                p for p in all_paras if text_sub.lower() in p.text.lower()
            ]

            if not matching_paras:
                raise ValueError(
                    f"Failed to resolve fixture: Could not find substring '{text_sub}' in Chapter {ch_num}"
                )

            # Sort by paragraph number
            matching_paras.sort(key=lambda p: p.paragraph_number)

            # Use the last match to avoid matching author notes at the beginning
            para = matching_paras[-1]
            print(
                f"DEBUG: Resolved '{text_sub}' to Chapter {ch_num} Paragraph {para.paragraph_number} (Matched {len(matching_paras)} paras)"
            )
            resolved_labels.append(
                {
                    "chapter_number": ch_num,
                    "start": para.paragraph_number,
                    "end": para.paragraph_number,
                    "grade": label["grade"],
                    "text": text_sub,
                }
            )

        resolved_fixtures.append(
            {"query": item["query"], "relevance_labels": resolved_labels}
        )
    return resolved_fixtures


def check_overlap(r_ch, r_start, r_end, labels):
    best_grade = 0
    matched_text = None
    for label in labels:
        if label["chapter_number"] == r_ch:
            # check intersection
            overlap_start = max(r_start, label["start"])
            overlap_end = min(r_end, label["end"])
            if overlap_start <= overlap_end:
                if label["grade"] > best_grade:
                    best_grade = label["grade"]
                    matched_text = label["text"]
    return best_grade, matched_text


def compute_dcg(relevances: List[int]) -> float:
    return sum((rel) / math.log2(idx + 2) for idx, rel in enumerate(relevances))


def compute_ndcg(
    retrieved_relevances: List[int], ideal_relevances: List[int], k: int = 10
) -> float:
    dcg = compute_dcg(retrieved_relevances[:k])
    idcg = compute_dcg(sorted(ideal_relevances, reverse=True)[:k])
    return dcg / idcg if idcg > 0 else 0.0


def compute_mrr(retrieved_relevances: List[int]) -> float:
    for idx, rel in enumerate(retrieved_relevances):
        if rel >= 2:
            return 1.0 / (idx + 1)
    return 0.0


async def evaluate_pipeline(
    service: SearchService,
    fic_id: str,
    version_id: str,
    resolved_fixtures: List[Dict],
    actual_model: str,
    mem_before: float,
):
    k_dense = config.SEMANTIC_RETRIEVAL_K
    hybrid = config.SEMANTIC_HYBRID_ENABLED
    config_model = config.SEMANTIC_RERANK_MODEL
    exp = config.SEMANTIC_EXPANSION_ENABLED

    total_mrr = 0.0
    total_ndcg = 0.0
    total_recall_10 = 0.0
    total_recall_30 = 0.0

    latencies = []
    expected_ranks = []

    print("\n=======================================================")
    print("=== Running Evaluation ===")
    print(f"Retrieval K:       {k_dense}")
    print(f"Hybrid Enabled:    {hybrid}")
    print(f"Expansion Enabled: {exp}")
    print(f"Configured Model:  {config_model}")
    print(f"Actual Loaded:     {actual_model}")
    print("Runtime/Provider:  FastEmbed")
    print("=======================================================")

    for item in resolved_fixtures:
        query = item["query"]
        labels = item["relevance_labels"]
        target_count = len([lb for lb in labels if lb["grade"] >= 2])

        start_time = time.time()
        res = await service.search_semantic(
            fic_id, version_id, query, limit=50
        )  # fetch up to 50 for Recall@30
        latency = time.time() - start_time
        latencies.append(latency)

        candidates = res.evaluation_candidates or []

        # Build query table
        print(f"\nQuery: '{query}'")
        print(
            f"{'Expected Passage (Semantic Match)':<40} | {'Entered Cand. Set':<18} | {'Dense Rank':<11} | {'Final Rank':<10}"
        )
        print("-" * 87)

        retrieved_relevances = []
        hits_10 = 0
        hits_30 = 0

        # Track final ranks for targets
        target_ranks = {lb["text"]: None for lb in labels if lb["grade"] >= 2}

        for idx, c in enumerate(candidates):
            grade, matched_text = check_overlap(
                c["chapter"].chapter_number, c["start_p"], c["end_p"], labels
            )
            # print(f"DEBUG CAND: Ch {c['chapter'].chapter_number} p{c['start_p']}-{c['end_p']} | Grade: {grade}")
            retrieved_relevances.append(grade)

            rank = idx + 1
            if grade >= 2:
                if rank <= 10:
                    hits_10 += 1
                if rank <= 30:
                    hits_30 += 1
                if matched_text and target_ranks[matched_text] is None:
                    target_ranks[matched_text] = rank

        # Find candidate set stats for all expected substrings
        for label in labels:
            if label["grade"] < 2:
                continue

            text = label["text"]
            entered_set = "No"
            dense_rank = "N/A"
            final_rank = target_ranks.get(text) or "N/A"

            # Look through ALL candidates to see if it entered the candidate set
            for idx, c in enumerate(candidates):
                grade, matched_text = check_overlap(
                    c["chapter"].chapter_number, c["start_p"], c["end_p"], [label]
                )
                if grade >= 2:
                    entered_set = "Yes"
                    dense_rank = c.get("dense_rank", "N/A")
                    break

            disp_text = text if len(text) <= 37 else text[:34] + "..."
            print(
                f"{disp_text:<40} | {entered_set:<18} | {str(dense_rank):<11} | {str(final_rank):<10}"
            )

            if final_rank != "N/A":
                expected_ranks.append(final_rank)

        mrr = compute_mrr(retrieved_relevances)
        ideal = [lb["grade"] for lb in labels]
        ndcg = compute_ndcg(retrieved_relevances, ideal, k=10)

        recall_10 = hits_10 / target_count if target_count > 0 else 0.0
        recall_30 = hits_30 / target_count if target_count > 0 else 0.0

        total_mrr += mrr
        total_ndcg += ndcg
        total_recall_10 += recall_10
        total_recall_30 += recall_30

    n = len(resolved_fixtures)

    avg_mrr = total_mrr / n
    avg_ndcg = total_ndcg / n
    avg_recall_10 = total_recall_10 / n
    avg_recall_30 = total_recall_30 / n

    avg_rank = statistics.mean(expected_ranks) if expected_ranks else 0.0
    med_latency = statistics.median(latencies) if latencies else 0.0
    p95_latency = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else max(latencies)
    )

    import resource
    import sys

    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    mem_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor

    print("\n=== Benchmark Results ===")
    print(f"MRR:                       {avg_mrr:.3f}")
    print(f"Recall@10:                 {avg_recall_10:.3f}")
    print(f"Recall@30:                 {avg_recall_30:.3f}")
    print(f"nDCG@10:                   {avg_ndcg:.3f}")
    print(f"Avg Expected-Result Rank:  {avg_rank:.1f}")
    print(f"Median Latency:            {med_latency:.3f}s")
    print(f"P95 Latency:               {p95_latency:.3f}s")
    print(
        f"Peak Memory:               {mem_peak:.1f}MB (+{mem_peak - mem_before:.1f}MB)"
    )
    print(f"Actual Reranker Model:     {actual_model}")


async def main():
    import resource
    import sys

    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor

    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/quotefinder")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    db_url = db_url.replace("?sslmode=require", "")

    engine = create_async_engine(db_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    from concurrent.futures import ThreadPoolExecutor

    executor = ThreadPoolExecutor(max_workers=2)

    vector_store = QdrantStore(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embed_provider = AsyncEmbeddingProvider(LocalFastEmbedProvider(), executor)

    reranker_impl = LocalFastEmbedReranker(config.SEMANTIC_RERANK_MODEL)
    actual_model = reranker_impl.model_name
    reranker = AsyncRerankerProvider(reranker_impl, executor)

    async with session_maker() as session:
        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()
        if not fic:
            print("No active fic found.")
            return

        print("Resolving fixtures against active database version...")
        try:
            resolved_fixtures = await resolve_fixtures(
                session, fic.id, fic.active_version_id
            )
            print("Fixtures resolved successfully.")
        except Exception as e:
            print(f"Fixture Resolution Error: {e}")
            return

        repo = QuoteSearchRepository(session)
        service = SearchService(repo, vector_store, embed_provider, reranker)
        await evaluate_pipeline(
            service,
            fic.id,
            fic.active_version_id,
            resolved_fixtures,
            actual_model,
            mem_before,
        )


if __name__ == "__main__":
    asyncio.run(main())
