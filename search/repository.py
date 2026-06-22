from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from database.models import Paragraph, Chapter, Chunk

class QuoteSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_exact(self, fic_id: str, version_id: str, normalized_query: str, limit: int) -> Tuple[List[Paragraph], int]:
        stmt = select(Paragraph).options(joinedload(Paragraph.chapter)).where(
            Paragraph.fic_id == fic_id,
            Paragraph.version_id == version_id,
            Paragraph.normalized_text.like(f"%{normalized_query}%")
        ).order_by(
            Paragraph.chapter_id,
            Paragraph.paragraph_number
        )
        
        # We need total count
        count_stmt = select(func.count()).select_from(Paragraph).where(
            Paragraph.fic_id == fic_id,
            Paragraph.version_id == version_id,
            Paragraph.normalized_text.like(f"%{normalized_query}%")
        )
        count = await self.session.scalar(count_stmt)
        
        result = await self.session.execute(stmt.limit(limit))
        paragraphs = list(result.scalars().all())
        
        return paragraphs, count or 0

    async def get_fuzzy_candidates(self, fic_id: str, version_id: str, normalized_query: str, limit: int) -> List[Paragraph]:
        stmt = select(Paragraph).options(joinedload(Paragraph.chapter)).where(
            Paragraph.fic_id == fic_id,
            Paragraph.version_id == version_id
        ).order_by(
            func.similarity(Paragraph.normalized_text, normalized_query).desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def fetch_paragraph_context(self, chapter_id: str, start_paragraph: int, end_paragraph: int) -> List[Paragraph]:
        stmt = select(Paragraph).where(
            Paragraph.chapter_id == chapter_id,
            Paragraph.paragraph_number >= start_paragraph,
            Paragraph.paragraph_number <= end_paragraph
        ).order_by(Paragraph.paragraph_number)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_chapter_by_number(self, fic_id: str, version_id: str, chapter_number: int) -> Optional[Chapter]:
        stmt = select(Chapter).where(
            Chapter.fic_id == fic_id,
            Chapter.version_id == version_id,
            Chapter.chapter_number == chapter_number
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def fetch_next_paragraphs_bulk(self, chapter_para_tuples: List[Tuple[str, int]]) -> dict[Tuple[str, int], Paragraph]:
        """Fetches a batch of paragraphs by chapter_id and paragraph_number."""
        if not chapter_para_tuples:
            return {}
            
        from sqlalchemy import tuple_
        stmt = select(Paragraph).where(
            tuple_(Paragraph.chapter_id, Paragraph.paragraph_number).in_(chapter_para_tuples)
        )
        
        result = await self.session.execute(stmt)
        paragraphs = result.scalars().all()
        
        return {(p.chapter_id, p.paragraph_number): p for p in paragraphs}
