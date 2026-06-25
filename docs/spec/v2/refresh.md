# Quote Finder Refresh Specification

## 1. Purpose

This document defines the automated refresh pipeline for the Quote Finder revamp.

The refresh system keeps configured FanFiction.net stories synchronized with the latest EPUB available through FicHub.

A refresh may:

* determine that the story is unchanged
* create and activate a complete replacement version
* fail without affecting the currently active version

The refresh system must never modify or delete the active searchable version before a replacement version has been fully ingested and validated.

---

## 2. Scope

This specification covers:

* refresh configuration per fic
* refresh scheduling
* selecting due fics
* claiming refresh jobs
* concurrency control
* downloading the latest EPUB
* detecting unchanged stories
* invoking the ingestion pipeline
* activating replacement versions
* recording refresh outcomes
* retry scheduling
* stale-job recovery
* old-version cleanup
* manual refresh requests
* refresh observability
* future incremental refresh support

This specification does not define:

* EPUB parsing
* paragraph extraction
* semantic chunking
* embedding generation details
* exact, fuzzy, or semantic search behaviour
* Discord command presentation
* deployment infrastructure

Those are defined in separate specifications.

---

## 3. Core Refresh Rule

The refresh pipeline must follow this rule:

```text
download latest EPUB
→ compare with current source state
→ build new version separately
→ validate new version
→ atomically activate new version
→ retain old version temporarily
→ clean old version later
```

It must never use this flow:

```text
delete active chapters
→ delete active vectors
→ download replacement
→ attempt rebuild
```

The active version remains searchable throughout refresh processing.

---

## 4. High-Level Refresh Flow

```text
Scheduler wakes
      ↓
Select fics due for refresh
      ↓
Claim one fic
      ↓
Create refresh job
      ↓
Download latest FicHub EPUB
      ↓
Calculate EPUB hash
      ↓
Compare with active version
      ├── unchanged
      │     ↓
      │  record successful check
      │     ↓
      │  schedule next refresh
      │     ↓
      │  delete temporary EPUB
      │
      └── changed
            ↓
         invoke ingestion service
            ↓
         build replacement version
            ↓
         validate Neon and Qdrant data
            ↓
         atomically activate replacement
            ↓
         mark previous version archived
            ↓
         schedule old-version cleanup
            ↓
         delete temporary EPUB
```

---

## 5. Refresh Configuration

Each fic must store refresh configuration.

Suggested fields on `fics`:

```text
auto_refresh_enabled
refresh_interval_hours
next_refresh_at
last_checked_at
last_refreshed_at
last_refresh_status
last_refresh_error
refresh_started_at
refresh_completed_at
consecutive_refresh_failures
active_refresh_job_id
```

Suggested defaults:

```text
auto_refresh_enabled = false
refresh_interval_hours = 24
consecutive_refresh_failures = 0
```

Automatic refresh should be opt-in for each fic.

---

## 6. Naming

Use:

```text
auto_refresh_enabled
```

instead of:

```text
run_cron
```

`run_cron` describes one possible implementation.

`auto_refresh_enabled` describes the intended behaviour.

The scheduler may later be implemented using:

* cron
* a `systemd` timer
* a worker loop
* a CI schedule
* another job runner

The database schema should not depend on the scheduling mechanism.

---

## 7. Refresh Interval

Each fic may define:

```text
refresh_interval_hours
```

Suggested allowed range:

```text
minimum: 6 hours
maximum: 720 hours
default: 24 hours
```

The initial implementation may refresh all enabled fics once per day.

Very frequent refreshes are unnecessary because fanfiction updates are not high-frequency market data, despite readers occasionally behaving otherwise.

---

## 8. Next Refresh Time

The scheduler should use:

```text
next_refresh_at
```

A fic is eligible when:

```sql
auto_refresh_enabled = TRUE
AND next_refresh_at <= NOW()
```

If `next_refresh_at` is null and auto-refresh is enabled, the scheduler may treat the fic as immediately due.

---

## 9. Scheduler Frequency

The scheduler may wake more frequently than each fic’s refresh interval.

Suggested scheduler frequency:

```text
every 15 minutes
```

or:

```text
every hour
```

The scheduler only processes fics whose `next_refresh_at` has passed.

This allows per-fic intervals without creating one cron entry per story.

---

## 10. Scheduler Responsibilities

The scheduler is responsible for:

* finding due fics
* claiming refresh work
* respecting concurrency limits
* invoking the refresh service
* recording scheduler-level failures
* not duplicating active jobs

