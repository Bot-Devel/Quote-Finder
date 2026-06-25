import asyncio
import time
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from database.models import Fic
from ingestion.embedding import LocalFastEmbedProvider, AsyncEmbeddingProvider
from search.reranker import LocalFastEmbedReranker, AsyncRerankerProvider
from ingestion.vector import QdrantStore
from search.repository import QuoteSearchRepository
from search.service import SearchService
import config
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

async def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")

    engine = create_async_engine(DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    vector_store = QdrantStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    executor = ThreadPoolExecutor(max_workers=2)
    sync_embedding = LocalFastEmbedProvider()
    embedding_provider = AsyncEmbeddingProvider(sync_embedding, executor)
    
    print("Loading reranker...")
    sync_reranker = LocalFastEmbedReranker()
    reranker_provider = AsyncRerankerProvider(sync_reranker, executor)

    async with session_maker() as session:
        # Find active fic
        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()
        if not fic:
            print("No active fic found.")
            return

        repo = QuoteSearchRepository(session)
        service = SearchService(
            repository=repo,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            reranker=reranker_provider
        )

        query = "Regulus destroying the horcrux"
        
        print(f"\n--- EVALUATION: {query} ---")
        
        # 1. DENSE ONLY (simulating reranker disabled)
        print("\n[ RUNNING DENSE-ONLY SEARCH (K=20) ]")
        config.SEMANTIC_RERANK_ENABLED = False
        res_dense = await service.search_semantic(fic.id, fic.active_version_id, query, limit=10)
        for i, res in enumerate(res_dense.results[:5]):
            print(f"Rank {i+1}: Ch {res.chapter_number} - Score: {res.semantic_score:.3f} | {res.matched_text[:80].replace(chr(10), ' ')}...")
            
        # 2. DENSE + RERANKER
        print("\n[ RUNNING HYBRID RERANK SEARCH (K=30) ]")
        config.SEMANTIC_RERANK_ENABLED = True
        config.SEMANTIC_RETRIEVAL_K = 30
        res_rerank = await service.search_semantic(fic.id, fic.active_version_id, query, limit=10)
        for i, res in enumerate(res_rerank.results[:5]):
            print(f"\n================ Rank {i+1} | Ch {res.chapter_number} | Score: {res.semantic_score:.3f} ================")
            print(res.matched_text)

if __name__ == "__main__":
    asyncio.run(main())
