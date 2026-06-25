# Quote Finder Revamp Architecture

## 1. Purpose

This document defines the target architecture for the Quote Finder bot revamp.

The current bot searches text extracted from a FanFiction.net story and returns matching lines with pagination. The bot is several years old, depends on brittle ebook-processing assumptions, requires manual data updates, and no longer reliably processes newer ebook files.

The revamp will preserve the existing quote-search and pagination experience while introducing:

* reliable EPUB ingestion through FicHub
* support for multiple FanFiction.net stories
* exact quote search
* keyword search
* vague scene search using semantic embeddings
* automated story refreshes
* versioned and atomic data replacement
* separation between ingestion, retrieval, and Discord interaction

The system is primarily a retrieval application, not a generative chatbot.

It must return passages written in the source story and must not invent or rewrite story content.

---

## 2. Goals

The revamp must:

1. Restore reliable exact quote search.
2. Support vague scene descriptions through semantic retrieval.
3. Support multiple FanFiction.net stories.
4. Fetch story EPUB files through FicHub.
5. Parse chapters using EPUB reading order rather than chapter-title formatting.
6. Preserve chapter numbers, chapter titles, paragraphs, and surrounding context.
7. Store canonical text separately from vector indexes.
8. Allow stories to be refreshed without taking search offline.
9. Reuse the existing Discord pagination system where practical.
10. Keep production runtime resource usage low.
11. Avoid paid services where possible.
12. Allow embedding providers and storage providers to be replaced later.

---

## 3. Non-goals

The first version will not:

* generate answers using an LLM
* summarize chapters
* answer broad literary-analysis questions
* rewrite retrieved passages
* support arbitrary websites outside the configured story sources
* provide a web dashboard
* perform cross-story semantic search by default
* perform chapter-level incremental refreshes
* rerank semantic results with a separate cross-encoder
* automatically resolve ambiguous story names using AI

These may be considered later.

---

## 4. Current System

The existing system:

* runs as a Python Discord bot
* runs as a `systemd` service
* searches locally processed story data
* supports pagination
* returns a matching line and nearby text
* depends on EPUB or text-processing logic written several years ago
* previously used FanFicFare for story downloads
* requires manual story updates
* assumes chapter metadata in a format that may no longer be stable
* fails to pick up newer ebook updates reliably

The main failure is not the Discord interface.

The fragile part is the ingestion and normalization layer.

---

## 5. Target System Overview

The target system consists of four major parts:

1. Discord bot
2. ingestion pipeline
3. relational text store
4. semantic vector store

```text
FanFiction.net story
        ↓
      FicHub
        ↓
 Temporary EPUB download
        ↓
 Ingestion and normalization
        ↓
 ┌─────────────────────────────┐
 │                             │
 │ Neon Postgres               │
 │ - stories                   │
 │ - versions                  │
 │ - chapters                  │
 │ - paragraphs                │
 │ - chunks                    │
 │ - exact/full-text search    │
 │                             │
 └─────────────────────────────┘
        ↓
 Embedding generation
        ↓
 ┌─────────────────────────────┐
 │                             │
 │ Qdrant Cloud                │
 │ - chunk vectors             │
 │ - vector metadata           │
 │ - semantic retrieval        │
 │                             │
 └─────────────────────────────┘

Discord bot
    ├── exact quote search → Neon
    ├── keyword search → Neon
    └── vague scene search
          ├── embedding provider
          ├── Qdrant
          └── Neon context fetch
```

---

## 6. Core Architectural Principles

### 6.1 Canonical text lives in Postgres

Neon Postgres is the source of truth for:

* story metadata
* story versions
* chapters
* paragraph text
* semantic chunk boundaries
* refresh state
* guild and channel configuration

Qdrant is not the canonical text store.

Qdrant contains vector indexes and enough metadata to resolve a result back to Postgres.

---

### 6.2 Exact search and semantic search are separate

Exact quote search and vague scene search solve different problems.

Exact quote search must use source text directly.

Semantic search must use embeddings.

The system must not rely on vector similarity for exact quotes.