The scheduler must not:

* parse EPUB files
* generate embeddings directly
* manipulate active chapter rows
* duplicate ingestion logic

---

## 11. Refresh Job Model

Each refresh attempt should have a durable job record.

Suggested table:

```text
refresh_jobs
```

Suggested fields:

```text
id
fic_id
trigger
status
scheduled_at
claimed_at
started_at
completed_at
failed_at
worker_id
attempt_number
source_epub_hash
previous_version_id
created_version_id
failure_stage
failure_code
failure_message
next_retry_at
created_at
updated_at
```

Possible triggers:

```text
scheduled
manual
initial
retry
admin
```

Possible statuses:

```text
pending
claimed
downloading
checking
ingesting
validating
activating
unchanged
completed
failed
cancelled
stale
```

---

## 12. Claiming Due Fics

Refresh jobs must be claimed safely so two workers do not refresh the same fic.

Recommended PostgreSQL pattern:

```sql
SELECT id
FROM fics
WHERE auto_refresh_enabled = TRUE
  AND next_refresh_at <= NOW()
  AND active_refresh_job_id IS NULL
ORDER BY next_refresh_at ASC
FOR UPDATE SKIP LOCKED
LIMIT :limit;
```

After selecting a fic:

1. create a refresh job
2. set `active_refresh_job_id`
3. commit the claim
4. begin refresh processing

---

## 13. One Refresh Per Fic

Only one refresh may run for a given fic at a time.

Required invariant:

```text
one active refresh job per fic
```

Possible enforcement:

* `active_refresh_job_id` on `fics`
* PostgreSQL advisory lock
* unique partial index on active jobs
* row locking

Using more than one mechanism is acceptable if it remains understandable.

A distributed lock system is not required.

---

## 14. Global Concurrency

The initial implementation should use low refresh concurrency.

Recommended:

```text
global refresh concurrency = 1
```

Later:

```text
2 to 3 concurrent fics
```

may be allowed after measuring:

* FicHub reliability
* embedding-provider limits
* Neon write throughput
* Qdrant limits
* server memory usage

Refreshing several giant fics in parallel merely proves that failure can be parallelized.

---

## 15. Manual Refresh

A fic may be refreshed manually regardless of `auto_refresh_enabled`.

Manual refresh should create a normal refresh job with:

```text
trigger = manual
```

Manual refresh options may include:

```text
force
activate
skip_hash_check
keep_failed_version
```

Suggested internal call:

```python
await refresh_service.request_refresh(
    fic_id=fic_id,
    trigger="manual",
    force=False,
)
```

---

## 16. Force Refresh

A forced refresh may rebuild a fic even when the downloaded EPUB hash matches the active version.

Use cases:

* parser changes
* chunking changes
* embedding-model migration
* data repair
* validation testing

A forced refresh must still:

* build a new version
* validate the new version
* avoid modifying the active version in place
* preserve rollback capability

---

## 17. Refresh Preconditions

Before downloading, the refresh service must verify:

* fic exists
* source is supported
* source story ID exists
* no other refresh is active
* active version exists, unless this is initial ingestion
* required providers are configured
* refresh is not administratively disabled

If a fic has no active version, the refresh job may invoke initial ingestion rather than update logic.

---

## 18. EPUB Download

The refresh service downloads the complete latest EPUB through the shared FicHub client.

The complete EPUB is expected.

The refresh pipeline does not require FicHub to provide incremental chapter updates.

Download destination:

```text
/tmp/quote-finder/
  refresh_<job-id>/
    story.epub
```

The download must use the same safety controls defined in the ingestion specification.

---

## 19. Temporary Files

Refresh temporary files must be scoped to the refresh job.

Suggested layout:

```text
/tmp/quote-finder/
  <fic-id>/
    <refresh-job-id>/
      story.epub.part
      story.epub
      metadata.json
```

Temporary files must be removed after:

* unchanged result
* successful ingestion
* failed ingestion
* cancellation
* timeout

Cleanup should run in a `finally`-equivalent path.

---

## 20. EPUB Hash Check

After download, calculate:

```text
SHA-256(epub bytes)
```

Compare with the active version’s:

```text
epub_hash
```

If equal and `force = false`:

```text
status = unchanged
```

No new version should be created.

No chapters should be rewritten.

No embeddings should be generated.

No Qdrant points should be inserted.

---

## 21. Unchanged Refresh Result

When unchanged:

Update:

```text
last_checked_at
last_refresh_status
last_refresh_error
refresh_completed_at
next_refresh_at
consecutive_refresh_failures
```

Suggested values:

```text
last_refresh_status = unchanged
consecutive_refresh_failures = 0
next_refresh_at = NOW() + refresh_interval
```

The refresh job status becomes:

```text
unchanged
```

The temporary EPUB is deleted.

---

## 22. Changed Refresh Result

If the EPUB hash differs:

1. record the new hash on the refresh job
2. invoke the ingestion service
3. create a replacement fic version
4. build all canonical text
5. build semantic chunks
6. generate all embeddings
7. upload vectors
8. validate version
9. activate replacement
10. archive old version
11. schedule cleanup

The initial implementation performs a full rebuild.

---

## 23. Initial Full-Rebuild Strategy

For version one, every changed EPUB triggers:

```text
complete EPUB parse
complete chapter replacement
complete paragraph replacement
complete search-line replacement
complete chunk replacement
complete embedding regeneration
complete Qdrant version upload
```

This is intentionally simple.

The system must not attempt chapter-level patching in the first implementation.

---

## 24. Why Full Rebuild First

A full rebuild avoids errors involving:

* changed chapter numbering
* inserted chapters
* deleted chapters
* renamed chapters
* edited old chapters
* shifted paragraph IDs
* changed chunk boundaries
* stale vectors
* mixed parser versions

The workload is small enough that correctness is more important than saving a few minutes of occasional batch processing.

---

## 25. Replacement Version Creation

The refresh job must create a new version.

Example:

```text
active version: v12
replacement version: v13
```

The replacement begins as:

```text
status = building
```

All new records reference `v13`.

The active `v12` remains untouched.

---

## 26. Refresh-to-Ingestion Contract

The refresh service should call the ingestion service through a structured request.

Suggested model:

```python
@dataclass
class IngestionRequest:
    fic_id: str
    source_story_id: str
    epub_path: Path
    epub_hash: str
    activate: bool
    force: bool
    trigger: str
    refresh_job_id: str | None
    previous_version_id: str | None
```

The refresh service decides when ingestion should run.

The ingestion service decides how to build the replacement version.

---

## 27. Validation

The replacement version must pass all ingestion validation.

Refresh-specific validation should additionally compare the replacement with the current active version.

Suggested comparisons:

```text
chapter count
paragraph count
search-line count
chunk count
word count
first chapter
last chapter
source story ID
embedding model
vector count
```

---

## 28. Suspicious Shrink Detection

The refresh pipeline must detect unexpectedly smaller replacements.

Suggested warnings:

```text
new chapter count < old chapter count
new word count < 80% of old word count
new paragraph count < 80% of old paragraph count
new chunk count unexpectedly low
```

By default, suspicious shrink conditions should prevent automatic activation.

The version may remain:

```text
ready_with_warnings
```

or:

```text
failed_validation
```

Manual forced activation may be allowed.

---

## 29. Legitimate Shrink Cases

Authors may:

* delete chapters
* rewrite the story
* replace the story with a shorter version
* remove author notes
* restructure content

Therefore, shrink detection is a safety mechanism, not proof of corruption.

Manual review and forced activation must be supported.

---

## 30. Atomic Activation

Activation must update the active version atomically in Neon.

Suggested transaction:

```sql
BEGIN;

SELECT active_version_id
FROM fics
WHERE id = :fic_id
FOR UPDATE;

UPDATE fic_versions
SET status = 'archived'
WHERE id = :old_version_id;

UPDATE fic_versions
SET status = 'active',
    activated_at = NOW()
WHERE id = :new_version_id;

UPDATE fics
SET active_version_id = :new_version_id,
    last_checked_at = NOW(),
    last_refreshed_at = NOW(),
    last_refresh_status = 'success',
    last_refresh_error = NULL,
    consecutive_refresh_failures = 0,
    active_refresh_job_id = NULL,
    next_refresh_at = NOW() + :refresh_interval
WHERE id = :fic_id;

COMMIT;
```

Activation must not occur before Qdrant validation succeeds.

---

## 31. Optimistic Activation Guard

The refresh job should record:

```text
previous_version_id
```

Before activation, verify that the fic still points to that version.

Example:

```sql
UPDATE fics
SET active_version_id = :new_version_id
WHERE id = :fic_id
  AND active_version_id = :previous_version_id;
```

If zero rows are updated, another process changed the active version.

The activation must stop rather than overwriting a newer version.

---

## 32. Qdrant Readiness

Before activation, verify:

