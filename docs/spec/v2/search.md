# Quote Finder Search Specification

## 1. Purpose

This document defines search behaviour for the Quote Finder revamp.

The bot exposes three distinct search commands:

```text
!qe <query>   exact quote search
!qf <query>   fuzzy quote search
!qs <query>   semantic scene search
```

Each command uses a separate retrieval strategy.

The search system must:

* support multiple FanFiction.net stories
* search only the selected fic and its active version
* preserve existing pagination behaviour
* return original story text
* return chapter metadata
* return nearby context
* cap exact and fuzzy results at 100
* keep exact, fuzzy, and semantic behaviour separate
* never generate or invent story content

The system is a retrieval service, not an answer-generating RAG chatbot.

---

## 2. Scope

This specification covers:

* exact quote search
* fuzzy quote search
* semantic scene search
* query validation
* query normalization
* result ranking
* search scoping
* context retrieval
* result limits
* result deduplication
* pagination integration
* search sessions
* error handling
* search observability
* performance expectations

This specification does not cover:

* FicHub EPUB ingestion
* refresh scheduling
* EPUB parsing
* Discord embed design
* deployment
* database migrations
* embedding-provider hosting

Those are defined in separate specifications.

---

## 3. Public Command Contract

The bot must preserve the following commands.

### Exact quote search

```text
!qe <query>
```

Purpose:

* find literal wording
* match normalized punctuation and casing
* return every matching search unit up to the configured result cap

---

### Fuzzy quote search

```text
!qf <query>
```

Purpose:

* find approximately remembered wording
* tolerate spelling differences
* tolerate omitted or changed words
* rank results by lexical similarity

---

### Semantic scene search

```text
!qs <query>
```

Purpose:

* find a scene from a vague description
* retrieve conceptually related passages
* work even when the query shares few exact words with the source text

---

## 4. Internal Search Modes

The search service must expose three modes:

```text
exact
fuzzy
semantic
```

These modes must not silently fall back into one another.

Specifically:

* `!qe` must not automatically run fuzzy search
* `!qf` must not automatically run semantic search
* `!qs` must not pretend to be exact quote search

The user explicitly selects the desired retrieval behaviour through the command.

---

## 5. Search Unit

The existing bot searches line-like units and returns the matched unit plus nearby text.

The revamp must preserve equivalent behaviour.

The ingestion layer must store or derive a deterministic quote-search unit.

Recommended model:

```text
search_lines
```

Suggested fields:

```text
id
fic_id
version_id
chapter_id
line_number
paragraph_number
text
normalized_text
created_at
```

A search line may correspond to:

* one original text line
* one paragraph
* one deterministic logical line produced by EPUB normalization

The final choice should preserve the current bot’s visible behaviour as closely as possible.

Semantic search does not use individual search lines. It uses larger paragraph-based chunks.

---

## 6. High-Level Search Flow

```text
Discord command
      ↓
Resolve selected fic
      ↓
Resolve active version
      ↓
Validate query
      ↓
Choose command-specific search mode
      ↓
┌───────────────────────────┐
│ !qe                       │
│ normalized literal search │
│ Neon Postgres             │
└───────────────────────────┘

or

┌───────────────────────────┐
│ !qf                       │
│ fuzzy lexical search      │
│ Postgres + RapidFuzz      │
└───────────────────────────┘

or

┌───────────────────────────┐
│ !qs                       │
│ query embedding           │
│ Qdrant similarity search  │
│ Neon context retrieval    │
└───────────────────────────┘
      ↓
Create shared result objects
      ↓
Create pagination session
      ↓
Return original source text
```

---

## 7. Fic Resolution

Every search must resolve exactly one fic.

Suggested resolution order:

1. fic explicitly supplied with command
2. channel default fic
3. guild default fic
4. user-selected fic, if supported
5. return fic-selection-required error

The selected fic must exist and have an active version.

Required condition:

```text
active_version_id IS NOT NULL
```

Search must not use:

* building versions
* failed versions
* archived versions
* ready but inactive versions

---

## 8. Version Resolution

Every query must resolve:

```text
fic_id
active_version_id
```

Both values must be included in all database and vector-store filters.

Example:

```text
fic_id = ffn_1234567
version_id = 01JACTIVEVERSION
```

A short-lived active-version cache may be used.

Recommended cache TTL:

```text
30 to 60 seconds
```

The cache must expire or be invalidated when a new fic version is activated.

---

