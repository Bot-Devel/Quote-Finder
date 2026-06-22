import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fic_id: Mapped[str] = mapped_column(String(36), ForeignKey("fics.id", ondelete="CASCADE"), nullable=True)
    
    job_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "ingest", "refresh"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued") # queued, running, completed, failed, stale
    
    current_stage: Mapped[str] = mapped_column(String(100), nullable=True)
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    
    failure_stage: Mapped[str] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    target_url: Mapped[str] = mapped_column(String, nullable=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=True) 
