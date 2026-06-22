import asyncio
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from database.models.job import Job
from ingestion.repository import FicRepository
from ingestion.service import IngestionService
import re

class JobWorker:
    def __init__(self, session_maker: async_sessionmaker, fichub_adapter, embedding_provider, vector_store):
        self.session_maker = session_maker
        self.fichub_adapter = fichub_adapter
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def start_ingestion(self, job_id: str, url: str, guild_id: int):
        asyncio.create_task(self._run_ingestion(job_id, url, guild_id))

    async def _run_ingestion(self, job_id: str, url: str, guild_id: int):
        logger.info(f"Worker picking up Job {job_id} for URL: {url}")
        
        async def update_progress(msg: str):
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if not job:
                    return
                job.current_stage = msg[:100]
                job.last_heartbeat = datetime.now(timezone.utc)
                
                # Simple heuristic to extract numbers like "3800/5200" or "3800 / 5200 chunks"
                match = re.search(r'(\d+)\s*/\s*(\d+)', msg)
                if match:
                    job.progress_current = int(match.group(1))
                    job.progress_total = int(match.group(2))
                    
                await session.commit()

        try:
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = "running"
                    job.started_at = datetime.now(timezone.utc)
                    await session.commit()
            
            # Run the actual ingestion process
            # We open a new session for the repository
            async with self.session_maker() as repo_session:
                repo = FicRepository(repo_session)
                service = IngestionService(
                    repository=repo,
                    fichub=self.fichub_adapter,
                    embedding_provider=self.embedding_provider,
                    vector_store=self.vector_store,
                )
                await service.ingest_fic(url, guild_id, update_progress)
                
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.current_stage = "Finished successfully."
                    await session.commit()
                    
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = "failed"
                    job.failure_message = str(e)
                    job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