## 9. Query Validation

Suggested limits:

```text
minimum query length: 2 characters
maximum exact query length: 500 characters
maximum fuzzy query length: 500 characters
maximum semantic query length: 1000 characters
```

Reject:

* empty queries
* whitespace-only queries
* excessive query length
* invalid fic identifiers
* unsupported control characters

Repeated whitespace should be collapsed before search.

---

## 10. Query Normalization

Exact and fuzzy quote search must use the same deterministic normalization rules used during ingestion.

Suggested normalization:

1. Unicode normalization
2. case folding
3. replace nonbreaking spaces
4. collapse repeated whitespace
5. normalize curly quotes
6. normalize apostrophes
7. normalize long dashes
8. remove zero-width characters
9. trim leading and trailing whitespace

Example:

```text
Input:
“Harry—don’t do that.”

Normalized:
"harry-don't do that."
```

Original source text must always be retained and displayed.

Normalized text exists only for matching.

---

# Exact Search

## 11. Exact Search Behaviour

Command:

```text
!qe <query>
```

Exact search finds normalized contiguous substring matches.

Suggested SQL behaviour:

```sql
WHERE fic_id = :fic_id
  AND version_id = :version_id
  AND normalized_text LIKE '%' || :normalized_query || '%'
```

Application code must use bound SQL parameters.

Raw query text must never be concatenated into SQL.

---

## 12. Exact Search Matching Rules

Exact search should tolerate only normalization-level differences.

It may match differences in:

* uppercase and lowercase
* curly and straight quotes
* apostrophe style
* dash style
* repeated whitespace
* Unicode formatting artifacts

It must not tolerate:

* reordered words
* missing words
* unrelated synonyms
* approximate spelling

Those belong to fuzzy or semantic search.

---

## 13. Exact Search Result Limit

Exact search must return at most:

```text
100 results
```

Configuration:

```text
QUOTE_EXACT_MAX_RESULTS=100
```

If more than 100 matches exist, the result metadata must preserve:

```text
returned_results
total_matches
results_truncated
```

Example:

```text
returned_results = 100
total_matches = 237
results_truncated = true
```

The Discord layer may display:

```text
Showing 100 of 237 matches.
```

---

## 14. Exact Search Ordering

Exact results should preserve story order.

Sort by:

```text
chapter_number ASC
line_number ASC
```

If exactness categories are introduced, use:

1. full-line equality
2. line starts with query
3. line contains query
4. story order

However, the initial implementation may simply preserve reading order for all matching lines.

---

## 15. Exact Search Context

Each result should include:

* matching line or search unit
* next line
* optionally previous line
* chapter number
* chapter title
* line number
* result number
* total returned results
* total matches when known

To preserve current behaviour, the minimum context should be:

```text
matched line
next line
```

Optional configuration:

```text
QUOTE_CONTEXT_PREVIOUS_LINES=0
QUOTE_CONTEXT_NEXT_LINES=1
```

---

## 16. Exact Search Pagination

The existing paginator should be reused.

Expected behaviour:

```text
1 result per page
up to 100 pages
```

The search service may fetch the first 100 result IDs and keep them in a search session.

It does not need to fetch every matching result beyond the 100-result cap.

---

# Fuzzy Search

## 17. Fuzzy Search Behaviour

Command:

```text
!qf <query>
```

Fuzzy search finds quote lines similar to the user’s wording.

It is lexical similarity search, not semantic scene search.

It should tolerate:

* spelling mistakes
* omitted words
* inserted words
* minor word substitutions
* punctuation differences
* partial remembered phrases
* slightly changed word order

---

## 18. Fuzzy Search Compatibility

The first implementation should inspect and preserve the existing bot’s fuzzy behaviour where practical.

The current implementation may use:

* `difflib.SequenceMatcher`
* FuzzyWuzzy
* RapidFuzz
* Levenshtein ratio
* partial ratio
* token-set ratio
* another lexical scorer

The existing threshold and scorer should be documented before replacement.

Compatibility is preferred over casually replacing a behaviour users already understand.

---

## 19. Recommended Fuzzy Implementation

Recommended stack:

```text
PostgreSQL pg_trgm
→ retrieve likely candidates
→ RapidFuzz final scoring
→ sort
→ return top 100
```

Postgres narrows the candidate set.

RapidFuzz calculates the final user-visible ranking.

This avoids comparing the query against every line in Python.

---

## 20. Candidate Retrieval