```text
Exact words
→ normalized substring search
→ Postgres

Keywords
→ Postgres full-text search

Vague scene description
→ query embedding
→ Qdrant similarity search
→ Postgres passage retrieval
```

---

### 6.3 Search results must always resolve to source text

Every returned result must contain text retrieved from the canonical database.

Semantic results must never return generated or reconstructed prose.

The result must reference:

* story
* version
* chapter
* paragraph or chunk range
* source text
* surrounding context

---

### 6.4 EPUB files are temporary inputs

EPUB files are only used during ingestion.

After a version has been:

* downloaded
* parsed
* normalized
* embedded
* validated
* activated

the temporary EPUB may be deleted.

The stored canonical representation is the normalized chapter, paragraph, and chunk data.

---

### 6.5 Chapter numbering comes from EPUB order

The ingestion system must not depend on chapter titles containing chapter numbers.

Chapter numbers are assigned from the EPUB spine or validated reading order.

Example:

```text
EPUB reading order:
1. Introduction
2. The Arrival
3. The Battle
```

Stored data:

```json
[
  {
    "chapter_number": 1,
    "chapter_title": "Introduction"
  },
  {
    "chapter_number": 2,
    "chapter_title": "The Arrival"
  },
  {
    "chapter_number": 3,
    "chapter_title": "The Battle"
  }
]
```

Chapter title and chapter number are separate fields.

---

### 6.6 Refreshes are versioned and atomic

A story refresh must never delete the active version before the replacement is complete.

New versions are built alongside the current version.

```text
Active version: v3
Building version: v4
```

After validation:

```text
active_version_id = v4
```

Old versions are deleted later by cleanup.

This provides:

* uninterrupted search
* rollback capability
* protection from malformed EPUB files
* protection from partial Neon or Qdrant writes

---

### 6.7 External providers must be replaceable

Embedding generation must be hidden behind a provider interface.

Possible providers include:

* Cloudflare Workers AI
* Modal
* local ONNX Runtime
* another compatible embedding API

The bot and ingestion code must not depend directly on one provider implementation.

Example interface:

```python
from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...

    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...
```

The same embedding model and vector dimensions must be used for document and query embeddings.

---

## 7. Main Components

## 7.1 Discord Bot

The Discord bot is responsible for:

* receiving commands
* resolving the selected story
* validating user input
* calling the search service
* formatting results
* reusing the existing pagination system
* displaying refresh and story information
* enforcing permissions for administrative commands

The Discord layer must not:

* parse EPUB files
* perform batch embedding
* rebuild story data
* directly manipulate raw database tables
* contain provider-specific search logic

---

## 7.2 Search Service

The search service exposes a common interface for exact and semantic retrieval.

Example:

```python
class QuoteSearchService:
    async def search_exact(
        self,
        fic_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> SearchPage:
        ...

    async def search_scene(
        self,
        fic_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> SearchPage:
        ...
```

Both search types return a shared result model.

```python
from dataclasses import dataclass
from typing import Literal


@dataclass
class SearchResult:
    fic_id: str
    version_id: str
    chapter_id: str
    chapter_number: int
    chapter_title: str | None
    matched_text: str
    context_before: str | None
    context_after: str | None
    result_type: Literal["exact", "keyword", "semantic"]
    score: float | None
```

---

## 7.3 Ingestion Service

The ingestion service is responsible for:

* accepting a FanFiction.net story identifier or URL
* downloading the latest EPUB through FicHub
* validating the downloaded file
* parsing EPUB reading order
* detecting story documents
* assigning chapter numbers
* extracting paragraphs
* normalizing text
* creating semantic chunks
* generating embeddings
* writing data to Neon
* writing vectors to Qdrant
* validating the new version
* activating the new version
* deleting temporary files

The ingestion service must support manual execution before automated refresh is introduced.

Example:

```bash
quote-finder ingest \
  --url "https://www.fanfiction.net/s/1234567/1/Story" \
  --activate
```

---

## 7.4 Refresh Worker

The refresh worker is responsible for:

* selecting stories eligible for refresh
* locking or claiming refresh jobs
* downloading the latest EPUB
* comparing the EPUB hash with the active version
* skipping unchanged stories
* creating a new version when changed
* calling the ingestion service
* recording success or failure
* scheduling the next refresh
* recovering stale jobs
* triggering cleanup of old versions

