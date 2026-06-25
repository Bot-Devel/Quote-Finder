# Quote Finder Discord Specification

## 1. Purpose

This document defines the Discord-facing behaviour for the Quote Finder revamp.

The Discord bot must expose three primary search commands:

```text
!qe <query>   exact quote search
!qf <query>   fuzzy quote search
!qs <query>   semantic scene search
```

The Discord layer is responsible for:

* receiving commands
* resolving the selected fic
* validating user input
* calling the search service
* formatting search results
* managing pagination
* exposing fic-management commands
* exposing refresh-management commands
* enforcing permissions
* presenting errors and status messages

The Discord layer must not:

* parse EPUB files
* generate document embeddings
* manipulate raw Neon or Qdrant records directly
* contain provider-specific ingestion logic
* implement search algorithms itself

---

## 2. Scope

This specification covers:

* public commands
* aliases
* command arguments
* fic selection
* guild and channel defaults
* exact-search interaction
* fuzzy-search interaction
* semantic-search interaction
* pagination
* result formatting
* administrative permissions
* fic-management commands
* refresh commands
* loading states
* errors
* cooldowns
* interaction expiry
* observability
* backward compatibility

This specification does not cover:

* EPUB parsing
* ingestion internals
* refresh worker implementation
* database schema details
* embedding-provider implementation
* deployment infrastructure

Those are defined separately.

---

## 3. Discord Command Style

The initial release should preserve prefix commands.

Default prefix:

```text
!
```

Primary commands:

```text
!qe
!qf
!qs
```

The bot may later add slash-command equivalents, but prefix commands remain supported unless explicitly deprecated.

---

## 4. Primary Search Commands

## 4.1 Exact Quote Search

Command:

```text
!qe <query>
```

Example:

```text
!qe there are no innocent men
```

Behaviour:

* resolve the active fic
* run exact normalized quote search
* return up to 100 results
* preserve story order
* show one result per page
* show matched line and next line
* reuse existing pagination behaviour

No fuzzy or semantic fallback is allowed.

---

## 4.2 Fuzzy Quote Search

Command:

```text
!qf <query>
```

Example:

```text
!qf there arent any innocent men
```

Behaviour:

* resolve the active fic
* run lexical fuzzy quote search
* return up to 100 results
* sort by similarity score
* show one result per page
* show matched line and next line

No exact or semantic fallback is implied.

---

## 4.3 Semantic Scene Search

Command:

```text
!qs <query>
```

Example:

```text
!qs the scene where Harry acts calm and collapses after everyone leaves
```

Behaviour:

* resolve the active fic
* embed the query
* run Qdrant semantic search
* retrieve canonical text from Neon
* return top scene candidates
* show one result per page
* include surrounding paragraphs
* avoid displaying raw similarity as a percentage

Initial result limit:

```text
10 results
```

---

## 5. Command Parsing

The full remaining command text after the command name is the query.

Example:

```text
!qe I solemnly swear that I am up to no good
```

Parsed query:

```text
I solemnly swear that I am up to no good
```

The parser must:

* trim leading and trailing whitespace
* collapse accidental repeated command whitespace
* preserve internal punctuation
* preserve original query for display if needed
* reject empty queries

Quoted arguments are not required.

Both should work:

```text
!qe some exact quote
!qe "some exact quote"
```

If surrounding quotes are present, they may be stripped.

---

## 6. Fic Resolution

Every search must resolve one fic.

Recommended resolution order:

1. fic explicitly specified in command
2. channel default fic
3. guild default fic
4. user-selected fic, if supported
5. return selection-required response

The initial implementation should support:

```text
channel default
guild default
explicit fic override
```

User-specific selection is optional.

---

## 7. Explicit Fic Override

A query may optionally specify a fic.

Recommended syntax:

```text
!qe --fic <fic-id-or-alias> <query>
!qf --fic <fic-id-or-alias> <query>
!qs --fic <fic-id-or-alias> <query>
```

