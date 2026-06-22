import os
from pathlib import Path
from loguru import logger

from adapters.fichub import FicHub
from .repository import FicRepository
from .embedding import EmbeddingProvider
from .vector import VectorStore
from .validator import EpubValidator
from .parser import EpubParser, ChunkBuilder
import config

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
        self.fichub.get_fic_metadata(source_url)
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
            self.fichub.get_fic_data(download_url)
            with open(epub_path, "wb") as f:
                f.write(self.fichub.response_data.content)
            
            # 5. Validate
            self.validator.validate(epub_path)
            
            # 6. Parse
            await report("Parsing EPUB chapters...")
            chapters = self.parser.parse(epub_path)
            
            # 7. Chunking
            await report("Building semantic chunks...")
            all_chunks = []
            chunk_num = 1
            for ch in chapters:
                chunks = self.chunk_builder.build_chunks(ch.number, ch.paragraphs, chunk_num)
                all_chunks.extend(chunks)
                chunk_num += len(chunks)
                
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
