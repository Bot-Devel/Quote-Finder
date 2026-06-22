# Quote Finder Ingestion Specification

## 1. Purpose

This document defines the ingestion pipeline for the Quote Finder revamp.

The ingestion pipeline transforms a FanFiction.net story into normalized, searchable, versioned data stored across:

* Neon Postgres for canonical text and metadata
* Qdrant Cloud for semantic vectors

The pipeline must support:

* initial ingestion
* manual re-ingestion
* refresh-triggered ingestion
* multiple stories
* safe version activation
* full rebuilds
* future incremental chapter updates

The downloaded EPUB is a temporary source artifact and is deleted after ingestion completes or fails.

---

## 2. Scope

This specification covers:

* accepting a FanFiction.net story URL or ID
* resolving the story through FicHub
* downloading the latest EPUB
* validating the EPUB
* parsing EPUB reading order
* excluding non-story documents
* assigning chapter numbers
* extracting chapter titles and paragraphs
* normalizing text
* generating exact-search data
* generating semantic chunks
* generating embeddings
* writing canonical data to Neon
* writing vectors to Qdrant
* validating the new fic version
* activating the version when requested
* failure recovery
* temporary-file cleanup

This specification does not define:

* scheduled refresh selection
* refresh retry scheduling
* Discord commands
* exact-search ranking
* semantic-search ranking
* deployment infrastructure

Those are covered by separate specifications.

---

## 3. High-Level Pipeline

```text
FanFiction.net URL or story ID
        ↓
Validate and normalize source identifier
        ↓
Create ingestion job
        ↓
Create fic version with status = building
        ↓
Request latest EPUB from FicHub
        ↓
Download EPUB to temporary storage
        ↓
Validate EPUB file
        ↓
Calculate EPUB SHA-256 hash
        ↓
Parse EPUB metadata and reading order
        ↓
Detect story chapter documents
        ↓
Extract and normalize chapters
        ↓
Extract and normalize paragraphs
        ↓
Generate semantic chunks
        ↓
Persist canonical data to Neon
        ↓
Generate document embeddings
        ↓
Upsert vectors to Qdrant
        ↓
Validate complete version
        ↓
Mark version ready
        ↓
Optionally activate version
        ↓
Delete temporary EPUB
```

---

## 4. Entry Points

The ingestion pipeline must support at least three entry points.

## 4.1 CLI ingestion

Used for development, manual imports, and initial production setup.

Example:

```bash
quote-finder ingest \
  --url "https://www.fanfiction.net/s/1234567/1/Story-Name" \
  --guild-id 123456789012345678 \
  --activate
```

Supported arguments:

```text
--url
--story-id
--guild-id
--activate
--force
--skip-embeddings
--keep-epub
--output-json
```

Only one of `--url` or `--story-id` is required. If ingesting a new fic, `--guild-id` is required.

---

## 4.2 Refresh-worker ingestion

The refresh worker may call the same ingestion service after determining that a story changed.

The ingestion service must not contain scheduling logic.

Example internal call:

```python
result = await ingestion_service.ingest(
    fic_id=fic.id,
    source_story_id=fic.source_story_id,
    activate=True,
    expected_previous_version_id=fic.active_version_id,
)
```

---

## 4.3 Administrative API or Discord command

A future administrative command may trigger ingestion.

The command must enqueue or invoke the ingestion service rather than duplicating ingestion logic.

---

## 5. Source Identification

The pipeline must accept either:

* full FanFiction.net story URL
* numeric FanFiction.net story ID

Example URL:

```text
https://www.fanfiction.net/s/1234567/1/Story-Name
```

Normalized source identifier:

```text
1234567
```

The parser must reject:

* non-FanFiction.net URLs
* chapter URLs without a valid story ID
* invalid numeric IDs
* unsupported domains
* malformed URLs

Canonical source URL:

```text
https://www.fanfiction.net/s/1234567/
```

The numeric story ID is the stable external identifier.

---

## 6. FicHub Client

The ingestion pipeline must access FicHub through a dedicated client.

Suggested interface:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FicHubDownloadResult:
    story_id: str
    file_path: Path
    content_type: str | None
    content_length: int | None
    source_filename: str | None


class FicHubClient:
    async def download_epub(
        self,
        source_url: str,
        destination: Path,
    ) -> FicHubDownloadResult:
        ...