* expected Qdrant point count exists
* all points use the replacement version ID
* vector dimensions are correct
* collection is reachable
* a test query can filter the version if desired

Neon activation must not point users to a version whose semantic vectors are incomplete.

---

## 33. Exact and Fuzzy Search Readiness

Before activation, verify that replacement data contains:

* chapters
* paragraphs
* search lines
* normalized search text
* required indexes or searchable rows

A simple smoke test should run against the replacement version.

Example:

```text
select first non-empty search line
search for a substring from that line
confirm at least one result
```

---

## 34. Semantic Smoke Test

A semantic smoke test may:

1. select one replacement chunk
2. embed a short excerpt from that chunk
3. search Qdrant filtered to the replacement version
4. confirm the expected chunk appears near the top

This is optional but useful for validating provider compatibility.

---

## 35. Successful Refresh Completion

After activation:

```text
refresh_jobs.status = completed
```

Update:

```text
completed_at
created_version_id
source_epub_hash
```

The fic should contain:

```text
last_refresh_status = success
last_refresh_error = null
last_refreshed_at = now
next_refresh_at = now + configured interval
```

---

## 36. Failure Behaviour

Any refresh failure must preserve the current active version.

Examples:

* FicHub unavailable
* download timeout
* invalid EPUB
* parser failure
* database failure
* embedding failure
* Qdrant failure
* validation failure
* activation conflict
* worker crash

The replacement version must remain inactive.

---

## 37. Failure Recording

On failure, record:

```text
status = failed
failure_stage
failure_code
failure_message
failed_at
attempt_number
next_retry_at
```

Update the fic:

```text
last_refresh_status = failed
last_refresh_error = sanitized message
consecutive_refresh_failures += 1
active_refresh_job_id = null
```

Do not store secrets or full story content in errors.

---

## 38. Failure Stages

Suggested failure stages:

```text
claim
download
hash
epub_validation
parse
persist_text
chunk
embedding
persist_vectors
version_validation
activation
cleanup
unknown
```

Failure stage should be machine-readable.

---

## 39. Retry Policy

Transient failures may be retried.

Suggested retry delays:

```text
attempt 1: 15 minutes
attempt 2: 1 hour
attempt 3: 6 hours
attempt 4: 24 hours
```

After the maximum automatic retries, resume the normal refresh interval or require manual attention.

Suggested maximum immediate retries:

```text
3
```

---

## 40. Retryable Errors

Retry automatically for:

* connection timeout
* HTTP 429
* HTTP 502
* HTTP 503
* HTTP 504
* temporary Neon connectivity error
* temporary Qdrant connectivity error
* temporary embedding-provider error

Do not automatically retry indefinitely for:

* corrupted EPUB
* unsupported EPUB structure
* invalid source story ID
* embedding-dimension mismatch
* database constraint violation
* suspicious shrink validation
* parser bug

---

## 41. Exponential Backoff

Provider-level retries inside one job should use bounded exponential backoff.

Example:

```text
2 seconds
5 seconds
15 seconds
```

Job-level retries should use the longer schedule defined above.

Do not combine large provider retries with large job retries in a way that leaves one refresh hanging for hours.

---

## 42. Consecutive Failure Handling

Track:

```text
consecutive_refresh_failures
```

Suggested behaviour:

```text
1 to 2 failures:
normal retry

3 failures:
mark warning

5 failures:
pause automatic refresh or notify administrator
```

Automatic pausing is optional.

The system must avoid hammering a permanently invalid source forever.

---

## 43. Stale Job Detection

A worker may crash while a job is marked active.

A job is stale when:

```text
status is active
AND updated_at < NOW() - stale_timeout
```

Suggested stale timeout:

```text
2 hours
```

The exact timeout depends on expected ingestion duration.

---

## 44. Stale Job Recovery

When a stale job is found:

1. mark job as `stale`
2. clear `fics.active_refresh_job_id`
3. mark incomplete replacement version failed or abandoned
4. schedule retry if appropriate
5. clean temporary artifacts if accessible

The active version remains unchanged.

---

## 45. Worker Heartbeat

Long-running refresh jobs should update:

```text
updated_at
```

or:

```text
heartbeat_at
```

Suggested heartbeat interval:

```text
30 to 60 seconds
```

This helps distinguish a slow valid job from a dead worker.

---

## 46. Cancellation

Administrative cancellation may be supported.

Cancellation should:

* stop further processing where safe
* mark the job cancelled
* leave active version unchanged
* mark incomplete replacement version abandoned
* clean temporary files
* clear active job state