Enable PostgreSQL trigram support:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Suggested index:

```sql
CREATE INDEX search_lines_normalized_text_trgm_idx
ON search_lines
USING GIN (normalized_text gin_trgm_ops);
```

Candidate query may use:

```sql
similarity(normalized_text, :normalized_query)
```

Suggested candidate limit:

```text
300
```

Configuration:

```text
QUOTE_FUZZY_CANDIDATE_LIMIT=300
```

The candidate limit may be increased after benchmarking.

---

## 21. Fuzzy Scoring

Recommended scorer:

```python
from rapidfuzz import fuzz

score = fuzz.partial_ratio(
    normalized_query,
    normalized_candidate,
)
```

Alternative scorers may be tested:

```text
ratio
partial_ratio
token_sort_ratio
token_set_ratio
WRatio
```

The chosen scorer must be documented.

The scorer must remain stable unless changed through an explicit migration.

---

## 22. Fuzzy Threshold

Only candidates above the configured threshold should be returned.

Suggested starting threshold:

```text
75
```

Configuration:

```text
QUOTE_FUZZY_MIN_SCORE=75
```

The final threshold should be based on the old implementation and actual search tests.

Do not treat 75 as a universal truth handed down from the mountain. It is merely a starting value wearing a number costume.

---

## 23. Fuzzy Search Result Limit

Fuzzy search must return at most:

```text
100 results
```

Configuration:

```text
QUOTE_FUZZY_MAX_RESULTS=100
```

Result ordering:

```text
similarity score DESC
chapter number ASC
line number ASC
```

---

## 24. Fuzzy Result Metadata

Each fuzzy result must include:

```text
match_type = fuzzy
similarity_score
```

Suggested score range:

```text
0 to 100
```

The score may be displayed in admin or debug mode.

The public bot interface does not need to expose the numeric score unless it already does.

---

## 25. Fuzzy Search Context

Fuzzy results should use the same context rules as exact search.

Minimum:

```text
matched line
next line
```

The result should also include:

* chapter number
* chapter title
* line number
* similarity score internally

---

## 26. Fuzzy Search Pagination

Expected behaviour:

```text
1 result per page
up to 100 pages
```

Results are ranked by fuzzy score before pagination.

The paginator must preserve the ranked order.

---

## 27. Exact and Fuzzy Separation

`!qe` and `!qf` must remain separate.

`!qe` must not:

* call fuzzy search when no results are found
* reorder results by fuzzy score
* return approximate matches

`!qf` must not:

* label approximate results as exact
* fall back to semantic search
* imply that returned text contains the exact user phrase

---

# Semantic Search

## 28. Semantic Search Behaviour

Command:

```text
!qs <query>
```

Semantic search finds scenes using vague natural-language descriptions.

Example:

```text
!qs Harry acts calm until everyone leaves and then collapses
```

The query may share few exact words with the source passage.

Semantic search must:

* generate a query embedding
* query Qdrant
* filter by fic and active version
* retrieve semantic chunk IDs
* fetch canonical text from Neon
* return multiple likely scenes

---

## 29. Semantic Query Embedding

The search service must use the configured embedding provider.

Interface:

```python
class EmbeddingProvider:
    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...
```

The query model must match the active version’s document-embedding model.

Validate:

```text
embedding model
embedding dimensions
```

A mismatch must fail safely.

---

## 30. Semantic Search Filters

Every Qdrant query must filter by:

```text
fic_id
version_id
```

Example:

```json
{
  "must": [
    {
      "key": "fic_id",
      "match": {
        "value": "ffn_1234567"
      }
    },
    {
      "key": "version_id",
      "match": {
        "value": "01JACTIVEVERSION"
      }
    }
  ]
}
```

Semantic search must never return chunks from:

* another fic
* another version
* an incomplete ingestion

---

## 31. Semantic Candidate Count

Recommended initial retrieval:

```text
Qdrant candidates: 20
displayed results: 10
```

Configuration:

```text
SCENE_SEARCH_TOP_K=20
SCENE_SEARCH_MAX_RESULTS=10
```

Unlike exact and fuzzy search, semantic search does not need to return 100 results.

The purpose is to surface the strongest candidate scenes, not paginate through a hundred philosophically related paragraphs.

---

## 32. Semantic Similarity Score

The raw Qdrant score should be retained internally.

Do not display it as an accuracy percentage.

Example:

```text
0.78 similarity
```

