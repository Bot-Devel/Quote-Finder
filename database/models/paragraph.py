from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base


class Paragraph(Base):
    """
    Represents one normalized paragraph.
    """

    __tablename__ = "paragraphs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    fic_id: Mapped[str] = mapped_column(String(32), index=True)
    version_id: Mapped[str] = mapped_column(String(32), index=True)
    chapter_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )

    paragraph_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)  # Original text
    normalized_text: Mapped[str] = mapped_column(
        Text
    )  # Lowercase, stripped text for substring search
    word_count: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="paragraphs")

    from sqlalchemy import Index

    __table_args__ = (
        Index("ix_paragraphs_chapter_para_num", "chapter_id", "paragraph_number"),
    )
