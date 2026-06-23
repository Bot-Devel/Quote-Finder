import os
import asyncio
from pathlib import Path
from loguru import logger

from adapters.fichub import FicHub
from .repository import FicRepository
from .embedding import EmbeddingProvider
from .vector import VectorStore
from .validator import EpubValidator
from .parser import EpubParser, ChunkBuilder
import config
from database.models import FicVersion
from sqlalchemy import select

class IngestionService:
    def __init__(
        self,
        repository: FicRepository,
        fichub: FicHub,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        temp_dir: str = config.INGESTION_TEMP_DIR
    ):
        self.repo = repository
        self.fichub = fichub
        self.embedding = embedding_provider
        self.vector_store = vector_store
        self.temp_dir = Path(temp_dir)
        
        self.validator = EpubValidator()
        self.parser = EpubParser()
        self.chunk_builder = ChunkBuilder()
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_fic(self, source_url: str, guild_id: int, progress_callback=None) -> None:
        async def report(msg: str):
            logger.info(msg)
            if progress_callback:
                try:
                    await progress_callback(msg)
                except Exception as e:
                    logger.debug(f"Failed to update progress callback: {e}")

        await report(f"Starting ingestion for {source_url} (Guild: {guild_id})")
        
        # 1. Fetch metadata
        await asyncio.to_thread(self.fichub.get_fic_metadata, source_url)
        if not hasattr(self.fichub, "response") or "meta" not in self.fichub.response:
            raise ValueError(f"Failed to fetch metadata for {source_url}")
            
        meta = self.fichub.response["meta"]
        epub_hash = self.fichub.response["hashes"]["epub"]
        
        source_story_id = str(meta["rawExtendedMeta"]["id"])
        title = meta["title"]
        author = meta["author"]
        
        # 2. Sync Fic & Guild
        fic = await self.repo.get_or_create_fic(source_story_id, title, author, source_url)
        await self.repo.associate_guild(fic.id, guild_id)
        
        # 3. Create Version
        version = await self.repo.create_version(
            fic.id, 
            epub_hash,
            self.embedding.model_name,
            self.embedding.dimensions
        )
        
        epub_path = None
        try:
            # 4. Download EPUB
            download_url = "https://fichub.net" + self.fichub.response["urls"]["epub"]
            epub_path = self.temp_dir / f"{version.id}.epub"
            
            await report(f"Downloading EPUB for **{title}**...")
            await asyncio.to_thread(self.fichub.get_fic_data, download_url)
            with open(epub_path, "wb") as f:
                f.write(self.fichub.response_data.content)
            
            # 5. Validate
            await asyncio.to_thread(self.validator.validate, epub_path)
            
            # 6. Parse
            await report("Parsing EPUB chapters...")
            chapters = await asyncio.to_thread(self.parser.parse, epub_path)
            
            # 7. Chunking
            await report("Building semantic chunks...")
            def _build_chunks():
                chunks_out = []
                for ch in chapters:
                    chs = self.chunk_builder.build_chunks(ch.number, ch.paragraphs, (ch.number * 10000) + 1)
                    chunks_out.extend(chs)
                return chunks_out
                
            all_chunks = await asyncio.to_thread(_build_chunks)
                
            # 8. Embedding
            await report(f"Generating vectors for {len(all_chunks)} chunks (This will take a while)...")
            chunk_texts = [c.text for c in all_chunks]
            
            async def embed_progress(current, total):
                await report(f"Generating vectors: {current}/{total} chunks embedded...")
                
            embeddings = await self.embedding.embed_documents(chunk_texts, progress_callback=embed_progress)
            
            # 9. Vector Store
            await report("Upserting vectors to Qdrant Cloud...")
            await self.vector_store.create_collection_if_not_exists(self.embedding.dimensions)
            await self.vector_store.upsert_chunks(fic.id, version.id, all_chunks, embeddings)
            
            # 10. Save to DB
            await report("Saving chunks and paragraphs to Neon Postgres...")
            await self.repo.save_parsed_data(version.id, fic.id, chapters, all_chunks)
            
            # 11. Activate
            await report("Activating version...")
            old_version_id = fic.active_version_id
            await self.repo.activate_version(fic.id, version.id)
            
            # 12. Cleanup Old Version
            if old_version_id and old_version_id != version.id:
                await report("Cleaning up old version from Qdrant and Postgres...")
                await self.vector_store.delete_version(old_version_id)
                await self.repo.delete_version(old_version_id)
            
            await report(f"Ingestion completed successfully for {title}!")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise
        finally:
            if not config.INGESTION_KEEP_FAILED_DATA:
                if epub_path and epub_path.exists():
                    epub_path.unlink()
                    logger.debug(f"Cleaned up temp file {epub_path}")
            else:
                logger.warning(f"Keeping temp file due to config: {epub_path}")

    async def refresh_fic(self, source_url: str, guild_id: int, progress_callback=None) -> bool:
        async def report(msg: str):
            logger.info(msg)
            if progress_callback:
                try: await progress_callback(msg)
                except Exception: pass

        await report(f"Starting differential refresh for {source_url}...")
        
        # 1. Fetch metadata
        await asyncio.to_thread(self.fichub.get_fic_metadata, source_url)
        if not hasattr(self.fichub, "response") or "meta" not in self.fichub.response:
            raise ValueError("Failed to fetch metadata")
            
        meta = self.fichub.response["meta"]
        source_story_id = str(meta["rawExtendedMeta"]["id"])
        new_epub_hash = meta["hashes"]["epub"]
        
        fic = await self.repo.get_or_create_fic(source_story_id, meta["title"], meta["author"], source_url)
        await self.repo.associate_guild(fic.id, guild_id)
        
        if not fic.active_version_id:
            await report("No active version found. Redirecting to full rebuild...")
            return await self.ingest_fic(source_url, guild_id, progress_callback)
            
        # Early exit check using FicHub hash
        stmt = select(FicVersion).where(FicVersion.id == fic.active_version_id)
        active_version = (await self.repo.session.execute(stmt)).scalar_one()
        if active_version.epub_hash == new_epub_hash:
            await report("EPUB hash matches active version. No changes detected.")
            await self.repo.touch_fic(fic.id)
            return False
            
        # 2. Download
        download_url = "https://fichub.net" + self.fichub.response["urls"]["epub"]
        epub_path = self.temp_dir / f"refresh_{fic.id}.epub"
        
        try:
            await report("Downloading EPUB for delta comparison...")
            await asyncio.to_thread(self.fichub.get_fic_data, download_url)
            with open(epub_path, "wb") as f:
                f.write(self.fichub.response_data.content)
            
            await asyncio.to_thread(self.validator.validate, epub_path)
            
            # 3. Parse and Compare
            await report("Parsing and hashing chapters...")
            chapters = await asyncio.to_thread(self.parser.parse, epub_path)
            
            old_hashes = await self.repo.get_chapter_hashes(fic.active_version_id)
            changed_chapters = []
            
            for ch in chapters:
                if ch.number not in old_hashes or old_hashes[ch.number] != ch.chapter_hash:
                    changed_chapters.append(ch)
                    
            if not changed_chapters:
                await report("No changes detected. Refresh complete.")
                await self.repo.touch_fic(fic.id)
                return False
                
            await report(f"Detected {len(changed_chapters)} changed/new chapters. Generating chunks...")
            
            # Delete old versions of changed chapters
            await report("Deleting old vectors for modified chapters...")
            changed_nums = [c.number for c in changed_chapters]
            await self.vector_store.delete_chapters(fic.active_version_id, changed_nums)
            await self.repo.delete_chapters(fic.active_version_id, changed_nums)
            
            def _build_changed_chunks():
                chunks_out = []
                for ch in changed_chapters:
                    chs = self.chunk_builder.build_chunks(ch.number, ch.paragraphs, (ch.number * 10000) + 1)
                    chunks_out.extend(chs)
                return chunks_out
                
            all_chunks = await asyncio.to_thread(_build_changed_chunks)
            
            if all_chunks:
                await report(f"Generating embeddings for {len(all_chunks)} new chunks...")
                chunk_texts = [c.text for c in all_chunks]
                async def embed_progress(curr, tot):
                    await report(f"Embedding: {curr}/{tot} chunks...")
                embeddings = await self.embedding.embed_documents(chunk_texts, progress_callback=embed_progress)
                
                await report("Upserting vectors...")
                await self.vector_store.upsert_chunks(fic.id, fic.active_version_id, all_chunks, embeddings)
                
                await report("Saving new chunks to database...")
                await self.repo.save_parsed_data(fic.active_version_id, fic.id, changed_chapters, all_chunks)
                
            # Update the active version's epub hash to the new one so we don't trigger again
            active_version.epub_hash = new_epub_hash
            await self.repo.session.commit()
            
            await self.repo.touch_fic(fic.id)
            await report("Differential refresh completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
            raise
        finally:
            if not config.INGESTION_KEEP_FAILED_DATA:
                if epub_path and epub_path.exists():
                    epub_path.unlink()
                    logger.debug(f"Cleaned up temp file {epub_path}")