does not mean:

```text
78% correct
```

The UI may omit the score entirely.

---

## 33. Semantic Minimum Score

The first implementation should avoid an aggressive hard threshold.

Recommended initial behaviour:

```text
retrieve top candidates
log score distributions
evaluate manually
introduce threshold later
```

Optional configuration:

```text
SCENE_SEARCH_MIN_SCORE
```

The threshold depends on the embedding model and corpus.

---

## 34. Semantic Context Retrieval

Qdrant returns chunk IDs and metadata.

The search service must fetch source text from Neon.

Each semantic result should include:

* chunk text
* chapter number
* chapter title
* start paragraph
* end paragraph
* previous context paragraphs
* following context paragraphs

The displayed source text must come from Neon.

---

## 35. Semantic Result Expansion

Recommended context:

```text
2 paragraphs before
2 paragraphs after
```

Configuration:

```text
SCENE_CONTEXT_PARAGRAPHS_BEFORE=2
SCENE_CONTEXT_PARAGRAPHS_AFTER=2
```

The final result must respect Discord message and embed limits.

Long results may be truncated or continued through pagination.

---

## 36. Semantic Overlap Deduplication

Overlapping chunks may produce nearly identical results.

Example:

```text
chunk 18: paragraphs 81–89
chunk 19: paragraphs 87–95
```

If two results:

* belong to the same chapter
* overlap by at least 50 percent

then keep the higher-scoring result or merge their ranges.

Deduplication must happen before pagination.

---

## 37. Semantic Result Ordering

Sort by:

```text
semantic score DESC
```

Tie-breakers:

```text
chapter number ASC
start paragraph ASC
```

---

## 38. Semantic Search Pagination

Expected behaviour:

```text
1 result per page
up to 10 pages initially
```

The complete bounded semantic result set may be held in memory for the pagination session.

---

## 39. Optional Reranking

A semantic reranker is not required initially.

A future implementation may rerank the top Qdrant candidates using:

* cross-encoder
* hosted reranking API
* local ONNX reranker

The search-service interface should allow this to be added later.

---

# Shared Search Models

## 40. Search Result Types

```python
from typing import Literal


SearchResultType = Literal[
    "exact",
    "fuzzy",
    "semantic",
]
```

---

## 41. Shared Search Result Model

```python
from dataclasses import dataclass


@dataclass
class SearchResult:
    fic_id: str
    version_id: str

    chapter_id: str
    chapter_number: int
    chapter_title: str | None

    start_position: int
    end_position: int

    matched_text: str
    context_before: str | None
    context_after: str | None

    result_type: SearchResultType

    fuzzy_score: float | None = None
    semantic_score: float | None = None

    source_line_id: str | None = None
    source_chunk_id: str | None = None
```

Exact results do not require a score.

Fuzzy results use `fuzzy_score`.

Semantic results use `semantic_score`.

---

## 42. Search Response Model

```python
@dataclass
class SearchResults:
    query_id: str

    fic_id: str
    version_id: str

    search_type: SearchResultType

    total_matches: int
    returned_results: int
    results_truncated: bool

    results: list[SearchResult]
```

For semantic search, `total_matches` may equal the number of bounded candidates returned.

---

## 43. Search Service Interface

```python
from typing import Protocol


class SearchService(Protocol):
    async def search_exact(
        self,
        fic_id: str,
        query: str,
        *,
        limit: int = 100,
    ) -> SearchResults:
        ...

    async def search_fuzzy(
        self,
        fic_id: str,
        query: str,
        *,
        limit: int = 100,
    ) -> SearchResults:
        ...

    async def search_semantic(
        self,
        fic_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> SearchResults:
        ...
```

---

## 44. Repository Interfaces

```python
class QuoteSearchRepository(Protocol):
    async def search_exact(
        self,
        fic_id: str,
        version_id: str,
        normalized_query: str,
        limit: int,
    ) -> tuple[list["LineMatch"], int]:
        ...

    async def get_fuzzy_candidates(
        self,
        fic_id: str,
        version_id: str,
        normalized_query: str,
        limit: int,
    ) -> list["LineCandidate"]:
        ...

    async def fetch_line_context(
        self,
        chapter_id: str,
        line_number: int,
        previous_lines: int,
        next_lines: int,
    ) -> "LineContext":
        ...

    async def fetch_chunk_context(
        self,
        chapter_id: str,
        start_paragraph: int,
        end_paragraph: int,
        previous_paragraphs: int,
        next_paragraphs: int,
    ) -> "ParagraphContext":
        ...


class VectorStore(Protocol):
    async def search(
        self,
        vector: list[float],
        fic_id: str,
        version_id: str,
        limit: int,
    ) -> list["VectorMatch"]:
        ...
```

