# Ingestion Pipeline Task Tracker

This document tracks the implementation progress of the Ingestion Pipeline components defined in the `ingestion.md` specification.

## Core Adapters & Providers
- [x] **FicHubClient**: Fetch story metadata, caching URLs, and stream EPUB downloads safely.
- [x] **EmbeddingProvider**: Interface to batch text chunks and return vector embeddings (e.g., using Cloudflare AI, OpenAI, or a local ONNX runtime).
- [x] **VectorStore**: Interface to upsert vectors in batches to Qdrant Cloud.
- [x] **FicRepository**: SQLAlchemy database models to read/write canonical data (`Fic`, `FicVersion`, `Chapter`, `Paragraph`, `Chunk`) to Neon Postgres.

## Parsing & Extraction
- [x] **EpubValidator**: Validate the downloaded file is a proper ZIP archive with a readable EPUB structure (META-INF, container.xml, package doc).
- [x] **EpubParser**: Extract the reading order from the EPUB spine and filter out non-story documents (e.g., title pages, navigation documents).
- [x] **ChapterExtractor**: Sanitize HTML (remove scripts/styles/navigation), extract chapter titles, and yield clean chapter content.
- [x] **ParagraphNormalizer**: Split chapter content into `Paragraph` objects, preserving original text while generating a `normalized_text` variant for exact DB searching.
- [x] **ChunkBuilder**: Group sequential paragraphs into semantic `Chunk` objects (target ~400 words, overlapping by ~75 words) without crossing chapter boundaries.

## Orchestration & Validation
- [x] **VersionValidator**: Run sanity checks on the built version (e.g., chapter/paragraph counts are >0, chunks match vectors, word counts haven't dropped drastically).
- [x] **VersionActivator**: Atomically swap the `active_version_id` on the `Fic` record in Postgres and clean up temporary EPUB files.
- [x] **IngestionService**: The master orchestrator that ties all the above components together. It manages the state machine (`building` -> `ready` -> `active`), handles unrecoverable failures safely, and exposes the `ingest()` method for the CLI/Bot.

## Entry Points
- [x] **Discord command**: `!qf ingest <url>` (Admin cog)