```

The client is responsible for:

* constructing FicHub requests
* handling redirects
* applying timeouts
* validating HTTP status
* streaming the response to disk
* limiting maximum file size
* retrying transient failures
* exposing structured errors

The client must not:

* parse the EPUB
* modify database state
* generate embeddings
* activate versions

---

## 7. Download Requirements

The EPUB must be downloaded to a unique temporary directory.

Example:

```text
/tmp/quote-finder/
  ffn_1234567/
    ingestion_01JABCDEF/
      story.epub
```

Requirements:

* directories must be created with restricted permissions
* downloads must stream to disk
* full response bodies must not remain in memory
* partial files must use a temporary suffix
* partial files must not be parsed
* successful download must be atomically renamed

Example:

```text
story.epub.part
→ story.epub
```

Recommended limits:

```text
connect timeout: 15 seconds
read timeout: 120 seconds
maximum EPUB size: configurable, default 250 MB
retry attempts: 3
```

Retries should apply only to transient errors such as:

* connection timeout
* HTTP 429
* HTTP 502
* HTTP 503
* HTTP 504

Retries must not apply indefinitely.

---

## 8. EPUB Validation

Before parsing, the pipeline must validate that the downloaded file is plausibly an EPUB.

Minimum checks:

1. file exists
2. file size is greater than zero
3. file is a valid ZIP archive
4. `mimetype` entry exists or EPUB structure is otherwise valid
5. `META-INF/container.xml` exists
6. package document can be resolved
7. EPUB spine exists
8. at least one readable document exists

The pipeline should reject:

* HTML error pages saved as `.epub`
* empty files
* corrupted ZIP archives
* unsupported archive formats
* EPUB files without readable content

Validation errors must include a machine-readable failure stage.

Example:

```text
failure_stage = epub_validation
```

---

## 9. File Hashing

After successful download, calculate:

```text
SHA-256(epub bytes)
```

Store the result as:

```text
epub_hash
```

Uses:

* detect unchanged downloads
* associate versions with source artifacts
* diagnose duplicate ingestions
* support refresh decisions
* support audit logging

The hash must not be used as the only content-validity check.

---

## 10. Version Creation

Before writing story content, create a new fic version.

Example status:

```text
building
```

Suggested fields:

```text
id
fic_id
epub_hash
status
source_story_id
embedding_model
embedding_dimensions
created_at
started_at
```

The new version must not become active during ingestion.

Example:

```text
active version: v7
new version: v8, status = building
```

The active version remains searchable until activation succeeds.

---

## 11. EPUB Parsing

The parser must use EPUB structure rather than filenames or visible chapter numbering.

The parser should inspect:

* package document
* manifest
* spine
* navigation document
* table of contents
* document media types

The spine defines primary reading order.

The table of contents may help resolve titles but must not be trusted as the only chapter ordering source.

---

## 12. Story Document Detection

EPUB files may contain non-story documents such as:

* title page
* cover page
* metadata page
* author notes
* table of contents
* copyright page
* index
* navigation document

The parser must identify likely story chapter documents.

Detection may use:

* spine order
* document text length
* navigation labels
* heading structure
* known FicHub EPUB conventions
* known non-story filenames
* content heuristics

No single filename rule may be required.

The parser must record excluded documents for debugging.

Example:

```json
{
  "excluded_documents": [
    {
      "path": "title_page.xhtml",
      "reason": "non_story_front_matter"
    },
    {
      "path": "nav.xhtml",
      "reason": "navigation_document"
    }
  ]
}
```

---

## 13. Chapter Numbering

Chapter numbers must be assigned sequentially from validated reading order.

Example:

```python
for index, document in enumerate(story_documents, start=1):
    chapter_number = index