Example:

```text
!qs --fic hp-mor Harry argues about prophecy
```

Alternative shorthand may be added later.

The command parser must avoid treating `--fic` as part of the query.

---

## 8. Fic Identifiers and Aliases

Each fic should have:

* internal fic ID
* FanFiction.net story ID
* human-readable title
* optional short alias

Example:

```text
Internal ID: ffn_5782108
Source ID: 5782108
Alias: hp-mor
Title: Harry Potter and the Methods of Rationality
```

Aliases must be unique within the bot or guild scope, depending on implementation.

Recommended initial behaviour:

```text
global unique alias
```

---

## 9. Guild Default Fic

A guild may define one default fic.

Command:

```text
!fic default <fic-id-or-alias>
```

Example:

```text
!fic default hp-mor
```

Required permission:

```text
Manage Server
```

or configured bot-admin role.

The setting is stored in Neon.

---

## 10. Channel Default Fic

A channel may override the guild default.

Command:

```text
!fic channel-default <fic-id-or-alias>
```

Example:

```text
!fic channel-default rogue-one
```

Resolution order:

```text
channel default
→ guild default
```

A channel default should be useful when different channels discuss different stories.

---

## 11. Clearing Fic Defaults

Commands:

```text
!fic clear-default
!fic clear-channel-default
```

The guild-level command clears the guild default.

The channel-level command clears the current channel override.

Required permissions should match the corresponding set commands.

---

## 12. Search Without Selected Fic

If no fic can be resolved, return:

```text
No fic is selected for this channel.

Use:
!fic list
!fic default <fic>
!fic channel-default <fic>

You can also search once with:
!qe --fic <fic> <query>
```

The message should be concise.

Do not run an unscoped cross-fic search automatically.

---

## 13. Search Result Header

Every result page should show:

* fic title
* chapter number
* chapter title, if available
* search type
* result position
* total returned results

Example:

```text
Harry Potter and the Methods of Rationality
Chapter 42: Courage

Exact match
Result 3 of 27
```

If result truncation occurred:

```text
Result 3 of 100
Showing first 100 of 237 matches
```

---

## 14. Exact Result Formatting

Exact result body should show:

```text
[matched line]
[next line]
```

The matched line should be visually distinct.

Possible formatting:

```text
**Matched line**
Next line
```

or:

```text
> Matched line
Next line
```

The final choice should respect Discord message limits and readability.

The source text must not be rewritten.

---

## 15. Fuzzy Result Formatting

Fuzzy result body should show:

```text
[matched line]
[next line]
```

Header label:

```text
Fuzzy match
```

The numeric score may be hidden by default.

Optional debug display:

```text
Similarity: 87
```

Do not display:

```text
87% accurate
```

because the score is not a correctness probability.

---

## 16. Semantic Result Formatting

Semantic result body should show:

* relevant chunk text
* context before
* context after
* chapter metadata
* result index

Suggested structure:

```text
Context before

Relevant passage

Context after
```

The passage may be truncated if required by Discord limits.

Semantic result label:

```text
Scene match
```

Do not call it an answer.

---

## 17. Result Footer

Suggested footer:

```text
Requested by <display name>
```

Optional additional footer data:

```text
Search session expires in 20 minutes
```

Avoid cluttering every result with implementation details.

---

## 18. Chapter Links

If a reliable source chapter URL can be constructed, include:

```text
Open chapter
```

URL pattern:

```text
https://www.fanfiction.net/s/<story-id>/<chapter-number>/
```

The link is optional.

The stored canonical passage remains the authoritative search result.

---

## 19. Pagination Controls

The existing pagination system should be reused where practical.

Recommended controls:

```text
First
Previous
Next
Last
Stop
```

For semantic search with few results, `First` and `Last` may be optional.

If the current bot uses reactions instead of buttons, reaction pagination may be preserved initially.

---

## 20. Pagination Ownership

Only the requesting user should control the paginator by default.

