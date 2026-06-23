import asyncio
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, update, or_, and_, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from database.models.job import Job
from database.models.fic import Fic
from ingestion.repository import FicRepository
from ingestion.service import IngestionService
import re

class JobWorker:
    def __init__(self, session_maker: async_sessionmaker, fichub_adapter, embedding_provider, vector_store):
        self.session_maker = session_maker
        self.fichub_adapter = fichub_adapter
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def recover_stale_jobs(self):
        async with self.session_maker() as session:
            stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
            stmt = update(Job).where(
                and_(
                    Job.status == "running",
                    Job.last_heartbeat < stale_threshold
                )
            ).values(
                status="failed",
                failure_message="Job timed out or worker crashed without completing.",
                completed_at=datetime.now(timezone.utc)
            )
            await session.execute(stmt)
            await session.commit()

    async def get_due_fics(self):
        async with self.session_maker() as session:
            now = datetime.now(timezone.utc)
            stmt = select(Fic).where(
                and_(
                    Fic.auto_refresh_enabled == True,
                    or_(
                        Fic.next_refresh_at <= now,
                        Fic.next_refresh_at == None
                    )
                )
            )
            return (await session.execute(stmt)).scalars().all()

    async def create_refresh_job_if_needed(self, fic_id: str, source_url: str):
        async with self.session_maker() as session:
            now = datetime.now(timezone.utc)
            job_check = select(Job).where(
                and_(
                    Job.fic_id == fic_id,
                    Job.job_type == "refresh",
                    Job.status.in_(["queued", "running"])
                )
            )
            existing_job = (await session.execute(job_check)).scalars().first()
            job_id = None
            if not existing_job:
                job = Job(
                    job_type="refresh",
                    fic_id=fic_id,
                    target_url=source_url,
                )
                session.add(job)
                await session.flush()
                job_id = job.id
            
            # Update next_refresh_at
            fic = await session.get(Fic, fic_id)
            if fic:
                fic.next_refresh_at = now + timedelta(hours=fic.refresh_interval_hours or 24)
            await session.commit()
            
            return job_id or (existing_job.id if existing_job else None)

    async def process_job_by_id(self, job_id: str):
        # Claim atomically
        async with self.session_maker() as session:
            stmt = text("""
                UPDATE jobs 
                SET status = 'running', 
                    started_at = NOW(), 
                    last_heartbeat = NOW()
                WHERE id = (
                    SELECT id FROM jobs 
                    WHERE id = :jid AND status IN ('queued', 'running')
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING target_url, guild_id, job_type;
            """)
            result = await session.execute(stmt, {"jid": job_id})
            row = result.fetchone()
            await session.commit()
            
            if not row:
                logger.info(f"Job {job_id} could not be claimed or is already processing.")
                return False
                
            target_url, guild_id, job_type = row

        logger.info(f"Processing job {job_id} ({job_type}) for URL: {target_url}")

        async def update_progress(msg: str):
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if not job:
                    return
                job.current_stage = msg[:100]
                job.last_heartbeat = datetime.now(timezone.utc)
                
                match = re.search(r'(\d+)\s*/\s*(\d+)', msg)
                if match:
                    job.progress_current = int(match.group(1))
                    job.progress_total = int(match.group(2))
                    
                await session.commit()

        try:
            async with self.session_maker() as repo_session:
                repo = FicRepository(repo_session)
                service = IngestionService(
                    repository=repo,
                    fichub=self.fichub_adapter,
                    embedding_provider=self.embedding_provider,
                    vector_store=self.vector_store,
                )
                
                if job_type == "refresh":
                    res = await service.refresh_fic(target_url, guild_id, update_progress)
                else:
                    res = await service.ingest_fic(target_url, guild_id, update_progress)
                    
                status = "completed" if res is not False else "no_changes"

            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = status
                    job.completed_at = datetime.now(timezone.utc)
                    job.current_stage = f"Finished successfully ({status})."
                    await session.commit()
            return True
                    
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            async with self.session_maker() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = "failed"
                    job.failure_message = str(e)
                    job.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            return False
