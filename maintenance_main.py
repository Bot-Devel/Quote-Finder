import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ingestion.embedding import LocalFastEmbedProvider, AsyncEmbeddingProvider
from ingestion.vector import QdrantStore
from adapters.fichub import FicHub
from ingestion.worker import JobWorker
import config

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

logger.add(
    "quote-finder-maintenance.log", rotation="10 MB", retention="5 days", level="INFO"
)


class LazyEmbeddingProvider:
    def __init__(self):
        self._provider = None
        self._executor = None
        self._model_name = config.SEMANTIC_EMBEDDING_MODEL

    @property
    def provider(self):
        if not self._provider:
            logger.info("Lazily loading document embedding model...")
            self._executor = ThreadPoolExecutor(max_workers=2)
            sync_provider = LocalFastEmbedProvider()
            self._provider = AsyncEmbeddingProvider(sync_provider, self._executor)
        return self._provider

    @property
    def model_name(self):
        return self._model_name

    @property
    def dimensions(self):
        return 384

    async def embed_documents(self, texts, progress_callback=None):
        return await self.provider.embed_documents(
            texts, progress_callback=progress_callback
        )

    async def embed_query(self, query):
        return await self.provider.embed_query(query)

    def shutdown(self):
        if self._executor:
            self._executor.shutdown(wait=True)


async def main():
    logger.info("Starting nightly maintenance process...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    vector_store = QdrantStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    fichub_adapter = FicHub()
    lazy_embedding = LazyEmbeddingProvider()

    worker = JobWorker(
        session_maker=session_maker,
        fichub_adapter=fichub_adapter,
        embedding_provider=lazy_embedding,
        vector_store=vector_store,
    )

    try:
        await worker.recover_stale_jobs()
        due_fics = await worker.get_due_fics()

        if not due_fics:
            logger.info("No fics are due for auto-refresh. Exiting.")
            return

        logger.info(f"Found {len(due_fics)} fics due for auto-refresh.")
        job_ids = []
        for fic in due_fics:
            job_id = await worker.create_refresh_job_if_needed(fic.id, fic.source_url)
            if job_id:
                job_ids.append(job_id)

        for jid in job_ids:
            logger.info(f"Processing nightly refresh job {jid}...")
            await worker.process_job_by_id(jid)

        logger.info("Nightly maintenance completed successfully.")
    except Exception:
        logger.exception("Maintenance process encountered a critical error.")
    finally:
        lazy_embedding.shutdown()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
