import config
from loguru import logger
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Fic, FicVersion, FicGuild, Chapter, Paragraph, Chunk
from .models import ParsedChapter, ParsedChunk

class FicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_or_create_fic(self, source_story_id: str, title: str, author: str, source_url: str) -> Fic:
        stmt = select(Fic).where(Fic.source_story_id == source_story_id)
        result = await self.session.execute(stmt)
        fic = result.scalar_one_or_none()
        
        if not fic:
            fic_id = uuid.uuid4().hex
            fic = Fic(
                id=fic_id,
                source_story_id=source_story_id,
                title=title,
                author=author,
                source_url=source_url,
            )
            self.session.add(fic)
            await self.session.commit()
            
        return fic

    async def associate_guild(self, fic_id: str, guild_id: int) -> None:
        stmt = select(FicGuild).where(FicGuild.fic_id == fic_id, FicGuild.guild_id == guild_id)
        result = await self.session.execute(stmt)
        association = result.scalar_one_or_none()
        
        if not association:
            self.session.add(FicGuild(fic_id=fic_id, guild_id=guild_id))
            await self.session.commit()

    async def create_version(self, fic_id: str, epub_hash: str, embedding_model: str, embedding_dimensions: int) -> FicVersion:
        version_id = uuid.uuid4().hex
        version = FicVersion(
            id=version_id,
            fic_id=fic_id,
            epub_hash=epub_hash,
            status="building",
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions
        )
        self.session.add(version)
        await self.session.commit()
        return version

    async def save_parsed_data(self, version_id: str, fic_id: str, parsed_chapters: list[ParsedChapter], parsed_chunks: list[ParsedChunk]) -> None:
        """Saves all chapters, paragraphs, and chunks atomically."""
        
        chapter_count = len(parsed_chapters)
        paragraph_count = 0
        chunk_count = len(parsed_chunks)
        word_count = sum(c.word_count for c in parsed_chapters)
        
        chapter_models = {}
        pending_objects = 0
        
        for pc in parsed_chapters:
            chapter_id = uuid.uuid4().hex
            chapter = Chapter(
                id=chapter_id,
                fic_id=fic_id,
                version_id=version_id,
                chapter_number=pc.number,
                chapter_title=pc.title,
                source_document_path=pc.source_path,
                chapter_hash=pc.chapter_hash,
                word_count=pc.word_count
            )
            self.session.add(chapter)
            chapter_models[pc.number] = chapter_id
            pending_objects += 1
            
            for pp in pc.paragraphs:
                paragraph_count += 1
                para = Paragraph(
                    id=uuid.uuid4().hex,
                    fic_id=fic_id,
                    version_id=version_id,
                    chapter_id=chapter_id,
                    paragraph_number=pp.number,
                    text=pp.text,
                    normalized_text=pp.normalized_text,
                    word_count=pp.word_count
                )
                self.session.add(para)
                pending_objects += 1
                
                if pending_objects >= config.DATABASE_BATCH_SIZE:
                    await self.session.flush()
                    pending_objects = 0
                
        for pch in parsed_chunks:
            chunk = Chunk(
                id=uuid.uuid4().hex,
                fic_id=fic_id,
                version_id=version_id,
                chapter_id=chapter_models[pch.chapter_number],
                chunk_number=pch.number,
                start_paragraph=pch.start_paragraph,
                end_paragraph=pch.end_paragraph,
                text=pch.text,
                normalized_text=pch.normalized_text,
                text_hash=pch.text_hash,
                word_count=pch.word_count
            )
            self.session.add(chunk)
            pending_objects += 1
            
            if pending_objects >= config.DATABASE_BATCH_SIZE:
                await self.session.flush()
                pending_objects = 0
            
        # Update version stats
        stmt = select(FicVersion).where(FicVersion.id == version_id)
        result = await self.session.execute(stmt)
        version = result.scalar_one()
        
        version.chapter_count = chapter_count
        version.paragraph_count = paragraph_count
        version.chunk_count = chunk_count
        version.word_count = word_count
        
        await self.session.commit()

    async def activate_version(self, fic_id: str, version_id: str) -> None:
        """Atomically set the fic's active_version_id and mark the version as active."""
        # Get the fic
        stmt = select(Fic).where(Fic.id == fic_id)
        result = await self.session.execute(stmt)
        fic = result.scalar_one()
        
        # Get the version
        v_stmt = select(FicVersion).where(FicVersion.id == version_id)
        v_result = await self.session.execute(v_stmt)
        version = v_result.scalar_one()
        
        fic.active_version_id = version.id
        fic.chapter_count = version.chapter_count
        version.status = "active"
        
        from sqlalchemy.sql import func
        version.activated_at = func.now()
        
        await self.session.commit()
        logger.info(f"Activated version {version_id} for fic {fic_id}")

    async def delete_version(self, version_id: str) -> None:
        """Deletes a version and relies on Postgres ON DELETE CASCADE to wipe children."""
        stmt = select(FicVersion).where(FicVersion.id == version_id)
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()
        if version:
            await self.session.delete(version)
            await self.session.commit()
            logger.info(f"Deleted version {version_id} and all its cascading children.")