```

Chapter numbering must not depend on:

* filename
* chapter title text
* numeric prefixes
* table-of-contents labels

Stored fields:

```text
chapter_number
chapter_title
source_document_path
```

Example:

```json
{
  "chapter_number": 14,
  "chapter_title": "A Long Night",
  "source_document_path": "OEBPS/Text/chapter14.xhtml"
}
```

---

## 14. Chapter Title Extraction

Chapter titles should be extracted in priority order:

1. EPUB navigation label
2. first meaningful heading in the document
3. document title metadata
4. generated fallback

Fallback:

```text
Chapter 14
```

The title must be stored separately from the chapter number.

The parser should normalize titles by:

* trimming whitespace
* removing duplicate whitespace
* decoding HTML entities
* removing surrounding formatting artifacts

The original visible title may also be retained for debugging if needed.

---

## 15. HTML Sanitization

EPUB chapter content is HTML or XHTML.

The parser must:

* parse HTML safely
* remove script tags
* remove style tags
* remove navigation elements
* remove embedded forms
* ignore executable content
* preserve textual reading order
* decode entities
* preserve paragraph boundaries

The parser must never execute EPUB content.

Potentially useful elements include:

```text
p
div
blockquote
pre
h1
h2
h3
h4
li
br
```

Element handling must prioritize readable text rather than visual fidelity.

---

## 16. Paragraph Extraction

Canonical text is stored as ordered paragraphs.

Each paragraph must include:

```text
paragraph_number
text
normalized_text
word_count
```

Paragraph numbering starts at 1 within each chapter.

Example:

```json
{
  "paragraph_number": 81,
  "text": "Harry looked away. He had no answer.",
  "normalized_text": "harry looked away. he had no answer.",
  "word_count": 8
}
```

Paragraph extraction must:

* preserve order
* remove empty paragraphs
* collapse repeated whitespace
* preserve dialogue punctuation in original text
* preserve source casing in original text
* avoid merging the entire chapter into one paragraph
* avoid splitting every sentence into separate paragraphs

---

## 17. Text Normalization

The system must retain two text forms:

### Original text

Used for:

* displayed search results
* surrounding context
* quoted output

### Normalized text

Used for:

* exact matching
* duplicate detection
* hashing
* search preprocessing

Suggested normalization:

* Unicode normalization
* case folding
* whitespace collapsing
* nonbreaking-space replacement
* curly quote normalization
* apostrophe normalization
* dash normalization
* zero-width character removal

Example:

```text
Original:
“Harry—don’t,” she said.

