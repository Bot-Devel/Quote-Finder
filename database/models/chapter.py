from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

class Chapter(Base):
    """
    Represents one chapter in a fic version.
    """
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    fic_id: Mapped[str] = mapped_column(String(32), index=True)
    version_id: Mapped[str] = mapped_column(String(32), ForeignKey("fic_versions.id", ondelete="CASCADE"), index=True)
    
    chapter_number: Mapped[int] = mapped_column(Integer)
    chapter_title: Mapped[Optional[str]] = mapped_column(String(255))
    source_document_path: Mapped[str] = mapped_column(String(255))
    
    chapter_hash: Mapped[str] = mapped_column(String(64))
    word_count: Mapped[int] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    version: Mapped["FicVersion"] = relationship("FicVersion", back_populates="chapters")
    paragraphs: Mapped[List["Paragraph"]] = relationship("Paragraph", back_populates="chapter", cascade="all, delete-orphan")