Cancellation does not need to interrupt an in-flight provider request immediately.

---

## 47. Cleanup Strategy

Old versions must be removed separately from activation.

Cleanup should target:

* archived Neon version data
* archived Qdrant points
* failed versions past retention
* abandoned versions
* expired temporary artifacts

Cleanup must never delete:

* the active version
* a version referenced by a live search session, where supported
* a replacement version still being validated

---

## 48. Version Retention

Suggested retention policy:

```text
keep active version
keep previous archived version
delete older archived versions after 24 to 72 hours
```

A simple initial policy:

```text
retain the latest 2 versions per fic
```

This provides rollback without accumulating endless duplicate story copies.

---

## 49. Failed-Version Retention

Suggested policy:

```text
retain failed version metadata for 7 days
delete failed paragraphs, chunks, and vectors sooner if storage matters
```

Metadata may be useful for debugging.

Full failed datasets need not be retained indefinitely.

---

## 50. Qdrant Cleanup

Delete old Qdrant points using filters:

```text
fic_id
version_id
```

Example logical operation:

```text
delete all points where:
fic_id = ffn_1234567
version_id = archived_version
```

Cleanup must be idempotent.

Deleting an already removed version should not fail the whole cleanup job.

---

## 51. Neon Cleanup

Cleanup order should respect foreign keys.

Suggested order:

```text
search_lines
chunks
paragraphs
chapters
fic_versions
```

Use database transactions where practical.

Large deletes may be batched.

---

## 52. Rollback

Rollback means switching the fic back to a retained archived version.

Rollback prerequisites:

* Neon data still exists
* Qdrant points still exist
* version passed validation previously
* embedding model remains available

Suggested operation:

```text
active version: v13
rollback target: v12
```

Activation rules should be reused.

Do not create a separate unsafe rollback path.

---

## 53. Rollback After Bad Activation

If a newly activated version is discovered to be bad:

1. select previous retained version
2. validate that its Neon and Qdrant data still exist
3. atomically reactivate it
4. mark bad version failed or quarantined
5. disable auto-refresh if repeated
6. investigate parser or source issue

---

## 54. Refresh Status Values

Suggested fic-level status values:

```text
never_run
scheduled
running
unchanged
success
failed
paused
```

The durable job table contains more detailed stage information.

---

## 55. Refresh Status API

The application should expose a structured status model.

```python
@dataclass
class RefreshStatus:
    fic_id: str
    auto_refresh_enabled: bool
    refresh_interval_hours: int
    next_refresh_at: datetime | None
    last_checked_at: datetime | None
    last_refreshed_at: datetime | None
    last_status: str | None
    last_error: str | None
    active_job_id: str | None
    consecutive_failures: int
```

The Discord layer may use this for `!fic info` or refresh-status commands.

---

## 56. Refresh Service Interface

Suggested interface:

```python
from typing import Protocol


class RefreshService(Protocol):
    async def request_refresh(
        self,
        fic_id: str,
        *,
        trigger: str,
        force: bool = False,
    ) -> str:
        ...

    async def run_job(
        self,
        job_id: str,
    ) -> None:
        ...

    async def recover_stale_jobs(
        self,
    ) -> int:
        ...

    async def cleanup_old_versions(
        self,
    ) -> int:
        ...
```

---

## 57. Refresh Repository Interface

```python
class RefreshRepository(Protocol):
    async def claim_due_fics(
        self,
        limit: int,
        worker_id: str,
    ) -> list["RefreshJob"]:
        ...

    async def mark_job_stage(
        self,
        job_id: str,
        status: str,
        stage: str,
    ) -> None:
        ...

    async def mark_job_completed(
        self,
        job_id: str,
        created_version_id: str | None,
        unchanged: bool,
    ) -> None:
        ...

    async def mark_job_failed(
        self,
        job_id: str,
        failure_stage: str,
        failure_code: str,
        failure_message: str,
        next_retry_at: datetime | None,
    ) -> None:
        ...

    async def clear_active_job(
        self,
        fic_id: str,
        job_id: str,
    ) -> None:
        ...
```

---

## 58. Scheduler Implementation Options

Acceptable implementations:

### Option A: systemd timer

```text
systemd timer
→ run refresh CLI
→ process due fics
→ exit
```

### Option B: cron

```text
cron
→ run refresh CLI
→ process due fics
→ exit
```

### Option C: long-running worker

```text
worker loop
→ sleep
→ claim due fics
→ process jobs
```

