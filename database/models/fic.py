from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

class Fic(Base):
    """
    Represents one configured FanFiction.net story.
    """
    __tablename__ = "fics"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    
    source: Mapped[str] = mapped_column(String(50), default="fanfiction.net")
    source_story_id: Mapped[str] = mapped_column(String(50), index=True)
    source_url: Mapped[str] = mapped_column(String(255))
    
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Points to the currently active, searchable version of this fic
    active_version_id: Mapped[Optional[str]] = mapped_column(String(32), ForeignKey("fic_versions.id", use_alter=True))
    
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Refresh logic
    auto_refresh_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_interval_hours: Mapped[Optional[int]] = mapped_column(Integer, default=24)
    next_refresh_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_refresh_status: Mapped[Optional[str]] = mapped_column(String(50))
    last_refresh_error: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    versions: Mapped[List["FicVersion"]] = relationship("FicVersion", back_populates="fic", foreign_keys="[FicVersion.fic_id]")
    guilds: Mapped[List["FicGuild"]] = relationship("FicGuild", back_populates="fic")


class FicVersion(Base):
    """
    Represents one complete indexed state of a story.
    """
    __tablename__ = "fic_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    fic_id: Mapped[str] = mapped_column(String(32), ForeignKey("fics.id", ondelete="CASCADE"), index=True)
    
    epub_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(50)) # e.g., building, validating, ready, active, failed, archived
    
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)
    paragraph_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    # Embedding Metadata
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100))
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    fic: Mapped["Fic"] = relationship("Fic", back_populates="versions", foreign_keys=[fic_id])
    chapters: Mapped[List["Chapter"]] = relationship("Chapter", back_populates="version", cascade="all, delete-orphan")


class FicGuild(Base):
    """
    Association table mapping a fic to the Discord servers where it is actively searchable.
    """
    __tablename__ = "fic_guilds"
    
    fic_id: Mapped[str] = mapped_column(String(32), ForeignKey("fics.id", ondelete="CASCADE"), primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to Fic
    fic: Mapped["Fic"] = relationship("Fic", back_populates="guilds")
