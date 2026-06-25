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
* **Pagination & Session Management**: Replaced eager-loading of all 100 pages with an asynchronous, paginated sliding-window approach backed by a `SearchSessionStore`. The bot fetches context for an initial window of results (e.g., 20) and asynchronously triggers background prefetching for adjacent windows as the user navigates, drastically reducing memory overhead and upfront database load.
* **Result Rendering**: Transitioned from ANSI code blocks to standard Discord markdown (e.g., `__**matched text**__`). This prevents code block formatting breakage on long texts and provides a cleaner look. Semantic results directly display the exact canonical chunk evaluated by the cross-encoder, ensuring no misalignment between the reranker's score and the text shown to the user.

## Semantic Search Pipeline Upgrades
The semantic search architecture (`!qs`) has been entirely redesigned and evaluated to improve recall, latency, and hard-negative discrimination:
1. **Production Configuration**: Through extensive offline benchmarking, the optimal configuration was finalized as a Dense-only K=30 retrieval pipeline using the `jinaai/jina-reranker-v1-tiny-en` cross-encoder. This provides an excellent balance of high accuracy (nDCG@10) and low latency (~4.4s P95 latency).
2. **FastEmbed Migration**: Replaced heavy `SentenceTransformers` with `fastembed` for base embeddings (BAAI/bge-small-en-v1.5) and reranking. These are offloaded to an `AsyncEmbeddingProvider` thread-executor. Models are explicitly pre-warmed during the bot's `setup_hook` to eliminate cold-start penalties on the first user query.
3. **Evaluation Framework**: Created `eval_pipeline.py` to execute offline ablation experiments across varying configurations. Evaluation fixtures utilize stable, version-resilient string matching for expected text substrings rather than relying on brittle database paragraph IDs, ensuring tests don't break when a fic is re-ingested.
4. **Post-Retrieval Chunk Merging**: Candidate paragraphs are grouped and merged into contiguous chapter-level segments prior to reranking. This avoids redundancy and prevents spamming the user with overlapping hits from the same scene.
5. **Experimental Features (Behind Flags)**: Hybrid retrieval (Reciprocal Rank Fusion with lexical Postgres search), Query Expansion, and larger cross-encoders (`BAAI/bge-reranker-base`) are fully implemented but remain disabled by default in production due to observed latency spikes and MRR degradation.
6. **Provenance Tracking**: Candidates track their sourcing (e.g., `original_dense`, `expansion_lexical`) via a `matched_by` payload field, allowing easy auditing of retrieval contributions without exposing it in the UI.
