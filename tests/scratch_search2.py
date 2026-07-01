import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.models import Fic
from search.repository import QuoteSearchRepository
from search.service import SearchService
from ingestion.embedding.local import LocalFastEmbedProvider, AsyncEmbeddingProvider
from search.reranker import AsyncRerankerProvider, LocalFastEmbedReranker
from ingestion.vector.qdrant import QdrantStore
from concurrent.futures import ThreadPoolExecutor

load_dotenv()


async def main():
    db_url = os.getenv("DATABASE_URL")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("sslmode=require", "")

    engine = create_async_engine(db_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    executor = ThreadPoolExecutor(max_workers=2)
    vector_store = QdrantStore(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embed_provider = AsyncEmbeddingProvider(LocalFastEmbedProvider(), executor)
    reranker = AsyncRerankerProvider(
        LocalFastEmbedReranker("jinaai/jina-reranker-v1-tiny-en"), executor
    )

    async with session_maker() as session:
        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()
        repo = QuoteSearchRepository(session)
        service = SearchService(repo, vector_store, embed_provider, reranker)

        print("Query 1: Regulus destroying the horcrux")
        res = await service.search_semantic(
            fic.id, fic.active_version_id, "Regulus destroying the horcrux", limit=3
        )
        for r in res.results:
            print(f"Ch {r.chapter_number} ({r.start_position}-{r.end_position}):")
            print(r.matched_text)
            print("-" * 20)


if __name__ == "__main__":
    asyncio.run(main())
