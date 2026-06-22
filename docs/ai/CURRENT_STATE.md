# Quote Finder V2 - Current State

## Architecture Overview
Quote Finder is a Discord bot designed to ingest fanfictions (e.g., from FicHub/FFN) and provide lightning-fast, highly accurate quote searching.
* **Discord Framework**: `discord.py` (via `commands.Cog`)
* **Database**: Neon Postgres (via `SQLAlchemy` + `Alembic`)
* **Vector Store**: Qdrant / Redis (for semantic embeddings)
* **Logging**: `loguru` (Console tracking of search pipeline durations)

## Available Search Modes
* **Exact Search** (`!qe`, `!qfe`, `!qf exact`): Literal substring matching against normalized paragraph text.
* **Fuzzy Search** (`!qff`, `!qf fuzzy`): Levenshtein-distance lexical searching using `RapidFuzz` to catch typos.
* **Semantic Search** (`!qs`, `!qfs`, `!qf semantic`): Vector-based embedding search for finding scenes based on abstract concepts.

## Data Model & Ingestion
* **Guild Scoping**: Fics are bound to specific Discord servers. Admins use `!qf connect <source_story_id> <guild_id>`. (UUID lookups were removed in favor of source IDs).
* **Versioning**: The system supports multiple ingested versions of a fic. The `Fic` table acts as the root, pointing to an `active_version_id` (`FicVersion`).
* **Chapter Counts**: `chapter_count` has been promoted to the root `Fic` table. When `activate_version()` runs in the ingestion pipeline, it automatically syncs the chapter count from the new `FicVersion` to the root `Fic`.

## Recent Performance Upgrades (The 50ms Search)
The V1 architecture suffered from 15-20 second delays during exact and fuzzy searches. V2 resolved this entirely, dropping search times to ~50ms.
1. **N+1 Query Elimination**: The old system iterated over 100 search results and fired 100 sequential SQL queries to fetch the following context paragraph. This was replaced with a single `fetch_next_paragraphs_bulk` method that uses a `tuple_ IN` clause to fetch all contexts simultaneously.
2. **Postgres GIN Trigram Indices**: Added a `pg_trgm` index on `paragraphs.normalized_text gin_trgm_ops` to make substring matching (`LIKE '%...%'`) instant instead of requiring a full sequential table scan.
3. **Composite Indices**: Added a B-Tree composite index on `paragraphs (chapter_id, paragraph_number)` to ensure the new bulk context fetch query executes instantly.
4. **Subquery Count Fix**: The SQLAlchemy `count()` query for exact searches was previously wrapping the entire `SELECT` (including `JOIN chapters` and `ORDER BY`). This was decoupled into a clean, standalone count statement to avoid forcing Postgres to join and sort rows in memory just to return an integer count.

## UI / Discord Presentation
* **Pagination**: Eagerly loaded. We strictly bound our search results to `limit=100`. Because bulk DB context fetching takes <20ms and Python string formatting takes <2ms, we eagerly format all 100 pages up front. This avoids the need for lazy loading and makes Discord pagination button clicks perfectly instant.
* **ANSI Highlighting**: `PaginationView` renders results using `discord.Embed` alongside ANSI code blocks. The matched text paragraph is colored bright green (`\u001b[0;32m`), while the preceding and following context paragraphs are colored dark gray (`\u001b[0;30m`) to ensure the exact matched quote instantly pops out visually.
