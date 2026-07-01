import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import config
from search.repository import QuoteSearchRepository
from search.service import SearchService
from search.reranker import AsyncRerankerProvider, LocalFastEmbedReranker
from ingestion.embedding.local import LocalFastEmbedProvider, AsyncEmbeddingProvider
from ingestion.vector.qdrant import QdrantStore
from concurrent.futures import ThreadPoolExecutor


async def main():
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

    executor = ThreadPoolExecutor(max_workers=2)

    vector_store = QdrantStore(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embed_provider = AsyncEmbeddingProvider(LocalFastEmbedProvider(), executor)
    reranker = AsyncRerankerProvider(
        LocalFastEmbedReranker(config.SEMANTIC_RERANK_MODEL), executor
    )

    async with session_maker() as session:
        from sqlalchemy import select
        from database.models import Fic

        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()
        if not fic:
            print("No active fic found.")
            return

        repo = QuoteSearchRepository(session)
        service = SearchService(repo, vector_store, embed_provider, reranker)

        query = "harry was disowned"
        print(f"Running semantic search for: {query}")

        # We need to peek into the candidates, so let's mock or patch it,
        # or we can reconstruct the expected chunk text from the DB bounds.
        res = await service.search_semantic(
            fic.id, fic.active_version_id, query, limit=5
        )

        for idx, r in enumerate(res.results):
            # Fetch paragraphs from DB to reconstruct chunk text
            fetch_ranges = [(r.chapter_id, r.start_position, r.end_position)]
            all_paragraphs = await repo.fetch_contexts_bulk(fetch_ranges)

            matched_lines = [
                p.text for p in sorted(all_paragraphs, key=lambda p: p.paragraph_number)
            ]
            expected_chunk_text = "\n\n".join(matched_lines)

            # Apply deterministic trimming logic
            if len(expected_chunk_text) > 3990:
                expected_chunk_text = expected_chunk_text[:3990].rstrip() + "..."

            print("=" * 60)
            print(
                f"Rank {idx + 1} | Ch: {r.chapter_number} | Score: {r.semantic_score:.3f}"
            )
            print("--- Displayed Text ---")
            print(r.matched_text)

            assert r.matched_text == expected_chunk_text, (
                f"Mismatch at rank {idx + 1}!\nExpected:\n{expected_chunk_text}\nGot:\n{r.matched_text}"
            )
            print("SUCCESS: Displayed passage exactly matches the trimmed chunk text.")


if __name__ == "__main__":
    asyncio.run(main())