Refresh scheduling is based on database state.

Suggested fields include:

```text
auto_refresh_enabled
refresh_interval_hours
next_refresh_at
last_checked_at
last_refreshed_at
last_refresh_status
last_refresh_error
refresh_started_at
```

---

## 7.5 Neon Postgres

Neon stores structured and canonical application data.

Expected logical tables:

```text
fics
fic_versions
chapters
paragraphs
chunks
guild_settings
channel_settings
refresh_jobs
```

Neon handles:

* relational integrity
* exact substring search
* full-text keyword search
* chapter and paragraph lookup
* active-version switching
* refresh state
* story selection settings

---

## 7.6 Qdrant Cloud

Qdrant stores semantic vectors for chunks.

Each point must contain:

* stable point ID
* embedding vector
* fic ID
* version ID
* chapter ID
* chunk ID
* paragraph range
* optional chapter number

Example payload:

```json
{
  "fic_id": "ffn_1234567",
  "version_id": "01JABCDEF123",
  "chapter_id": "01JCHAPTER123",
  "chunk_id": "01JCHUNK123",
  "chapter_number": 42,
  "start_paragraph": 81,
  "end_paragraph": 89
}
```

Semantic queries must filter by:

```text
fic_id
version_id
```

The active version is resolved from Neon before querying Qdrant.

---

## 8. Data Model Overview

## 8.1 Fic

Represents one configured FanFiction.net story scoped to a specific Discord server.

Suggested fields:

```text
id
source
source_story_id
source_url
title
author
active_version_id
auto_refresh_enabled
refresh_interval_hours
next_refresh_at
last_checked_at
last_refreshed_at
last_refresh_status
last_refresh_error
created_at
updated_at
```

`source_story_id` should contain the FanFiction.net numeric story ID.

Example:

```text
1234567
```

---

## 8.2 Fic Version

Represents one complete indexed state of a story.

Suggested fields:

```text
id
fic_id
epub_hash
status
chapter_count
paragraph_count
chunk_count
word_count
created_at
validated_at
activated_at
failed_at
failure_reason
```

Possible statuses:

```text
building
validating
ready
active
failed
archived
```

Only one version may be active for a fic.

---

## 8.3 Chapter

Represents one chapter in a fic version.

Suggested fields:

```text
id
fic_id
version_id
chapter_number
chapter_title
source_document_path
chapter_hash
word_count
created_at
```

Constraints:

* chapter number must be unique within a version
* chapter number must be positive
* chapter text must not cross fic versions

---

## 8.4 Paragraph

Represents one normalized paragraph.

Suggested fields:

```text
id
fic_id
version_id
chapter_id
paragraph_number
text
normalized_text
word_count
created_at
```

Paragraph order must be stable within a chapter.

---

## 8.5 Chunk

Represents one semantic-search unit.

Suggested fields:

```text
id
fic_id
version_id
chapter_id
chunk_number
start_paragraph
end_paragraph
text
text_hash
word_count
embedding_model
embedding_dimensions
created_at
```

Chunks must:

* remain within one chapter
* preserve paragraph boundaries
* overlap neighbouring chunks
* resolve back to paragraph ranges

---

## 9. Search Modes

## 9.1 Exact Quote Search

Exact quote search is used when the user remembers literal wording.

Example:

```text
!quote there are no innocent men
```

The search flow is:

```text
query
→ normalize query
→ search normalized paragraph text
→ rank literal matches
→ fetch surrounding paragraphs
→ return paginated results
```

Normalization may include:

* Unicode normalization
* case folding
* whitespace collapsing
* curly quote normalization
* apostrophe normalization
* dash normalization

The original source text must be shown in results.

---

## 9.2 Keyword Search

Keyword search is used when the user remembers several words but not the exact phrase.

It may use PostgreSQL full-text search.

Example:

```text
Harry hospital argument Dumbledore
```

Keyword search may later be exposed through:

```text
!find
```

or used as a fallback inside `!quote`.

The exact behaviour will be defined in the search specification.

---