For the initial deployment, a `systemd` timer or cron-triggered CLI is sufficient.

---

## 59. Recommended Initial Scheduler

Recommended:

```text
systemd timer every hour
```

Command:

```bash
quote-finder refresh-due --limit 1
```

Advantages:

* process exits after work
* memory is released
* failures are visible in journal logs
* no separate queue infrastructure
* simple stale-job handling
* easy manual execution

---

## 60. Example systemd Service

```ini
[Unit]
Description=Quote Finder Refresh Worker
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=quote-finder
WorkingDirectory=/opt/quote-finder
EnvironmentFile=/opt/quote-finder/.env
ExecStart=/opt/quote-finder/.venv/bin/quote-finder refresh-due --limit 1
```

---

## 61. Example systemd Timer

```ini
[Unit]
Description=Run Quote Finder refresh checks hourly

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

A randomized delay avoids every scheduled system waking at the exact same second, because apparently even servers benefit from not joining a queue with everyone else.

---

## 62. Manual CLI Commands

Suggested commands:

```bash
quote-finder refresh-due
quote-finder refresh-due --limit 5
quote-finder refresh --fic-id ffn_1234567
quote-finder refresh --fic-id ffn_1234567 --force
quote-finder refresh-status --fic-id ffn_1234567
quote-finder recover-stale-refreshes
quote-finder cleanup-versions
```

---

## 63. Automatic Refresh Enablement

Suggested command:

```bash
quote-finder fic update \
  --fic-id ffn_1234567 \
  --auto-refresh-enabled true \
  --refresh-interval-hours 24