Other users clicking controls should receive:

```text
This search belongs to another user.
```

An admin override is optional.

---

## 21. Pagination Expiry

Recommended search-session lifetime:

```text
20 minutes
```

After expiry:

* disable buttons if possible
* remove reactions if practical
* preserve the displayed result
* reject further navigation

Expired response:

```text
This search session has expired. Run the command again.
```

---

## 22. Pagination After Bot Restart

The initial implementation may store search sessions in memory.

After a bot restart:

* old pagination controls may stop working
* the visible message remains
* the user must rerun the command

Persistent pagination is not required initially.

---

## 23. Pagination and Version Changes

Each search session must retain the version ID used for the original search.

If the fic refreshes during pagination:

* continue serving the archived version while retained
* otherwise return expired-result response

The paginator must not silently switch remaining pages to a newer fic version.

---

## 24. Discord Message Limits

The formatter must respect Discord limits.

Relevant practical limits include:

* message content length
* embed description length
* embed field lengths
* total embed character limits
* component limits

The formatter must:

* truncate safely
* avoid splitting Unicode incorrectly
* indicate truncation
* preserve the matched passage where possible

Suggested truncation indicator:

```text
[…]
```

---

## 25. Search Loading State

Exact search may respond immediately.

Fuzzy and semantic search may take longer.

Recommended behaviour:

1. send temporary loading message
2. perform search
3. edit loading message into result
4. on failure, edit into error state

Examples:

```text
Searching exact quotes…
```

```text
Searching fuzzy matches…
```

```text
Searching scenes…
```

Do not post several progress messages for one request.

---

## 26. Search Timeout Response

If a search exceeds its timeout:

```text
The search timed out. Try again in a moment.
```

Semantic timeout may mention provider availability only in admin/debug mode.

Do not expose internal stack traces.

---

## 27. No Exact Results

Response:

```text
No exact matches found.
```

Optional hint:

```text
Try !qf for approximate wording or !qs for a vague scene description.
```

This is a suggestion only.

The bot must not automatically run another search mode.

---

## 28. No Fuzzy Results

Response:

```text
No fuzzy matches passed the similarity threshold.
```

Optional hint:

```text
Try a longer quote or use !qs for a scene description.
```

Do not silently lower the fuzzy threshold.

---

## 29. No Semantic Results

Response:

```text
No strong scene matches were found.
```

Optional hint:

```text
Try adding characters, location, emotion, or what happened before or after.
```

Do not generate a speculative answer.

---

## 30. Query Too Short

Response:

```text
That query is too short.
```

Suggested minimum:

```text
2 characters
```

For semantic search, a higher practical minimum may be considered.

---

## 31. Query Too Long

Response:

```text
That query is too long for this search mode.
```

The response may include the allowed limit.

---

## 32. Invalid Fic

Response:

```text
I could not find that fic.

Use !fic list to see available stories.
```

Do not leak internal database IDs unless useful.

---

## 33. Fic Has No Active Version

Response:

```text
That fic has not finished indexing yet.
```

If refresh failed:

```text
The latest indexing attempt failed. The current active version is unavailable.
```

Admin-only details may include the failure stage.

---

# Fic Management Commands

## 34. Fic Command Group

Suggested command group:

```text
!fic
```

Subcommands:

```text
!fic list
!fic info <fic>
!fic add <fanfiction.net-url>
!fic remove <fic>
!fic alias <fic> <alias>
!fic default <fic>
!fic channel-default <fic>
!fic clear-default
!fic clear-channel-default
!fic refresh <fic>
!fic refresh-status <fic>
!fic enable-refresh <fic>
!fic disable-refresh <fic>
```

Not every command must ship in the first release.

---

## 35. Fic List

Command:

```text
!fic list
```

Output should include:

* alias
* title
* source story ID
* chapter count
* active status
* refresh status

Example:

```text
Available fics

hp-mor
Harry Potter and the Methods of Rationality
122 chapters

rogue-one
Some Story Title
180 chapters
```

Paginate if the list is long.

---

## 36. Fic Info

Command:

```text
!fic info <fic>
```

Output:

```text
Title
Author
FanFiction.net ID
Source URL
Alias
Active version
Chapter count
Word count
Last refreshed
Next scheduled refresh
Refresh enabled
Last refresh status
```

Do not show internal secrets or provider credentials.

---

## 37. Add Fic

Command:

```text
!fic add <fanfiction.net-url>
```

Required permission:

```text
bot admin
```

Behaviour:

1. validate URL
2. create fic record
3. trigger initial ingestion
4. report job ID or status
5. return when queued or completed, depending on architecture

Suggested immediate response:

```text
Fic added. Initial ingestion has started.
```

The command should not block for a long ingestion if a background job exists.

---

## 38. Duplicate Fic Add

If the fic already exists:

```text
That fic is already configured.
```

Optional:

```text
Use !fic refresh <fic> to rebuild it.
```

---

## 39. Remove Fic

Command:

```text
!fic remove <fic>
```

Required permission:

```text
bot admin
```

Removal is destructive and should require confirmation.

Suggested confirmation:

```text
This will remove the fic, all versions, and semantic vectors.

Confirm with:
!fic remove <fic> --confirm
```

Alternative button confirmation is preferable.

---

## 40. Fic Alias

Command:

```text
!fic alias <fic> <alias>
```

Requirements:

* alias must be unique
* lowercase normalization recommended
* allow letters, numbers, hyphens, underscores
* reject whitespace-heavy aliases
* reject reserved command words

Example:

```text
!fic alias ffn_1234567 rogue-one
```

---

# Refresh Commands

## 41. Manual Refresh

Command:

```text
!fic refresh <fic>
```

Required permission:

```text
bot admin
```

Behaviour:

* queue refresh job
* do not duplicate active refresh
* report queued status

Response:

```text
Refresh queued for <title>.
```

If already running:

```text
A refresh is already running for this fic.
```

---

## 42. Force Refresh

Command:

```text
!fic refresh <fic> --force
```

Use cases:

* parser change
* embedding-model change
* data repair
* same EPUB, new pipeline version

Required permission:

```text
bot owner or elevated admin
```

The UI should warn that this performs a full rebuild.

---

## 43. Refresh Status

Command:

```text
!fic refresh-status <fic>
```

Output:

```text
Status
Current stage
Started at
Last checked
Last refreshed
Next refresh
Consecutive failures
Last error
```

Error details should be sanitized.

---

## 44. Enable Auto Refresh

Command:

```text
!fic enable-refresh <fic> [hours]
```

Example:

```text
!fic enable-refresh hp-mor 24
```

If hours are omitted, use default interval.

Required permission:

```text
bot admin
```

Response:

```text
Automatic refresh enabled every 24 hours.
```

---

## 45. Disable Auto Refresh

Command:

```text
!fic disable-refresh <fic>
```

Behaviour:

* disable future scheduled checks
* do not cancel an already running refresh unless explicitly requested

Response:

```text
Automatic refresh disabled.
```

---

## 46. Refresh Completion Notification

Optional notification after successful changed refresh:

```text
<Title> was updated.

Chapters: 180 → 181
Words: 1,502,100 → 1,519,840
```

Unchanged checks should not spam channels.

Failure notifications may go to a configured admin channel.

---

# Permissions

## 47. Public Commands

Available to normal users:

```text
!qe
!qf
!qs
!fic list
!fic info
!fic refresh-status
```

Depending on server policy, `refresh-status` may also be admin-only.

---

## 48. Administrative Commands

Restricted commands:

```text
!fic add
!fic remove
!fic alias
!fic default
!fic channel-default
!fic clear-default
!fic clear-channel-default
!fic refresh
!fic enable-refresh
!fic disable-refresh
```

Suggested permission rule:

```text
Manage Server
OR configured bot-admin role
OR bot owner
```

---

## 49. Bot Owner Commands

Highest-risk commands:

```text
!fic remove --confirm
!fic refresh --force
!fic rollback
!fic cleanup
```

These may be restricted to the bot owner initially.

---

## 50. Configured Admin Roles

The bot may support one or more configured admin-role IDs.

Suggested setting:

```text
bot_admin_role_ids
```

Permission check order:

1. bot owner
2. guild owner
3. Discord `Manage Server`
4. configured admin role

---

# Rate Limits and Abuse Prevention

## 51. Exact Search Cooldown

Suggested:

```text
10 requests per minute per user
```

Exact search is cheap but may still return large result sets.

---

## 52. Fuzzy Search Cooldown

Suggested:

```text
10 requests per minute per user
```

Fuzzy search is more CPU-intensive than exact search.

---

## 53. Semantic Search Cooldown

Suggested:

```text
5 requests per minute per user
```

Semantic search uses an embedding provider and Qdrant.

---

## 54. Guild-Level Limits

Optional guild-level limits:

```text
30 semantic searches per minute
```

Useful if the bot becomes public.

Not required for a small private server.

---

## 55. Concurrent Search Handling

If too many semantic searches are active:

```text
Scene search is busy. Try again shortly.
```

Do not start unbounded background tasks.

---

## 56. Bot Mention and Help

Command:

```text
!qhelp
```

or:

```text
!help quote
```

Output:

```text
Quote Finder commands

!qe <quote>
Exact wording search

!qf <quote>
Approximate wording search

!qs <description>
Vague scene search

!fic list
Show available stories
```

Keep help concise.

---

## 57. Command Aliases

Optional aliases:

```text
!quote-exact → !qe
!quote-fuzzy → !qf
!quote-scene → !qs
```

The short commands remain canonical.

Do not introduce ambiguous aliases such as `!q`.

---

# Search Result State

## 58. Search Session Model

Suggested in-memory model:

```python
@dataclass
class DiscordSearchSession:
    query_id: str
    user_id: int
    guild_id: int | None
    channel_id: int
    message_id: int | None

    fic_id: str
    version_id: str
    search_type: str

    result_ids: list[str]
    current_index: int

    created_at: datetime
    expires_at: datetime
```

---

## 59. Search Session Security

A pagination event must verify:

* matching message ID
* matching session ID
* requesting user, unless admin override
* session not expired
* result version still available

---

## 60. Search Session Cleanup

Expired sessions should be removed periodically.

Suggested cleanup interval:

```text
every 5 minutes
```

No durable database table is required initially.

---

# Result Formatting Models

## 61. Discord Result View Model

The Discord layer may transform search results into:

```python
@dataclass
class DiscordResultView:
    title: str
    subtitle: str | None
    body: str
    footer: str | None
    source_url: str | None
    result_index: int
    result_count: int
    truncated: bool
```

The formatter should not receive raw database rows.

---

## 62. Exact Result View

Suggested title:

```text
Exact match
```

Suggested subtitle:

```text
Chapter 42: Courage
```

Suggested body:

```text
Matched line

Next line
```

---

## 63. Fuzzy Result View

Suggested title:

```text
Fuzzy match
```

Suggested subtitle:

```text
Chapter 42: Courage
```

Suggested body:

```text
Matched line

Next line
```

Optional debug footer:

```text
Similarity score: 87
```

---

## 64. Semantic Result View

Suggested title:

```text
Scene match
```

Suggested subtitle:

```text
Chapter 42: Courage
```

Suggested body:

```text
Context before

Relevant passage

Context after
```

---

## 65. Empty Chapter Title

If title is missing:

```text
Chapter 42
```

Do not display:

```text
Chapter 42: None
```

A surprisingly common achievement in unfinished software.

---

## 66. Text Escaping

The formatter should prevent accidental Discord formatting problems.

Consider escaping:

* mass mentions
* role mentions
* channel mentions
* unwanted Markdown
* triple backticks

At minimum, disable dangerous mentions:

```python
allowed_mentions = discord.AllowedMentions.none()
```

Story text must not trigger `@everyone`, `@here`, or user pings.

---

## 67. Story Text Markdown

Story text may contain:

* asterisks
* underscores
* backticks
* blockquotes

The formatter should either:

* escape Markdown
* wrap safely
* use embed descriptions with controlled escaping

Preserving readability is more important than preserving author formatting exactly.

---

# Error Handling

## 68. User-Facing Error Principles

Errors should be:

* concise
* actionable
* free of stack traces
* free of provider secrets
* specific enough to guide the user

Admin/debug logs may contain more detail.

---

## 69. Database Unavailable

Response:

```text
Search storage is temporarily unavailable.
```

---

## 70. Vector Store Unavailable

For `!qs`:

```text
Scene search is temporarily unavailable.
```

Exact and fuzzy commands should remain functional if Neon is available.

---

## 71. Embedding Provider Unavailable

Response:

```text
Scene search could not generate a query embedding. Try again later.
```

Do not affect `!qe` or `!qf`.

---

## 72. Refresh Failure

Admin-facing response:

```text
Refresh failed during <stage>.

The current active version is still available.
```

This reassures the administrator that the bot did not erase the fic in a fit of modernisation.

---

## 73. Internal Error ID

Unexpected failures should return a short error ID.

Example:

```text
Search failed. Error ID: QF-7A2C91
```

The same ID should appear in logs.

---

# Observability

## 74. Command Logging

Log:

```text
command_name
user_id
guild_id
channel_id
fic_id
version_id
query_length
result_count
duration_ms
success
error_code
```

Do not log full query text by default.

---

## 75. Pagination Logging

Log:

```text
query_id
action
old_index
new_index
user_id
session_expired
```

Detailed pagination logs may be debug-level only.

---

## 76. Admin Action Logging

Log:

```text
admin_user_id
guild_id
command
fic_id
refresh_job_id
result
```

Administrative destructive actions should be auditable.

---

# Backward Compatibility

## 77. Existing Commands

The revamp must preserve:

```text
!qe
!qf
```

The new semantic command is:

```text
!qs
```

Existing users should not have to learn a replacement command for exact or fuzzy search.

---

## 78. Existing Pagination

The current paginator should be reused or matched closely.

Preserve where practical:

* button or reaction behaviour
* result numbering
* chapter display
* next-result workflow
* timeout behaviour

The backend may change completely without forcing the visible interaction to become unfamiliar.

---

## 79. Existing Search Context

Current quote results show:

```text
matched line
next line
```

The revamp must preserve this minimum output for:

```text
!qe
!qf
```

Semantic search may use paragraph context instead.

---

## 80. Migration Mode

During rollout, the bot may support a hidden comparison mode.

Example:

```text
!qe-test <query>
```

or admin-only flag:

```text
!qe <query> --new
```

This can compare old and new results before full cutover.

The comparison mode is optional.

---

# Testing

## 81. Command Parsing Tests

Test:

* empty query
* quoted query
* punctuation
* repeated whitespace
* explicit fic override
* invalid fic override
* very long query
* Unicode text
* command aliases

---

## 82. Fic Resolution Tests

Test:

* explicit fic
* channel default
* guild default
* no default
* invalid default
* fic without active version
* archived version not selected

---

## 83. Exact Command Tests

Test:

* one result
* many results
* more than 100 results
* no results
* story-order pagination
* matched line and next line
* session expiry
* user ownership

---

## 84. Fuzzy Command Tests

Test:

* ranked results
* threshold exclusion
* more than 100 candidates
* no passing results
* tied scores
* paginator order
* score hidden by default

---

## 85. Semantic Command Tests

Test:

* one strong result
* several overlapping results
* no result
* provider timeout
* Qdrant failure
* long passage truncation
* pagination
* version change during session