## 9.3 Semantic Scene Search

Semantic search is used when the user remembers the meaning of a scene.

Example:

```text
!scene Harry acts calm until everyone leaves and then collapses
```

The search flow is:

```text
query
→ embedding provider
→ query vector
→ Qdrant search
→ filter by fic and active version
→ retrieve top chunk IDs
→ fetch source text from Neon
→ expand surrounding paragraphs
→ return paginated results
```

Semantic search must return multiple candidates because vague memories may match several scenes.

---

## 10. Story Selection

The system must support multiple fics.

A fic can be scoped to multiple Discord servers via a many-to-many relationship (`fic_guilds`). A query must resolve one active fic associated with the current server before searching. Cross-server search is not permitted for servers that haven't explicitly added the fic.

Suggested resolution order:

1. explicit fic argument (must belong to the server)
2. channel default fic
3. guild default fic
4. request that the user select a fic from the server's available fics

Suggested commands:

```text
!fic add <fanfiction.net-url>
!fic list
!fic select <fic-id>
!fic info
!fic refresh <fic-id>

!quote <text>
!scene <description>
```

The exact command syntax will be defined in the Discord specification.

---

## 11. Version Activation

Version activation is the boundary between ingestion and production search.

A version may only be activated after validation succeeds.

Minimum validation:

* EPUB parsed successfully
* at least one chapter exists
* chapter numbers are unique
* paragraph count is greater than zero
* chunk count is greater than zero
* expected Qdrant vector count exists
* first and last chapters contain content
* word count is within a sensible range
* source story ID matches the expected fic

Activation must update the fic atomically:

```sql
UPDATE fics
SET active_version_id = :new_version_id,
    last_refreshed_at = NOW(),
    last_refresh_status = 'success'
WHERE id = :fic_id;
```

The previous version remains available until cleanup.

---

## 12. Failure Handling

The active version must remain searchable when:

* FicHub is unavailable
* EPUB download fails
* EPUB parsing fails
* embedding generation fails
* Neon write fails
* Qdrant write fails
* validation fails
* worker crashes
* refresh times out

Failed versions must be marked as failed.

Suggested stored information:

```text
failure_stage
failure_reason
failed_at
retry_count
```

Temporary data from failed versions may be cleaned asynchronously.

---

## 13. Provider Boundaries

External services must be wrapped behind internal adapters.

Suggested interfaces:

```text
FicHubClient
EmbeddingProvider
VectorStore
FicRepository
RefreshRepository
```

Example:

```python
class VectorStore:
    async def upsert_chunks(
        self,
        points: list["VectorPoint"],
    ) -> None:
        ...

    async def search(
        self,
        vector: list[float],
        fic_id: str,
        version_id: str,
        limit: int,
    ) -> list["VectorMatch"]:
        ...

    async def delete_version(
        self,
        fic_id: str,
        version_id: str,
    ) -> None:
        ...
```

This prevents Discord command handlers from depending directly on Qdrant or Neon clients.

---

## 14. Deployment Architecture

The expected production deployment is:

```text
Netcup VPS
├── Discord bot
├── refresh worker or scheduled CLI
├── application configuration
└── optional local embedding runtime

External services
├── Neon Postgres
├── Qdrant Cloud
├── FicHub
└── optional remote embedding provider
```

The initial deployment may continue using:

* Python virtual environments
* `systemd`
* separate services

Docker Compose may be introduced after the migration is stable.

The first production release must not depend on Docker.

---

## 15. Security

The system must:

* store secrets outside source control
* use environment variables or protected environment files
* use TLS for Neon and Qdrant connections
* restrict administrative Discord commands
* validate FanFiction.net URLs
* validate FicHub responses
* avoid rendering arbitrary HTML from EPUB files
* never execute ebook content
* limit query length
* limit refresh concurrency
* avoid logging Discord tokens or database credentials

Required secrets may include:

```text
DISCORD_TOKEN
DATABASE_URL
QDRANT_URL
QDRANT_API_KEY
EMBEDDING_API_KEY
```

---

## 16. Observability

The system must log:

* fic ID
* version ID
* refresh job ID
* ingestion stage
* chapter count
* paragraph count
* chunk count
* embedding count
* duration
* search type
* search duration
* result count
* provider errors

Logs must not include:

* full user queries by default, unless intentionally enabled
* full story passages
* secrets
* connection strings

Basic health information should include:

```text
Discord connection status
Neon connectivity
Qdrant connectivity
embedding provider connectivity
last successful refresh
last failed refresh
```

---

## 17. Performance Expectations

For the initial large story:

* approximately 1.5 million words
* approximately 180 chapters
* approximately 4,000 to 8,000 semantic chunks

Expected user-facing performance:

```text
Exact quote search:
under 1 second in normal conditions

Semantic scene search:
under 3 seconds in normal conditions

Pagination:
under 1 second after results are available
```

The system is not expected to support high request volume.

Correctness and reliability are more important than extreme throughput.

---

## 18. Rollout Plan

### Phase 1: Core ingestion and exact search

Deliver:

* FicHub EPUB download
* EPUB parsing
* chapter and paragraph normalization
* Neon schema
* literal quote search
* keyword search
* existing pagination integration
* multiple-fic storage

Semantic search is not required for this phase.

---

### Phase 2: Semantic scene search

Deliver:

* chunk generation
* embedding provider
* Qdrant collection
* document embedding upload
* query embedding
* `!scene` retrieval
* context expansion

---

### Phase 3: Refresh automation

Deliver:

* refresh database state
* scheduled worker
* EPUB hash comparison
* versioned re-ingestion
* atomic activation
* retry handling
* stale-job recovery
* old-version cleanup

---

### Phase 4: Deployment and migration

Deliver:

* Netcup deployment
* service configuration
* environment setup
* production database configuration
* production Qdrant configuration
* DigitalOcean cutover
* rollback procedure

---

### Phase 5: Optional improvements

Possible future work:

* chapter-level incremental refresh
* semantic reranking
* hybrid search command
* global cross-fic search
* user feedback on results
* admin dashboard
* automatic model migration
* scheduled CI-based ingestion
* story update notifications

---

## 19. Acceptance Criteria

The architecture is considered successfully implemented when:

1. A FanFiction.net URL can be ingested through FicHub.
2. Chapters are numbered correctly without relying on title text.
3. Exact queries return matching source passages.
4. Vague scene queries return relevant semantic candidates.
5. Multiple stories can coexist.
6. Every search is scoped to the selected fic and active version.
7. Refreshing a fic does not interrupt active search.
8. A failed refresh does not delete or replace the current version.
9. Discord pagination works for both exact and semantic results.
10. Temporary EPUB files are deleted after successful or failed processing.
11. Canonical text remains in Neon.
12. Qdrant vectors can be rebuilt from canonical source data.
13. The embedding provider can be replaced without rewriting command handlers.
14. The bot does not generate or invent story text.

---

## 20. Architectural Decision Summary

| Decision             | Choice                         |
| -------------------- | ------------------------------ |
| Story source         | FicHub EPUB                    |
| Canonical text store | Neon Postgres                  |
| Vector store         | Qdrant Cloud                   |
| Exact search         | Normalized substring search    |
| Keyword search       | PostgreSQL full-text search    |
| Vague scene search   | Embedding similarity           |
| Chapter numbering    | EPUB reading order             |
| Refresh strategy     | Full version rebuild initially |
| Activation strategy  | Atomic active-version switch   |
| Old version deletion | Deferred cleanup               |
| EPUB retention       | Temporary only                 |
| Multiple stories     | Supported                      |
| Pagination           | Reuse existing implementation  |
| Answer generation    | Not supported                  |
| Initial deployment   | Python and systemd             |
| Future deployment    | Docker Compose optional        |

---

## 21. Final Architecture Statement

The Quote Finder revamp is a hybrid retrieval system.

Neon stores the canonical story text and application state.

Qdrant stores semantic vector indexes.

FicHub provides temporary EPUB inputs.

The ingestion pipeline transforms EPUB files into normalized, versioned, searchable story data.

The Discord bot performs retrieval only.

Exact quote searches use source text.

Vague scene searches use semantic similarity.

All results return original passages from the indexed story.