Normalized:
"harry-don't," she said.
```

Normalization rules must be deterministic and shared with query normalization.

---

## 18. Chapter Hashing

Each normalized chapter must receive a content hash.

Suggested input:

```text
normalized chapter title
+
ordered normalized paragraph text
```

Hash:

```text
SHA-256
```

Stored as:

```text
chapter_hash
```

Chapter hashes support future incremental refreshes.

They are not required for initial full-rebuild activation logic but must be generated from the beginning.

---

## 19. Paragraph Storage

Paragraphs must be inserted into Neon in batches.

Suggested batch size:

```text
100 to 1000 rows
```

The exact value should be configurable.

Requirements:

* inserts must reference the new version
* paragraph order must be preserved
* duplicate IDs must not silently overwrite unrelated rows
* insertion failures must fail the version
* partial versions must remain inactive

Stable or deterministic IDs are preferred where practical.

Example deterministic input:

```text
fic_id + version_id + chapter_number + paragraph_number
```

---

## 20. Semantic Chunking

Semantic chunks are built from ordered paragraphs.

Chunks must:

* remain inside one chapter
* preserve paragraph order
* preserve paragraph boundaries
* contain enough context for vague scene search
* overlap neighbouring chunks
* resolve back to paragraph ranges

Initial recommended settings:

```text
target chunk size: 400 words
minimum chunk size: 200 words
maximum chunk size: 650 words
overlap: 75 words
```

These values must be configurable.

---

## 21. Chunk Construction Rules

Chunking should accumulate whole paragraphs until the target size is reached.

Example:

```text
paragraphs 1–6 → chunk 1
paragraphs 5–10 → chunk 2
paragraphs 9–14 → chunk 3
```

Store:

```text
chunk_number
start_paragraph
end_paragraph
text
normalized_text
word_count
text_hash
```

Example:

```json
{
  "chunk_number": 18,
  "start_paragraph": 81,
  "end_paragraph": 89,
  "word_count": 417
}
```

A chunk must never contain paragraphs from two chapters.

---

## 22. Chunk Hashing

Each semantic chunk must receive a content hash.

Suggested input:

```text
normalized chunk text
```

Hash:

```text
SHA-256
```

Stored as:

```text
text_hash
```

Uses:

* duplicate detection
* embedding reuse
* future incremental updates
* diagnostics

---

## 23. Embedding Generation

Document embeddings are generated after chunk construction.

The embedding provider must receive chunk text in batches.

Example:

```python
vectors = await embedding_provider.embed_documents(
    [chunk.text for chunk in chunks]
)
```

Requirements:

* document and query embeddings must use the same model
* vector dimensions must be validated
* empty vectors must be rejected
* NaN values must be rejected
* batch size must be configurable
* provider retries must be bounded
* provider rate limits must be respected

Suggested initial batch size:

```text
16 to 64 chunks
```

---

## 24. Embedding Metadata

Each version must record:

```text
embedding_provider
embedding_model
embedding_dimensions
embedding_created_at
```

Each chunk may also record:

```text
embedding_model
embedding_dimensions
```

This prevents querying an index with an incompatible embedding model.

A version must not activate if its vectors use inconsistent dimensions.

---

## 25. Qdrant Collection Strategy

The initial architecture should use one shared collection for all fic chunks.

Example collection:

```text
quote_finder_chunks
```

Each Qdrant point must include a vector and payload.

Example payload:

```json
{
  "fic_id": "ffn_1234567",
  "version_id": "01JVERSION123",
  "chapter_id": "01JCHAPTER123",
  "chunk_id": "01JCHUNK123",
  "chapter_number": 42,
  "chunk_number": 18,
  "start_paragraph": 81,
  "end_paragraph": 89,
  "embedding_model": "model-name"
}
```

Qdrant point IDs must map deterministically or explicitly to Neon chunk IDs.

---

## 26. Qdrant Upserts

Vectors must be uploaded in batches.

Suggested batch size:

```text
64 to 256 points
```

Requirements:

* use idempotent upserts
* verify vector dimensions
* include fic and version filters
* record successful batch counts
* fail ingestion on unrecoverable Qdrant errors
* avoid activating partially indexed versions

The ingestion service must know the expected vector count.

---

## 27. Neon Transaction Boundaries

A single transaction should not remain open for the entire ingestion of a large fic.

Recommended pattern:

1. create version record
2. insert chapters
3. insert paragraphs in batches
4. insert chunks in batches
5. commit each controlled phase
6. mark version validating
7. activate only after cross-system validation

Because Neon and Qdrant do not share a transaction, consistency is enforced through version status and activation rules.

An inactive partial version is acceptable.

A partial active version is not.

---

## 28. Ingestion State Machine

Suggested states:

```text
created
downloading
validating_epub
parsing
persisting_text
embedding
persisting_vectors
validating_version
ready
active
failed
```

The current state should be persisted.

Example fields:

```text
status
current_stage
started_at
updated_at
completed_at
failed_at
failure_stage
failure_reason
```

---

## 29. Validation Before Activation

A new version must pass validation before activation.

Minimum checks:

### Source validation

* story ID matches expected fic
* EPUB hash exists
* EPUB parsed successfully

### Chapter validation

* chapter count greater than zero
* chapter numbers are unique
* chapter numbers are sequential
* first chapter contains text
* last chapter contains text

### Paragraph validation

* paragraph count greater than zero
* each paragraph belongs to a valid chapter
* paragraph numbers are sequential within chapters

### Chunk validation

* chunk count greater than zero
* chunks remain within chapter boundaries
* paragraph ranges are valid
* no chunk has empty text

### Vector validation

* Qdrant point count matches expected chunk count
* vector dimensions match version metadata
* all points carry correct fic and version IDs

### Sanity validation

* word count is within configurable limits
* chapter count is within configurable limits
* new version is not unexpectedly tiny compared with previous active version

Suggested warning thresholds:

```text
new word count < 80% of active version
new chapter count < active chapter count
```

These conditions may fail activation unless forced.

---

## 30. Activation

Activation must occur only after validation succeeds.

Suggested transaction:

```sql
BEGIN;

UPDATE fic_versions
SET status = 'ready',
    validated_at = NOW()
WHERE id = :version_id;

UPDATE fics
SET active_version_id = :version_id,
    last_refreshed_at = NOW(),
    last_refresh_status = 'success',
    last_refresh_error = NULL,
    updated_at = NOW()
WHERE id = :fic_id;

UPDATE fic_versions
SET status = 'active',
    activated_at = NOW()
WHERE id = :version_id;

COMMIT;
```

The previous active version should become:

```text
archived
```

but should not be deleted immediately.

---

## 31. Non-Activating Ingestion

The pipeline must support building and validating a version without activating it.

Example:

```bash
quote-finder ingest \
  --story-id 1234567 \
  --no-activate
```

Use cases:

* testing new parser logic
* comparing version counts
* testing embedding changes
* validating a new provider
* manual review

The resulting version status should be:

```text
ready
```

---

## 32. Force Mode

A force flag may allow ingestion despite selected warnings.

Example:

```bash
quote-finder ingest \
  --story-id 1234567 \
  --activate \
  --force