---

## 86. Permission Tests

Test:

* normal user exact search
* normal user fic add denied
* Manage Server accepted
* configured admin role accepted
* bot owner accepted
* destructive confirmation required

---

## 87. Mention Safety Tests

Test story text containing:

```text
@everyone
@here
<@123456789>
<@&123456789>
```

No mention should fire.

---

# Configuration

## 88. Suggested Discord Configuration

```text
DISCORD_PREFIX=!

DISCORD_SEARCH_SESSION_TTL_SECONDS=1200
DISCORD_SEARCH_RESULTS_PER_PAGE=1

DISCORD_EXACT_COOLDOWN_COUNT=10
DISCORD_EXACT_COOLDOWN_SECONDS=60

DISCORD_FUZZY_COOLDOWN_COUNT=10
DISCORD_FUZZY_COOLDOWN_SECONDS=60

DISCORD_SEMANTIC_COOLDOWN_COUNT=5
DISCORD_SEMANTIC_COOLDOWN_SECONDS=60

DISCORD_ADMIN_ROLE_IDS
DISCORD_ADMIN_CHANNEL_ID
DISCORD_REFRESH_NOTIFICATION_CHANNEL_ID

DISCORD_ENABLE_SOURCE_LINKS=true
DISCORD_ENABLE_SEMANTIC_SCORE=false
```

---

## 89. Initial Implementation Order

Recommended order:

1. preserve `!qe`
2. preserve `!qf`
3. adapt existing paginator to shared result model
4. add fic resolution
5. add `!fic list`
6. add `!fic info`
7. add guild default
8. add channel default
9. add `!qs`
10. add refresh-status commands
11. add admin refresh command
12. add fic add/remove commands
13. add notifications
14. add slash-command equivalents later

---

# Acceptance Criteria

## 90. Search Command Acceptance Criteria

The Discord search interface is complete when:

1. `!qe` runs exact search only.
2. `!qf` runs fuzzy search only.
3. `!qs` runs semantic search only.
4. Every search resolves one fic.
5. Channel default overrides guild default.
6. Exact search returns up to 100 results.
7. Fuzzy search returns up to 100 results.
8. Semantic search returns a bounded candidate set.
9. One result is shown per page.
10. Existing pagination behaviour is preserved.
11. Exact and fuzzy results show matched line plus next line.
12. Semantic results show passage context.
13. Search results contain chapter metadata.
14. Story text cannot trigger Discord mentions.
15. Expired sessions stop accepting controls.
16. Search errors do not expose stack traces.
17. The bot never generates story text.

---

## 91. Fic Management Acceptance Criteria

Fic management is complete when:

1. admins can list configured fics
2. users can inspect fic metadata
3. admins can set guild default fic
4. admins can set channel default fic
5. explicit fic override works
6. admins can add a valid FanFiction.net story
7. duplicate fic creation is prevented
8. destructive removal requires confirmation
9. permissions are enforced
10. fic settings persist in Neon

---

## 92. Refresh Command Acceptance Criteria

Refresh command support is complete when:

1. admins can queue a refresh
2. duplicate active refreshes are rejected
3. refresh status can be displayed
4. auto-refresh can be enabled
5. auto-refresh can be disabled
6. force refresh is restricted
7. failures report that the active version remains available
8. update notifications do not spam unchanged checks

---

## 93. Final Discord Rules

```text
!qe
→ exact quote search
→ up to 100 results
→ story order
→ matched line plus next line

!qf
→ fuzzy quote search
→ up to 100 results
→ similarity order
→ matched line plus next line

!qs
→ semantic scene search
→ top candidate scenes
→ semantic order
→ passage plus surrounding context
```

The Discord layer resolves fic selection, formats results, and manages pagination.

It does not implement ingestion or retrieval algorithms.

The bot must preserve the old quote-finder experience while adding multi-fic support, automated refresh controls, and vague scene retrieval.
