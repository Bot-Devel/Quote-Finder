from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from database.models import Paragraph, Chapter


class QuoteSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_exact_ids(
        self, fic_id: str, version_id: str, normalized_query: str, limit: int
    ) -> Tuple[List[str], int]:
        stmt = (
            select(Paragraph.id)
            .where(
                Paragraph.fic_id == fic_id,
                Paragraph.version_id == version_id,
                Paragraph.normalized_text.like(f"%{normalized_query}%"),
            )
            .order_by(Paragraph.chapter_id, Paragraph.paragraph_number)
            .limit(limit)
        )

        count_stmt = (
            select(func.count())
            .select_from(Paragraph)
            .where(
                Paragraph.fic_id == fic_id,
                Paragraph.version_id == version_id,
                Paragraph.normalized_text.like(f"%{normalized_query}%"),
            )
        )
        count = await self.session.scalar(count_stmt)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), count or 0

    async def search_exact(
        self, fic_id: str, version_id: str, normalized_query: str, limit: int
    ) -> Tuple[List[Paragraph], int]:
        stmt = (
            select(Paragraph)
            .options(joinedload(Paragraph.chapter))
            .where(
                Paragraph.fic_id == fic_id,
                Paragraph.version_id == version_id,
                Paragraph.normalized_text.like(f"%{normalized_query}%"),
            )
            .order_by(Paragraph.chapter_id, Paragraph.paragraph_number)
        )

        count_stmt = (
            select(func.count())
            .select_from(Paragraph)
            .where(
                Paragraph.fic_id == fic_id,
                Paragraph.version_id == version_id,
                Paragraph.normalized_text.like(f"%{normalized_query}%"),
            )
        )
        count = await self.session.scalar(count_stmt)

        result = await self.session.execute(stmt.limit(limit))
        paragraphs = list(result.scalars().all())

        return paragraphs, count or 0

    async def get_fuzzy_candidates(
        self, fic_id: str, version_id: str, normalized_query: str, limit: int
    ) -> List[Tuple[str, str, str, int]]:
        stmt = (
            select(
                Paragraph.id,
                Paragraph.normalized_text,
                Paragraph.chapter_id,
                Paragraph.paragraph_number,
            )
            .where(Paragraph.fic_id == fic_id, Paragraph.version_id == version_id)
            .order_by(
                func.similarity(Paragraph.normalized_text, normalized_query).desc()
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.all())

    async def fetch_paragraph_context(
        self, chapter_id: str, start_paragraph: int, end_paragraph: int
    ) -> List[Paragraph]:
        stmt = (
            select(Paragraph)
            .where(
                Paragraph.chapter_id == chapter_id,
                Paragraph.paragraph_number >= start_paragraph,
                Paragraph.paragraph_number <= end_paragraph,
            )
            .order_by(Paragraph.paragraph_number)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_chapter_by_number(
        self, fic_id: str, version_id: str, chapter_number: int
    ) -> Optional[Chapter]:
        stmt = select(Chapter).where(
            Chapter.fic_id == fic_id,
            Chapter.version_id == version_id,
            Chapter.chapter_number == chapter_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chapters_by_numbers(
        self, fic_id: str, version_id: str, chapter_numbers: List[int]
    ) -> List[Chapter]:
        if not chapter_numbers:
            return []
        stmt = select(Chapter).where(
            Chapter.fic_id == fic_id,
            Chapter.version_id == version_id,
            Chapter.chapter_number.in_(chapter_numbers),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def fetch_contexts_bulk(
        self, fetch_ranges: List[Tuple[str, int, int]]
    ) -> List[Paragraph]:
        if not fetch_ranges:
            return []
        from sqlalchemy import or_, and_

        conditions = [
            and_(
                Paragraph.chapter_id == cid,
                Paragraph.paragraph_number >= start,
                Paragraph.paragraph_number <= end,
            )
            for cid, start, end in fetch_ranges
        ]
        stmt = (
            select(Paragraph)
            .where(or_(*conditions))
            .order_by(Paragraph.chapter_id, Paragraph.paragraph_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_lexical_chunks(
        self, fic_id: str, version_id: str, query: str, limit: int
    ) -> List[dict]:
        from sqlalchemy import text

        stmt = text("""
            SELECT c.id, c.chapter_id, ch.chapter_number, c.chunk_number, c.start_paragraph, c.end_paragraph,
                   ts_rank_cd(to_tsvector('english', c.normalized_text), websearch_to_tsquery('english', :query)) as rank
            FROM chunks c
            JOIN chapters ch ON c.chapter_id = ch.id
            WHERE c.fic_id = :fic_id AND c.version_id = :version_id
              AND to_tsvector('english', c.normalized_text) @@ websearch_to_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        result = await self.session.execute(
            stmt,
            {
                "fic_id": fic_id,
                "version_id": version_id,
                "query": query,
                "limit": limit,
            },
        )
        return [
            {
                "id": row.id,
                "chapter_id": row.chapter_id,
                "chapter_number": row.chapter_number,
                "chunk_number": row.chunk_number,
                "start_paragraph": row.start_paragraph,
                "end_paragraph": row.end_paragraph,
                "score": row.rank,
            }
            for row in result
        ]

    async def fetch_next_paragraphs_bulk(
        self, chapter_para_tuples: List[Tuple[str, int]]
    ) -> dict[Tuple[str, int], Paragraph]:
        """Fetches a batch of paragraphs by chapter_id and paragraph_number."""
        if not chapter_para_tuples:
            return {}

        from sqlalchemy import tuple_

        stmt = select(Paragraph).where(
            tuple_(Paragraph.chapter_id, Paragraph.paragraph_number).in_(
                chapter_para_tuples
            )
        )

        result = await self.session.execute(stmt)
        paragraphs = result.scalars().all()

        return {(p.chapter_id, p.paragraph_number): p for p in paragraphs}

    async def fetch_context_bulk(self, line_ids: List[str]) -> List[Paragraph]:
        if not line_ids:
            return []
        stmt = (
            select(Paragraph)
            .options(joinedload(Paragraph.chapter))
            .where(Paragraph.id.in_(line_ids))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