```

Force mode must not bypass:

* corrupted EPUB validation
* empty chapter validation
* missing vectors
* vector dimension mismatch
* database integrity errors

Force mode may bypass:

* reduced chapter-count warning
* reduced word-count warning
* duplicate EPUB hash
* known source metadata mismatch with explicit confirmation

All forced activations must be logged.

---

## 33. Duplicate EPUB Handling

If the new EPUB hash matches the active version:

```text
no new version is required
```

Default behavior:

* record last checked time
* delete temporary EPUB
* return unchanged result
* do not re-embed
* do not create duplicate active data

A `--force` option may permit re-ingestion for parser or model migrations.

---

## 34. Re-Embedding Without Re-Parsing

The architecture should allow a future operation that rebuilds vectors from canonical chunks without downloading the EPUB again.

Example:

```bash
quote-finder reembed \
  --fic-id ffn_1234567 \
  --version-id 01JVERSION123 \
  --model new-model
```

This is possible because canonical chunk text is stored in Neon.

Qdrant indexes must therefore be reproducible from Neon data.

---

## 35. Failure Handling

Any unrecoverable failure must:

1. stop activation
2. mark the version failed
3. record failure stage
4. record sanitized error message
5. retain the active version
6. clean temporary files
7. optionally retain failed database rows for debugging

Example failure:

```json
{
  "status": "failed",
  "failure_stage": "embedding",
  "failure_reason": "provider_timeout",
  "retry_count": 3
}
```

Secrets and full EPUB content must not appear in error logs.

---

## 36. Cleanup After Failure

Temporary cleanup must run in a `finally`-equivalent path.

Cleanup targets:

* temporary EPUB
* partial download
* extracted temporary directory
* temporary JSON files
* temporary vector batches

Failed Neon and Qdrant version data may be cleaned immediately or asynchronously.

The active version must never be deleted as part of failed-ingestion cleanup.

---

## 37. Idempotency

The ingestion process must be safe to retry.

Idempotency requirements:

* version IDs are unique
* Qdrant point IDs are stable within a version
* repeated batch upserts do not create duplicates
* repeated paragraph inserts must be detectable
* activation must not activate the wrong version
* retries must not create multiple active versions

An ingestion job ID should be associated with the version.

---

## 38. Concurrency Control

Only one ingestion for a given fic should run at a time.

Possible mechanisms:

* Postgres advisory lock
* row-level lock
* ingestion-job claim column
* unique partial index on running job

Example rule:

```text
one running ingestion per fic_id
```

Different fics may ingest concurrently if configured.

Initial recommended global concurrency:

```text
1
```

This reduces provider rate-limit and memory problems.

---

## 39. Observability

The ingestion service must log:

```text
ingestion_job_id
fic_id
source_story_id
version_id
stage
duration
download_size
chapter_count
paragraph_count
chunk_count
word_count
embedding_count
provider
model
activation_result
```

Example structured log:

```json
{
  "event": "ingestion_completed",
  "fic_id": "ffn_1234567",
  "version_id": "01JVERSION123",
  "chapter_count": 180,
  "paragraph_count": 42318,
  "chunk_count": 5214,
  "word_count": 1512044,
  "duration_seconds": 487
}
```

---

## 40. Metrics

Recommended metrics:

```text
ingestion_started_total
ingestion_completed_total
ingestion_failed_total
ingestion_duration_seconds
epub_download_bytes
epub_download_duration_seconds
chapters_processed_total
paragraphs_processed_total
chunks_created_total
embeddings_generated_total
embedding_duration_seconds
qdrant_upsert_duration_seconds
neon_insert_duration_seconds
```

Metrics may initially be represented by structured logs rather than a dedicated monitoring system.

---

## 41. Security

The ingestion pipeline must:

* validate source URLs
* restrict supported domains
* sanitize archive paths
* prevent ZIP path traversal
* avoid extracting files outside the temporary directory
* enforce file-size limits
* enforce extraction-size limits
* reject suspicious archive structures
* never execute EPUB content
* never render raw HTML in Discord
* store credentials outside source control

Potential ZIP-slip paths such as:

```text
../../etc/passwd
```

must be rejected.

---

## 42. Resource Limits

The pipeline must use bounded resources.

Recommended defaults:

```text
maximum EPUB size: 250 MB
maximum extracted size: 1 GB
maximum chapter count: 10,000
maximum paragraph count: configurable
maximum chunk count: configurable
embedding batch size: 32
Qdrant batch size: 128
Neon insert batch size: 500
global ingestion concurrency: 1
```

These values should be configurable through environment variables or application settings.

---

## 43. Configuration

Suggested configuration:

```text
FICHUB_BASE_URL
INGESTION_TEMP_DIR
INGESTION_MAX_EPUB_BYTES
INGESTION_MAX_EXTRACTED_BYTES
INGESTION_CONCURRENCY
INGESTION_KEEP_FAILED_DATA
CHUNK_TARGET_WORDS
CHUNK_MIN_WORDS
CHUNK_MAX_WORDS
CHUNK_OVERLAP_WORDS
EMBEDDING_BATCH_SIZE
QDRANT_BATCH_SIZE
DATABASE_BATCH_SIZE
```

---

## 44. Suggested Internal Models

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedParagraph:
    number: int
    text: str
    normalized_text: str
    word_count: int


@dataclass
class ParsedChapter:
    number: int
    title: str | None
    source_path: str
    chapter_hash: str
    paragraphs: list[ParsedParagraph]
    word_count: int


@dataclass
class ParsedChunk:
    number: int
    chapter_number: int
    start_paragraph: int
    end_paragraph: int
    text: str
    normalized_text: str
    text_hash: str
    word_count: int


@dataclass
class ParsedFic:
    source_story_id: str
    title: str
    author: str | None
    epub_hash: str
    chapters: list[ParsedChapter]
    chunks: list[ParsedChunk]
    word_count: int
```