```

The Discord admin command may provide equivalent behaviour later.

---

## 64. Initial Refresh Schedule

When automatic refresh is enabled:

```text
next_refresh_at = NOW()
```

or:

```text
next_refresh_at = NOW() + refresh_interval
```

Recommended behaviour:

* newly enabled fic: refresh immediately
* newly ingested fic: schedule after configured interval

---

## 65. Next Refresh Calculation

After success or unchanged result:

```text
next_refresh_at =
completion time + refresh interval
```

After transient failure:

```text
next_refresh_at =
retry time
```

After permanent failure:

```text
next_refresh_at =
normal interval
```

or pause auto-refresh after repeated failures.

---

## 66. Clock and Time Zones

Store all timestamps as:

```text
TIMESTAMPTZ
```

Use UTC internally.

The Discord layer may display times in guild or user-local time later.

Do not store naive timestamps.

---

## 67. Refresh Notifications

Notifications are optional.

Possible events:

* story updated successfully
* story unchanged
* refresh failed
* auto-refresh paused
* manual review required

The first implementation does not need to announce every unchanged check.

Failure notifications and successful story-update notifications may be useful.

---

## 68. Update Notification Data

When a version changes, calculate:

```text
old chapter count
new chapter count
old word count
new word count
new chapters added
```

Possible notification:

```text
Story updated from 180 to 181 chapters.
```

This data should be derived from version metadata.

---

## 69. Logging

Each refresh job must log:

```text
refresh_job_id
fic_id
trigger
worker_id
previous_version_id
created_version_id
stage
attempt_number
download_duration
epub_size
epub_hash
changed
ingestion_duration
validation_duration
activation_duration
total_duration
result
failure_code
```

Do not log:

* database credentials
* Qdrant API keys
* Discord tokens
* full EPUB content
* full story passages

---

## 70. Metrics

Recommended metrics:

```text
refresh_jobs_started_total
refresh_jobs_completed_total
refresh_jobs_unchanged_total
refresh_jobs_failed_total
refresh_jobs_stale_total
refresh_duration_seconds
refresh_download_duration_seconds
refresh_ingestion_duration_seconds
refresh_activation_duration_seconds
refresh_consecutive_failures
refresh_old_versions_cleaned_total
```

Structured logs are sufficient initially.

---

## 71. Timeouts

Suggested job timeouts:

```text
EPUB download: 2 minutes
EPUB parse: 10 minutes
embedding generation: 30 minutes
Qdrant upload: 15 minutes
overall refresh: 60 minutes
```

These values should be configurable.

The overall timeout should accommodate the largest supported fic.

---

## 72. Refresh Resource Limits

Suggested defaults:

```text
global refresh concurrency: 1
maximum EPUB size: 250 MB
maximum refresh duration: 60 minutes
embedding batch size: defined by ingestion config
Qdrant batch size: defined by ingestion config
```

The refresh worker must not load the entire EPUB and all embeddings into memory unnecessarily.

---

## 73. Provider Outage Behaviour

If FicHub is unavailable:

* active version remains searchable
* refresh job fails or retries
* next retry is scheduled
* no data is deleted

If Neon is unavailable:

* job fails safely
* no activation occurs

If Qdrant is unavailable:

* exact and fuzzy active searches remain available
* replacement version remains inactive
* semantic replacement data is retried later

If embedding provider is unavailable:

* replacement remains inactive
* current version remains active

---

## 74. Partial Ingestion Cleanup

A failed refresh may leave:

* Neon rows for an inactive version
* Qdrant points for an inactive version
* temporary files

The cleanup process should identify abandoned versions using:

```text
status IN ('failed', 'abandoned')
AND created_at < retention threshold
```

Cleanup must not rely only on temporary file presence.

---

## 75. Idempotency

Refresh operations must be safe to retry.

Required properties:

* repeated unchanged checks create no duplicate fic versions
* repeated Qdrant upserts create no duplicate points
* repeated activation of the same version is harmless or rejected clearly
* repeated cleanup does not fail
* retrying a failed job does not modify the active version
* one fic cannot acquire two simultaneous active versions

---

## 76. Version Uniqueness

A fic version should be uniquely identifiable.

Suggested fields:

```text
id
fic_id
epub_hash
parser_version
chunking_version
embedding_model
```

A unique constraint on `fic_id + epub_hash` may be too strict because forced rebuilds with a new parser or model may use the same EPUB.

A more suitable uniqueness key may include:

```text
fic_id
epub_hash
pipeline_version
embedding_model
```

---

## 77. Pipeline Version

Store:

```text
pipeline_version
```

This represents the ingestion implementation or schema version.

Example:

```text
2026-01
```

A forced refresh may rebuild the same EPUB when:

```text
pipeline_version changed
```

This supports parser and normalization migrations.

---

## 78. Embedding Model Migration

Changing the embedding model requires re-embedding the story.

The refresh pipeline may treat this as a forced rebuild.

Conditions:

```text
active embedding model != configured embedding model
```

The replacement version must be fully built and activated normally.

Do not mix vectors from different models in one active version.

---

## 79. Chunking Configuration Migration

Changing:

```text
chunk target words
chunk overlap
chunk normalization
```

should increment:

```text
pipeline_version
```

or:

```text
chunking_version
```

This may trigger a forced rebuild.

---

## 80. Future Chapter-Level Incremental Refresh

A later implementation may optimize changed stories using chapter hashes.

Possible flow:

```text
download full EPUB
→ parse all chapters
→ calculate chapter hashes
→ compare with active version
→ identify unchanged chapters
→ identify changed chapters
→ identify new chapters
→ identify removed chapters
→ rebuild only changed/new chunks
→ reuse embeddings where safe
→ construct complete replacement version
→ activate
```

The resulting version must still be complete and isolated.

---

## 81. Incremental Refresh Must Not Patch Active Data

Even with chapter-level diffing, the system must not update the active version in place.

Incremental means:

```text
reuse data while constructing a new version
```

It does not mean:

```text
mutate live chapter rows and vectors
```

---

## 82. Embedding Reuse

Future embedding reuse may use:

```text
chunk text hash
embedding model
embedding dimensions
normalization version
```

If all match, an existing vector may be copied or reused.

Embedding reuse must not occur when:

* model changed
* dimensions changed
* text changed
* normalization changed
* chunk boundaries changed

---

## 83. Chapter Insertion and Renumbering

Incremental refresh must account for chapter insertions.

Example:

```text
old:
1, 2, 3, 4

new:
1, 2, new 3, old 3 becomes 4, old 4 becomes 5
```

Chapter number alone is not a safe persistent identity.

Future diffing should use:

* chapter hash
* title
* relative order
* source document path
* content similarity

This complexity is why full rebuild comes first.

---

## 84. Database Indexes

Suggested indexes:

```sql
CREATE INDEX fics_due_refresh_idx
ON fics (next_refresh_at)
WHERE auto_refresh_enabled = TRUE;

CREATE INDEX refresh_jobs_status_idx
ON refresh_jobs (status, scheduled_at);

CREATE INDEX refresh_jobs_fic_idx
ON refresh_jobs (fic_id, created_at DESC);