---

# Pagination

## 45. Existing Pagination

The existing paginator should be reused where practical.

The paginator must accept a structured result list rather than knowing search implementation details.

Suggested input:

```text
SearchResults.results
```

The paginator should not directly query Neon or Qdrant.

---

## 46. Results Per Page

Initial behaviour:

```text
exact:   1 result per page
fuzzy:   1 result per page
semantic: 1 result per page
```

This preserves the old quote-finder interaction model.

---

## 47. Search Sessions

Pagination interactions occur after the original command.

A short-lived search session should be created.

Suggested fields:

```text
query_id
requesting_user_id
guild_id
channel_id
fic_id
version_id
search_type
result_ids
created_at
expires_at
```

Initial storage may be in memory.

Losing pagination state after bot restart is acceptable for the first release.

---

## 48. Search Session Expiry

Recommended TTL:

```text
15 to 30 minutes
```

After expiration, pagination should return a friendly expired-session message.

---

## 49. Version Changes During Pagination

The search session must retain the version ID used during the original query.

Preferred behaviour:

* allow pagination against the archived version
* retain old versions longer than the search-session TTL

If the old version has already been removed, return an expired-result response.

---

# Performance and Limits

## 50. Performance Targets

Expected normal response times:

```text
exact search:
under 1 second

fuzzy search:
under 2 seconds

semantic search:
under 3 seconds
```

These are targets, not hard guarantees during provider outages or cold starts.

---

## 51. Rate Limits

Suggested per-user defaults:

```text
!qe:
10 requests per minute

!qf:
10 requests per minute

!qs:
5 requests per minute
```

Semantic search is more expensive and should have a stricter limit.

---

## 52. Concurrency Limits

Suggested initial limits:

```text
exact search:
normal database connection-pool limits

fuzzy search:
5 concurrent searches

semantic search:
3 concurrent searches
```

These values should be configurable.

---

## 53. Timeouts

Suggested defaults:

```text
exact database query: 5 seconds
fuzzy candidate query: 5 seconds
fuzzy scoring: 5 seconds
query embedding: 10 seconds
Qdrant query: 5 seconds
context fetch: 5 seconds
overall semantic search: 15 seconds
```

---

# Error Handling

## 54. Error Codes

Suggested internal errors:

```text
fic_not_selected
fic_not_found
fic_has_no_active_version
query_empty
query_too_short
query_too_long
invalid_query
database_unavailable
vector_store_unavailable
embedding_provider_unavailable
embedding_model_mismatch
search_timeout
search_session_expired
search_failed
```

The Discord specification defines user-facing wording.

---

## 55. No-Result Behaviour

### Exact search

Return an empty exact result set.

Do not automatically run fuzzy search.

### Fuzzy search

Return an empty fuzzy result set when no candidate meets the threshold.

Do not automatically run semantic search.

### Semantic search

Return an empty semantic result set when no suitable candidates exist.

Do not manufacture an answer.

---

# Observability

## 56. Search Logging

Log:

```text
query_id
fic_id
version_id
search_type
query_length
candidate_count
returned_result_count
duration_ms
database_duration_ms
fuzzy_scoring_duration_ms
embedding_duration_ms
qdrant_duration_ms
error_code
```

Do not log full user queries by default.

A query hash may be logged for correlation.

---

## 57. Search Metrics

Recommended metrics:

```text
search_exact_requests_total
search_fuzzy_requests_total
search_semantic_requests_total

search_exact_no_results_total
search_fuzzy_no_results_total
search_semantic_no_results_total

search_failures_total

search_exact_duration_seconds
search_fuzzy_duration_seconds
search_semantic_duration_seconds

fuzzy_candidates_total
semantic_candidates_total
```

Structured logs are sufficient initially.

---

# Testing

## 58. Exact Search Tests

Test:

* exact casing
* different casing
* curly quotes
* straight quotes
* apostrophe variants
* dash variants
* repeated whitespace
* common phrase with more than 100 matches
* no matches
* chapter boundaries
* next-line context
* multiple fics
* inactive version exclusion

---

## 59. Fuzzy Search Tests

Test:

* one misspelled word
* several misspelled words
* omitted words
* inserted words
* changed punctuation
* partial remembered quote
* slightly reordered words
* threshold boundary
* more than 100 fuzzy matches
* identical fuzzy scores
* no candidate above threshold
* multiple fics
* inactive version exclusion

The test suite should include known examples from the old bot to preserve behaviour.

---

## 60. Semantic Search Tests

Test:

* vague action scene
* emotional scene
* remembered conversation
* several similar scenes
* overlapping chunk results
* irrelevant query
* wrong fic filter
* wrong version filter
* embedding model mismatch
* embedding-provider timeout
* Qdrant timeout
* context expansion

---

## 61. Semantic Relevance Benchmark

Maintain a small curated benchmark.

Example:

```json
[
  {
    "query": "Harry pretends to be fine and collapses after everyone leaves",
    "expected_chapters": [42],
    "notes": "hospital aftermath"
  }
]
```

Suggested measurements:

```text
Recall@5
Recall@10
Mean Reciprocal Rank
```

Formal evaluation is optional, but manual benchmark queries are strongly recommended.

---

# Configuration

## 62. Suggested Configuration

```text
QUOTE_EXACT_MAX_QUERY_LENGTH
QUOTE_EXACT_MAX_RESULTS

QUOTE_FUZZY_MAX_QUERY_LENGTH
QUOTE_FUZZY_MAX_RESULTS
QUOTE_FUZZY_CANDIDATE_LIMIT
QUOTE_FUZZY_MIN_SCORE
QUOTE_FUZZY_SCORER

QUOTE_CONTEXT_PREVIOUS_LINES
QUOTE_CONTEXT_NEXT_LINES

SCENE_SEARCH_MAX_QUERY_LENGTH
SCENE_SEARCH_TOP_K
SCENE_SEARCH_MAX_RESULTS
SCENE_SEARCH_MIN_SCORE

SCENE_CONTEXT_PARAGRAPHS_BEFORE
SCENE_CONTEXT_PARAGRAPHS_AFTER

SEARCH_SESSION_TTL_SECONDS
SEARCH_ACTIVE_VERSION_CACHE_TTL
SEARCH_MAX_CONCURRENT_FUZZY
SEARCH_MAX_CONCURRENT_SEMANTIC
```

---

# Acceptance Criteria

## 63. Exact Search Acceptance Criteria

Exact search is complete when:

1. `!qe` performs normalized literal matching.
2. Search is scoped to one fic and active version.
3. Source text is returned unchanged.
4. Matching is case-insensitive.
5. Punctuation normalization works.
6. Results preserve story order.
7. Up to 100 results are returned.
8. More than 100 matches are reported as truncated.
9. The matched line and next line are returned.
10. Existing pagination works.
11. No fuzzy or semantic fallback occurs.

---

## 64. Fuzzy Search Acceptance Criteria

Fuzzy search is complete when:

1. `!qf` performs lexical approximate matching.
2. The existing fuzzy behaviour is documented.
3. Postgres narrows candidates.
4. RapidFuzz or the selected scorer ranks candidates.
5. Results below the threshold are excluded.
6. Up to 100 results are returned.
7. Results are ordered by similarity.
8. The matched line and next line are returned.
9. Existing pagination works.
10. Approximate matches are not labelled exact.
11. No semantic fallback occurs.

---

## 65. Semantic Search Acceptance Criteria

Semantic search is complete when:

1. `!qs` embeds the user query.
2. The query model matches the indexed model.
3. Qdrant filters by fic and active version.
4. Multiple candidate chunks are retrieved.
5. Overlapping chunks are deduplicated.
6. Canonical text is fetched from Neon.
7. Surrounding paragraphs are returned.
8. Results are ranked by semantic similarity.
9. Existing pagination works.
10. No generated prose is returned.
11. No exact or fuzzy fallback occurs.

---

## 66. Final Search Rules

```text
!qe
→ normalized literal quote matching
→ up to 100 results
→ story order
→ matched line plus next line

!qf
→ fuzzy lexical quote matching
→ up to 100 results
→ similarity order
→ matched line plus next line

!qs
→ semantic scene retrieval
→ top candidate scenes
→ similarity order
→ chunk plus surrounding paragraphs
```

All three commands must return original source text.

Exact, fuzzy, and semantic behaviour must remain separate.

The bot retrieves what the author wrote.

It does not invent what the user hoped the author wrote.