---

## 45. Suggested Service Boundaries

```text
SourceIdentifierParser
FicHubClient
EpubValidator
EpubParser
ChapterExtractor
ParagraphNormalizer
ChunkBuilder
EmbeddingProvider
FicRepository
VectorStore
VersionValidator
VersionActivator
IngestionService
```

The ingestion service coordinates these components.

It should not implement every detail directly.

---

## 46. Initial Implementation Strategy

The first implementation should prefer simplicity over optimization.

Version one should:

* download the entire EPUB
* parse the entire story
* rebuild all chapters
* rebuild all paragraphs
* rebuild all chunks
* regenerate all embeddings
* create a complete new version
* activate only after validation

It should not initially:

* diff chapters
* reuse old vectors
* patch individual chapters
* stream directly from FicHub into Qdrant
* modify the active version in place

---

## 47. Future Incremental Ingestion

A later implementation may compare chapter hashes.

Possible flow:

```text
parse latest EPUB
→ calculate chapter hashes
→ compare with active version
→ reuse unchanged chapter data
→ rebuild changed chapters
→ embed changed chunks only
→ create complete replacement version
```

Incremental ingestion must preserve the same versioned activation model.

It must not mutate active chapter rows in place.

---

## 48. Acceptance Criteria

The ingestion pipeline is complete when:

1. A valid FanFiction.net URL can be normalized.
2. FicHub EPUB can be downloaded successfully.
3. Invalid or corrupted downloads are rejected.
4. EPUB reading order is parsed correctly.
5. Non-story documents are excluded.
6. Chapters are numbered sequentially from reading order.
7. Chapter titles are stored separately from numbers.
8. Paragraphs preserve readable order and original text.
9. Normalized text is deterministic.
10. Chapter hashes are generated.
11. Semantic chunks preserve paragraph boundaries.
12. Chunks do not cross chapter boundaries.
13. Chunk hashes are generated.
14. Canonical data is written to Neon.
15. Embeddings are generated with the configured model.
16. Vectors are written to Qdrant.
17. Qdrant point count matches chunk count.
18. Failed ingestion does not affect the active version.
19. Successful ingestion may activate atomically.
20. Temporary EPUB files are deleted.
21. Duplicate EPUB hashes skip unnecessary rebuilds.
22. The pipeline can be safely retried.
23. Multiple fics can be ingested independently.
24. Canonical data can later be re-embedded without the EPUB.
25. The pipeline supports non-activating test ingestion.

---

## 49. Final Ingestion Rule

The ingestion pipeline must always produce a complete, isolated fic version.

It must never modify the active searchable version in place.

Downloaded EPUB files are temporary.

Neon stores canonical text.

Qdrant stores semantic vectors.

A new version becomes visible only after the entire ingestion and validation process succeeds.