CREATE INDEX fic_versions_cleanup_idx
ON fic_versions (status, created_at);
```

A unique active-job constraint should be considered.

---

## 85. Security

The refresh pipeline must:

* validate source identifiers
* use HTTPS
* restrict temporary-file permissions
* sanitize downloaded filenames
* prevent ZIP path traversal
* avoid executing EPUB content
* redact secrets from logs
* restrict manual refresh commands
* limit refresh concurrency
* limit file and extraction sizes

---

## 86. Configuration

Suggested configuration:

```text
REFRESH_SCHEDULER_INTERVAL_MINUTES
REFRESH_DEFAULT_INTERVAL_HOURS
REFRESH_MIN_INTERVAL_HOURS
REFRESH_MAX_INTERVAL_HOURS

REFRESH_MAX_CONCURRENCY
REFRESH_STALE_JOB_TIMEOUT_MINUTES
REFRESH_JOB_TIMEOUT_MINUTES

REFRESH_MAX_ATTEMPTS
REFRESH_RETRY_DELAY_MINUTES
REFRESH_PAUSE_AFTER_FAILURES

REFRESH_VERSION_RETENTION_COUNT
REFRESH_ARCHIVED_RETENTION_HOURS
REFRESH_FAILED_RETENTION_DAYS

REFRESH_ENABLE_SHRINK_GUARD
REFRESH_MIN_WORD_COUNT_RATIO
REFRESH_MIN_PARAGRAPH_COUNT_RATIO

REFRESH_NOTIFY_SUCCESS
REFRESH_NOTIFY_FAILURE
```

---

## 87. Initial Implementation Order

Recommended order:

1. add refresh fields to `fics`
2. add `refresh_jobs`
3. implement manual refresh request
4. implement FicHub download and hash comparison
5. invoke ingestion for changed EPUB
6. activate replacement safely
7. record unchanged checks
8. add retry handling
9. add `systemd` timer
10. add stale-job recovery
11. add archived-version cleanup
12. add rollback command
13. add notifications
14. consider incremental refresh later

---

## 88. Refresh Tests

Test:

* auto-refresh disabled
* fic not yet due
* fic due
* two workers claim jobs
* duplicate refresh request
* unchanged EPUB
* changed EPUB
* invalid EPUB
* FicHub timeout
* embedding-provider failure
* Neon failure
* Qdrant failure
* suspicious chapter-count reduction
* successful activation
* activation conflict
* old version remains searchable
* stale-job recovery
* retry scheduling
* failed-version cleanup
* archived-version cleanup
* rollback
* forced refresh with identical EPUB
* pipeline-version rebuild

---

## 89. Unchanged Refresh Acceptance Criteria

An unchanged refresh is complete when:

1. the EPUB downloads successfully
2. the EPUB hash matches the active version
3. no new version is created
4. no embeddings are generated
5. no Qdrant points are inserted
6. `last_checked_at` is updated
7. `next_refresh_at` is scheduled
8. the refresh job is marked unchanged
9. the temporary EPUB is deleted
10. the active version remains unchanged

---

## 90. Changed Refresh Acceptance Criteria

A changed refresh is complete when:

1. the EPUB hash differs
2. a replacement version is created
3. the complete story is ingested
4. exact-search data is created
5. fuzzy-search data is created
6. semantic chunks are created
7. all embeddings are generated
8. Qdrant points are uploaded
9. replacement validation succeeds
10. activation occurs atomically
11. previous version becomes archived
12. old version is retained temporarily
13. refresh status is recorded
14. next refresh is scheduled
15. temporary files are deleted

---

## 91. Failure Acceptance Criteria

Refresh failure handling is complete when:

1. the active version remains searchable
2. the replacement version is not activated
3. the failure stage is recorded
4. the error is sanitized
5. retry state is recorded
6. temporary files are cleaned
7. the fic’s active job is cleared
8. stale jobs can be recovered
9. repeated failures do not create duplicate active jobs
10. automatic refresh can be paused after repeated failures

---

## 92. Final Refresh Rules

```text
auto_refresh_enabled
→ controls whether the scheduler checks a fic

next_refresh_at
→ controls when the fic becomes eligible

EPUB hash unchanged
→ record check
→ do not rebuild

EPUB hash changed
→ create complete replacement version
→ rebuild text and vectors
→ validate
→ atomically activate

refresh failure
→ preserve active version

old version
→ retain temporarily
→ clean asynchronously
```

The refresh pipeline downloads the complete EPUB.

The initial implementation fully rebuilds changed stories.

It does not delete active chapters first.

It does not mutate live search data in place.

A replacement becomes searchable only after the entire ingestion and validation process succeeds.
