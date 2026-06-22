# Quote Finder Discord UI Specification

## 1. Purpose

This document defines the Discord user interface for the Quote Finder bot using Discord Components V2 and modern `discord.py`.

The bot exposes three public search commands:

```text
!qff <query>  fuzzy quote search
!qfe <query>  exact quote search
!qfs <query>  semantic scene search
```

Each Discord server is connected to exactly one fic.

Normal users do not select or change fics.

The UI must provide:

* exact quote search
* fuzzy quote search
* semantic scene search
* modal-based query entry
* rich native Discord layouts
* lazy result pagination
* chapter links
* loading, empty, error, and expired states
* a separate root-only administration panel
* ingestion and refresh controls
* guild-to-fic connection management

The interface must preserve the existing Quote Finder identity while replacing the old embed-based UI with a cleaner Components V2 experience.

---

# 2. Technology

The new implementation should use:

```text
discord.py 2.7.x
discord.ui.LayoutView
discord.ui.Container
discord.ui.Section
discord.ui.TextDisplay
discord.ui.Separator
discord.ui.ActionRow
discord.ui.Button
discord.ui.Select
discord.ui.Modal
discord.ui.TextInput
```

Search result messages should use Components V2.

Traditional embeds may still be used for simple logging or notifications where an interactive layout is unnecessary.

Search interfaces must not combine Components V2 layouts with legacy embeds in the same message.

---

# 3. Public Command Contract

The public search commands are:

```text
!qff
!qfe
!qfs
```

Their meanings are fixed.

```text
!qff → fuzzy quote search
!qfe → exact quote search
!qfs → semantic scene search
```

These names must not be repurposed.

---

## 3.1 Fuzzy Search

```text
!qff <query>
```

Example:

```text
!qff there arent any innocent men
```

Behaviour:

* resolve the fic connected to the current guild
* run fuzzy lexical quote search
* rank results by similarity
* retain up to 100 results
* show one result at a time
* show matched line plus following line
* use lazy pagination

When no query is supplied:

```text
!qff
```

open the Fuzzy Search modal.

---

## 3.2 Exact Search

```text
!qfe <query>
```

Example:

```text
!qfe there are no innocent men
```

Behaviour:

* resolve the fic connected to the current guild
* run normalized literal quote search
* preserve story order
* retain up to 100 results
* show one result at a time
* show matched line plus following line
* use lazy pagination

When no query is supplied:

```text
!qfe
```

open the Exact Search modal.

---

## 3.3 Semantic Scene Search

```text
!qfs <query>
```

Example:

```text
!qfs Harry acts calm until everyone leaves and then collapses
```

Behaviour:

* resolve the fic connected to the current guild
* create a local query embedding
* query Qdrant
* retrieve canonical passage text from Neon
* retain the strongest scene candidates
* show one result at a time
* include surrounding paragraph context
* use lazy pagination

When no query is supplied:

```text
!qfs
```

open the Scene Search modal.

---

# 4. Guild-Scoped Fic Model

Each Discord guild is connected to exactly one fic.

```text
guild_id
→ fic_id
→ active_version_id
```

Suggested table:

```text
guild_fic_connections
```

Suggested fields:

```text
guild_id
fic_id
connected_by_user_id
connected_at
updated_at
is_enabled
```

Required constraint:

```sql
UNIQUE (guild_id)
```

A fic may be connected to multiple guilds.

Normal users must never be shown a fic selector.

---

# 5. Guild Resolution

Every public search follows:

```text
receive command
→ require guild context
→ resolve guild_id
→ load guild-to-fic connection
→ load fic
→ load active version
→ execute search
```

Search must fail safely when:

* command is used in DMs
* guild has no connected fic
* guild connection is disabled
* connected fic has no active version
* active version is unavailable

---

## 5.1 DM Behaviour

Public search commands used in DMs should return:

```text
Quote Finder searches are only available inside a connected Discord server.
```

No personal fic-selection flow is required.

---

## 5.2 Unconnected Guild

If the guild is not connected:

```text
Quote Finder is not configured for this server.

The bot owner must connect this server to a fic before search can be used.
```

Do not show users a fic selector.

---

## 5.3 Fic Still Indexing

If a fic exists but has no active version:

```text
The fic connected to this server is still being indexed.

Search will become available when ingestion completes.
```

If an older active version exists during refresh, continue using it.

---

# 6. UI Principles

The UI must:

1. Clearly identify the search mode.
2. Clearly show fic and chapter information.
3. Make the source passage the visual focus.
4. Preserve original story wording.
5. Return the first result quickly.
6. Load later pages lazily.
7. Keep navigation controls stable.
8. Work well on desktop and mobile.
9. Prevent users from controlling another user’s session.
10. Prevent story text from triggering Discord mentions.
11. Avoid unnecessary buttons.
12. Separate public search from root administration.
13. Avoid displaying implementation details to normal users.
14. Remain readable in light and dark themes.
15. Keep business logic outside component callbacks.

---

# 7. Search Modal Flow

When a command is used without a query, open a modal.

Examples:

```text
!qff
→ Fuzzy Quote Search modal

!qfe
→ Exact Quote Search modal

!qfs
→ Scene Search modal
```

Each modal contains one text input.

---

## 7.1 Fuzzy Search Modal

Title:

```text
Fuzzy Quote Search
```

Label:

```text
Approximate quote
```

Placeholder:

```text
Enter the wording you roughly remember
```

Maximum length:

```text
500 characters
```

---

## 7.2 Exact Search Modal

Title:

```text
Exact Quote Search
```

Label:

```text
Exact wording
```

Placeholder:

```text
Enter the exact wording you remember
```

Maximum length:

```text
500 characters
```

---

## 7.3 Scene Search Modal

Title:

```text
Scene Search
```

Label:

```text
Scene description
```

Placeholder:

```text
Describe what happens in the scene
```

Maximum length:

```text
1000 characters
```

---

# 8. Direct Query Flow

When the command includes a query:

```text
!qfe exact quote here
```

the bot should skip the modal and begin searching immediately.

Flow:

```text
parse query
→ validate query
→ resolve guild fic
→ send loading state
→ execute search
→ create search session
→ fetch first result
→ edit loading message into result view
```

---

# 9. Loading States

The bot should send one temporary loading message.

Suggested text:

```text
Fuzzy:
Searching for approximate quote matches…

Exact:
Searching for exact quote matches…

Semantic:
Searching for relevant scenes…
```

The loading message should be edited into:

* first result
* empty result state
* error state

Do not send several separate progress messages.

---

## 9.1 Slow Search Update

For searches taking longer than approximately three seconds, the bot may update the loading message once.

Examples:

```text
Ranking fuzzy candidates…
```

```text
Searching indexed scenes…
```

Avoid frequent edits.

This is progress reporting, not streaming.

---

# 10. Search Result Layout

All search result messages should use:

```text
LayoutView
└── Container
    ├── Search heading
    ├── Fic and chapter metadata
    ├── Separator
    ├── Passage
    ├── Separator
    ├── Result metadata
    ├── Primary navigation row
    └── Secondary action row
```

One result should be shown per message.

The same Discord message should be edited during pagination.

---

# 11. Search Mode Identity

Suggested labels:

```text
Fuzzy Quote Search
Exact Quote Search
Scene Search
```

Suggested accent colours:

```text
Fuzzy:
orange or gold

Exact:
blue

Scene:
purple
```

Colours must be defined centrally.

Example:

```python
SEARCH_ACCENTS = {
    "fuzzy": 0xF0B232,
    "exact": 0x5865F2,
    "semantic": 0x9B59B6,
}
```

The search type must also be shown as text.

Colour alone must not communicate meaning.

---

# 12. Exact Search Result Layout

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Exact Quote Search                           │
│                                              │
│ Story Title                                  │
│ Chapter 116                                  │
│ HP&DEM 32: The Blackest Day Finale           │
│ ──────────────────────────────────────────── │
│                                              │
│ “The matched line appears here.”             │
│                                              │
│ The following line appears here.             │
│                                              │
│ ──────────────────────────────────────────── │
│ Result 2 of 37                               │
│                                              │
│ [First] [Previous] [2 / 37] [Next] [Last]   │
│ [Jump] [Open Chapter] [New Search] [Close]   │
└──────────────────────────────────────────────┘
```

Required data:

* search type
* fic title
* chapter number
* chapter title
* matched line
* next line
* current result number
* returned result count
* total match count when greater than the result cap

---

# 13. Fuzzy Search Result Layout

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Fuzzy Quote Search                           │
│ Approximate quote match                      │
│                                              │
│ Story Title                                  │
│ Chapter 116                                  │
│ HP&DEM 32: The Blackest Day Finale           │
│ ──────────────────────────────────────────── │
│                                              │
│ “The closest matching line appears here.”    │
│                                              │
│ The following line appears here.             │
│                                              │
│ ──────────────────────────────────────────── │
│ Result 2 of 100                              │
│                                              │
│ [First] [Previous] [2 / 100] [Next] [Last]  │
│ [Jump] [Open Chapter] [New Search] [Close]   │
└──────────────────────────────────────────────┘
```

Fuzzy score should remain hidden by default.

Optional root/debug display:

```text
Lexical similarity score: 87
```

Do not display:

```text
87% accurate
```

---

# 14. Scene Search Result Layout

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Scene Search                                 │
│                                              │
│ Story Title                                  │
│ Chapter 42: Courage                          │
│ ──────────────────────────────────────────── │
│                                              │
│ Context before the relevant passage...       │
│                                              │
│ The relevant source passage appears here...  │
│                                              │
│ Context following the passage...             │
│                                              │
│ ──────────────────────────────────────────── │
│ Candidate 3 of 10                            │
│                                              │
│ [First] [Previous] [3 / 10] [Next] [Last]   │
│ [Jump] [Open Chapter] [New Search] [Close]   │
└──────────────────────────────────────────────┘
```

Required data:

* fic title
* chapter metadata
* canonical source passage
* surrounding paragraph context
* candidate number
* total candidates

Semantic score should not be shown by default.

---

# 15. Text Hierarchy

Suggested heading:

```markdown
## Exact Quote Search
```

Suggested metadata:

```markdown
**Story Title**

**Chapter 116**
HP&DEM 32: The Blackest Day Finale
```

Suggested exact or fuzzy passage:

```markdown
> **Matched source line**
>
> Following source line
```

Suggested scene passage:

```markdown
Context before...

> **Relevant passage**

Context after...
```

The renderer must control all Markdown formatting.

---

# 16. Story Text Safety

Search result messages must suppress mentions.

Use:

```python
discord.AllowedMentions.none()
```

Story text must not trigger:

```text
@everyone
@here
user mentions
role mentions
channel mentions
```

This applies to:

* exact matches
* fuzzy matches
* semantic passages
* chapter titles
* fic titles

---

# 17. Markdown Escaping

Story content may contain Discord Markdown characters.

The renderer should:

* escape accidental Markdown
* neutralize triple backticks
* preserve readable paragraph breaks
* avoid code blocks for ordinary story text
* preserve dialogue punctuation
* add only bot-controlled emphasis

Suggested helper:

```python
def escape_story_text(text: str) -> str:
    ...
```

Tests must cover:

```text
*
_
~
`
>
||
```

---

# 18. Text Limits

Application-level limits should keep layouts safe.

Suggested limits:

```text
Exact matched line and context:
2500 characters

Fuzzy matched line and context:
2500 characters

Semantic passage and context:
3500 characters

Metadata:
500 characters
```

When truncating:

1. preserve the matched passage
2. remove distant context first
3. retain chapter link
4. avoid splitting Unicode incorrectly
5. append:

```text
[…]
```

---

# 19. Result Caps

Search limits:

```text
Exact:
100 results

Fuzzy:
100 results

Semantic:
10 results initially
```

If exact search finds 237 matches:

```text
Result 2 of 100
Showing the first 100 of 237 matches
```

The UI must distinguish:

* total matches
* retained results
* current result index

---

# 20. Lazy Pagination

The paginator must not eagerly build every page.

Initial search:

```text
run search
→ retain ordered result references
→ create search session
→ fetch result 1 content
→ render result 1
→ send response
```

Page change:

```text
user presses Next
→ resolve target result reference
→ fetch source content and context
→ render target result
→ edit original message
```

A result reference should contain identifiers, not complete rendered content.

---

# 21. Search Result References

Suggested model:

```python
from dataclasses import dataclass


@dataclass
class SearchResultRef:
    result_id: str
    chapter_id: str

    line_id: str | None = None
    chunk_id: str | None = None

    fuzzy_score: float | None = None
    semantic_score: float | None = None
```

---

# 22. Search Session Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


SearchType = Literal[
    "fuzzy",
    "exact",
    "semantic",
]


@dataclass
class SearchSession:
    session_id: str

    owner_user_id: int
    guild_id: int
    channel_id: int
    message_id: int | None

    fic_id: str
    version_id: str
    search_type: SearchType

    result_refs: list[SearchResultRef]
    current_index: int

    total_matches: int
    returned_results: int
    results_truncated: bool

    created_at: datetime
    expires_at: datetime

    page_cache: dict[int, "RenderedSearchPage"] = field(
        default_factory=dict,
    )
```

---

# 23. Session Storage

Initial session storage:

```text
in memory
```

Requirements:

* keyed by session ID
* bounded number of sessions
* periodic cleanup
* sessions expire automatically
* losing sessions after bot restart is acceptable
* expired controls fail safely

Future storage may use:

```text
Redis
Postgres
```

Persistent sessions are not required initially.

---

# 24. Page Cache

The paginator may cache a small number of rendered pages.

Recommended limit:

```text
5 pages per session
```

Useful pages:

* current
* previous
* next
* recently visited

Do not cache all 100 rendered pages by default.

---

# 25. Exact Search Pagination Data

Initial exact search should return:

```text
ordered matching line IDs
total match count
```

The first result fetch loads:

```text
matched line
next line
chapter metadata
fic metadata
```

Later pages should use stored line IDs.

The exact query should not rerun for every button click.

---

# 26. Fuzzy Search Pagination Data

Initial fuzzy search performs:

```text
candidate retrieval
→ fuzzy scoring
→ threshold filtering
→ ranking
→ retain up to 100 line references
```

Each retained reference includes:

```text
line ID
score
rank
```

Later pages fetch source content using the stored line ID.

Fuzzy scoring must not rerun during pagination.

---

# 27. Semantic Search Pagination Data

Initial semantic search performs:

```text
query embedding
→ Qdrant search
→ overlap deduplication
→ retain ordered chunk references
```

Each result reference includes:

```text
chunk ID
semantic score
rank
```

Later pages retrieve canonical text and context from Neon.

---

# 28. Optional Prefetch

After displaying page N, the bot may prefetch page N+1.

Rules:

* do not delay current page rendering
* do not fail the user request if prefetch fails
* only prefetch one page ahead
* respect session cache limits
* skip if system load is high

This is optional.

---

# 29. Primary Navigation Row

Recommended buttons:

```text
First
Previous
Page Indicator
Next
Last
```

Example:

```text
[⏮] [◀] [2 / 37] [▶] [⏭]
```

The page indicator is a disabled button.

---

# 30. Navigation Button States

First page:

```text
First: disabled
Previous: disabled
Next: enabled if more results exist
Last: enabled if more results exist
```

Middle page:

```text
First: enabled
Previous: enabled
Next: enabled
Last: enabled
```

Final page:

```text
First: enabled
Previous: enabled
Next: disabled
Last: disabled
```

Single result:

```text
all navigation buttons disabled
```

---

# 31. Secondary Action Row

Recommended actions:

```text
Jump
Open Chapter
New Search
Close
```

Do not include:

```text
Change Fic
```

Normal users cannot change the guild’s fic.

---

# 32. Jump Modal

Pressing Jump opens a modal.

Field:

```text
Result number
```

Validation:

* required
* integer
* minimum 1
* maximum retained result count

After submission:

1. validate session ownership
2. validate session expiry
3. convert to zero-based index
4. lazily fetch result
5. edit original message

Invalid input should receive an ephemeral error.

---

# 33. Open Chapter

Use a URL button when a reliable chapter URL exists.

Pattern:

```text
https://www.fanfiction.net/s/<story-id>/<chapter-number>/
```

If a reliable link cannot be produced, omit the button.

Do not show a disabled or broken chapter link.

---

# 34. New Search

Pressing New Search should open a modal for the same search mode.

Examples:

```text
Fuzzy result
→ New Search
→ Fuzzy Search modal

Exact result
→ New Search
→ Exact Search modal

Scene result
→ New Search
→ Scene Search modal
```

The same result message may be reused and replaced after the new query completes.

Optional additional buttons:

```text
Try Exact
Try Fuzzy
Try Scene
```

These are especially useful in empty-result states.

---

# 35. Close

Pressing Close:

1. validates session ownership
2. ends the session
3. disables or removes controls
4. preserves the visible result
5. marks the UI closed
6. removes session state

Suggested final note:

```text
Search closed.
```

Deleting the message is not required.

---

# 36. Session Ownership

Only the user who initiated the search may control it.

Required check:

```python
interaction.user.id == session.owner_user_id
```

Other users receive an ephemeral response:

```text
This search belongs to another user.

Run the command yourself to start a new search.
```

---

# 37. Interaction Handling

Interactions must be acknowledged promptly.

For page loads:

```text
defer interaction
→ fetch target result
→ rebuild layout
→ edit original message
```

The user must not see Discord’s failed-interaction warning because the bot was still waiting for Postgres to contemplate existence.

---

# 38. Page Load Lock

Each session must allow only one page transition at a time.

Suggested lock:

```python
asyncio.Lock
```

Flow:

```text
acquire lock
→ determine target index
→ fetch page
→ update session
→ edit message
→ release lock
```

Rapid button clicks must not corrupt the current index.

---

# 39. Session Expiry

Recommended session lifetime:

```text
20 minutes
```

After expiry:

* disable controls if possible
* retain visible result
* remove session from memory
* reject later interactions
* show ephemeral expiry message

Suggested visible note:

```text
Search session expired.
```

---

# 40. Version Pinning

Each session must remain pinned to:

```text
fic_id
version_id
ordered result references
```

If the fic refreshes during pagination:

* current session continues using the old version
* new searches use the new active version
* result order remains stable

Old versions should be retained longer than the search session TTL.

Recommended:

```text
session TTL:
20 minutes

old version retention:
at least 24 hours
```

---

# 41. Empty States

## 41.1 Exact Empty State

```text
No exact quote matches were found.
```

Buttons:

```text
Try Fuzzy
Try Scene
Close
```

---

## 41.2 Fuzzy Empty State

```text
No fuzzy quote matches passed the similarity threshold.
```

Buttons:

```text
Try Exact
Try Scene
Close
```

---

## 41.3 Scene Empty State

```text
No strong scene matches were found.

Try including characters, location, emotion, or what happened nearby.
```

Buttons:

```text
Try Exact
Try Fuzzy
Close
```

---

# 42. Error States

Error layouts should contain:

* short title
* user-readable explanation
* error ID
* optional retry
* close action

Example:

```text
Scene search is temporarily unavailable.

Exact and fuzzy search are still available.

Error ID: QF-7A2C91
```

Buttons:

```text
Retry
Close
```

---

# 43. Timeout State

```text
The search took too long to complete.

Try again in a moment.
```

Exact, fuzzy, and semantic timeouts should be handled independently.

---

# 44. Public UI Help

A help command may exist:

```text
!qfhelp
```

Suggested output:

```text
Quote Finder

!qff <query>
Search approximately remembered wording

!qfe <query>
Search exact wording

!qfs <query>
Search using a scene description

Run a command without a query to open a search form.
```

---

# 45. Root Administration Interface

The bot has a separate root-only administration panel.

The root user is configured by Discord user ID.

```env
QUOTE_FINDER_ROOT_USER_ID=123456789012345678
```

The admin UI manages:

* fic ingestion
* fic refresh
* forced rebuilds
* version inspection
* rollback
* guild connections
* ingestion jobs
* failed jobs
* embedding health
* Neon health
* Qdrant health
* bot status

---

# 46. Admin Visibility

The admin panel should be available through an ephemeral slash command.

Recommended:

```text
/qfadmin
```

This allows only the root user to see the panel.

Prefix-command messages are not truly private, so the root interface should not rely on them for secrecy.

---

# 47. Root Authorization

Every admin command and component callback must verify:

```python
interaction.user.id == settings.root_user_id
```

Visibility is not authorization.

The backend must enforce root access for:

* buttons
* selects
* modals
* slash commands
* direct service calls triggered by Discord

Unauthorized users receive:

```text
You are not authorized to use Quote Finder administration.
```

---

# 48. Admin Dashboard Layout

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Quote Finder Administration                  │
│                                              │
│ Fics: 8                                      │
│ Connected guilds: 12                         │
│ Active jobs: 1                               │
│ Failed jobs: 0                               │
│                                              │
│ [Fics] [Guilds] [Jobs] [System]              │
│ [Refresh Dashboard] [Close]                  │
└──────────────────────────────────────────────┘
```

---

# 49. Fics Panel

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Fics                                         │
│                                              │
│ [Select Fic ▼]                               │
│                                              │
│ [Ingest New Fic]                             │
│ [View Fic]                                   │
│ [Refresh]                                    │
│ [Force Rebuild]                              │
│ [Versions]                                   │
│ [Guild Connections]                          │
└──────────────────────────────────────────────┘
```

---

# 50. Ingest New Fic

Pressing Ingest New Fic opens a modal.

Fields:

```text
FanFiction.net story ID or URL
Optional display name
Optional alias
Auto refresh enabled
Refresh interval
```

Only the story ID or URL is required.

On submit:

```text
validate source
→ create or locate fic
→ create ingestion job
→ return job status view
```

The component callback must not perform full ingestion synchronously.

---

# 51. Fic Detail View

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Story Title                                  │
│                                              │
│ FFN ID: 1234567                              │
│ Active version: v12                          │
│ Chapters: 180                                │
│ Words: 1,502,000                             │
│ Last checked: 3 hours ago                    │
│ Last refreshed: 12 days ago                  │
│ Auto refresh: Enabled                        │
│ Refresh interval: 24 hours                   │
│                                              │
│ [Refresh] [Force Rebuild]                    │
│ [Versions] [Guilds]                          │
│ [Disable Refresh] [Back]                     │
└──────────────────────────────────────────────┘
```

---

# 52. Refresh Action

Pressing Refresh:

```text
validate root
→ verify no active refresh exists
→ create refresh job
→ show queued/running status
```

Response:

```text
Refresh queued.
```

If already running:

```text
A refresh is already running for this fic.
```

---

# 53. Force Rebuild

Force rebuild must require confirmation.

Warning:

```text
This will rebuild the fic even if the EPUB has not changed.

The active version will remain available until the replacement is validated.
```

Buttons:

```text
Confirm Rebuild
Cancel
```

---

# 54. Versions Panel

The versions panel should list:

```text
version ID
status
created time
activated time
chapter count
word count
embedding model
EPUB hash prefix
```

Actions:

```text
Inspect
Rollback
Delete Archived Version
Back
```

Only archived versions may be manually deleted.

The active version must never expose a delete action.

---

# 55. Rollback

Rollback requires confirmation.

Flow:

```text
select archived version
→ validate Neon data
→ validate Qdrant vectors
→ show comparison
→ confirm
→ atomically reactivate
```

Warning must show:

```text
Current version
Rollback target
Chapter count difference
Word count difference
```

---

# 56. Guild Management Panel

Conceptual layout:

```text
┌──────────────────────────────────────────────┐
│ Guild Connections                            │
│                                              │
│ [Select Guild ▼]                             │
│                                              │
│ Current fic: Story Title                     │
│                                              │
│ [Connect to Fic]                             │
│ [Change Connection]                          │
│ [Disconnect]                                 │
│ [Back]                                       │
└──────────────────────────────────────────────┘
```

The select menu should list guilds the bot currently belongs to.

---

# 57. Connect Guild

Flow:

```text
select guild
→ select fic
→ confirm
→ create guild_fic_connection
```

Confirmation:

```text
Connect Guild Name to Story Title?
```

Buttons:

```text
Confirm
Cancel
```

---

# 58. Change Guild Connection

When a guild already has a fic:

```text
This guild is currently connected to:
Old Story

Reconnect it to:
New Story?
```

Require confirmation.

After success:

```text
Guild Name is now connected to New Story.
```

New searches use the newly connected fic immediately.

Existing search sessions remain pinned to their original version.

---

# 59. Disconnect Guild

Disconnecting disables public search in that guild.

Warning:

```text
Disconnecting this guild will make Quote Finder search unavailable there.
```

Buttons:

```text
Disconnect
Cancel
```

---

# 60. Jobs Panel

The jobs panel should display:

```text
active ingestion jobs
active refresh jobs
failed jobs
stale jobs
recent completed jobs
```

Job detail:

```text
job ID
fic
trigger
current stage
progress
started time
last heartbeat
failure stage
failure message
```

Actions:

```text
Refresh Status
Retry
Cancel
Mark Stale
Back
```

Only valid actions should be shown for each job state.

---

# 61. Job Progress UI

Example:

```text
Ingesting Story Title

Stage:
Generating embeddings

Progress:
3,800 / 5,200 chunks

Status:
Running
```

The panel may provide:

```text
Refresh
Cancel
Back
```

The UI should poll only when the root presses Refresh or through a modest background update interval.

Do not update every second.

---

# 62. System Panel

The system panel should display:

```text
Discord gateway status
Neon connectivity
Qdrant connectivity
embedding model status
embedding model name
embedding dimensions
model cache status
last successful refresh
last failed refresh
active worker state
```

Example:

```text
Discord: Healthy
Neon: Healthy
Qdrant: Healthy
Embeddings: Ready
Model: BAAI/bge-small-en-v1.5
Dimensions: 384
```

Actions:

```text
Run Health Check
Reload
Close
```

---

# 63. Admin Callback Boundaries

Admin component callbacks must only:

* validate root
* validate input
* invoke service methods
* create jobs
* retrieve status
* render UI

They must not:

* parse EPUB files directly
* generate thousands of embeddings directly
* hold long database transactions
* wait through full ingestion
* perform destructive operations without confirmation

---

# 64. Custom IDs

Suggested public component IDs:

```text
qf:<session-id>:first
qf:<session-id>:previous
qf:<session-id>:next
qf:<session-id>:last
qf:<session-id>:jump
qf:<session-id>:chapter
qf:<session-id>:new
qf:<session-id>:close
```

Suggested admin IDs:

```text
qfa:<admin-session-id>:fics
qfa:<admin-session-id>:guilds
qfa:<admin-session-id>:jobs
qfa:<admin-session-id>:system
```

Do not encode:

* full query
* API keys
* database IDs unnecessarily
* story text

---

# 65. Layout Builder Architecture

Suggested UI classes:

```text
FuzzySearchResultView
ExactSearchResultView
SceneSearchResultView

SearchLoadingView
SearchEmptyView
SearchErrorView
SearchExpiredView

AdminDashboardView
AdminFicsView
AdminFicDetailView
AdminGuildsView
AdminJobsView
AdminSystemView
```

Suggested renderer classes:

```text
SearchResultRenderer
SearchMetadataRenderer
StoryTextRenderer
PaginationControlBuilder
AdminPanelRenderer
```

Command handlers should not construct layouts manually.

---

# 66. Public Search View Skeleton

```python
class SearchResultView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        session: SearchSession,
        session_store: SearchSessionStore,
        page_loader: SearchPageLoader,
        renderer: SearchResultRenderer,
        timeout: float = 1200,
    ) -> None:
        super().__init__(timeout=timeout)

        self.session = session
        self.session_store = session_store
        self.page_loader = page_loader
        self.renderer = renderer

        self.message: discord.Message | None = None
        self.page_lock = asyncio.Lock()

        self.rebuild()
```

---

# 67. Error IDs

Unexpected errors should generate short IDs.

Example:

```text
QF-7A2C91
```

User-facing message:

```text
Search failed.

Error ID: QF-7A2C91
```

The same ID must appear in logs.

---

# 68. Logging

Public UI logs should include:

```text
command
search type
guild ID
user ID
fic ID
version ID
result count
initial response time
page fetch duration
session ID
error ID
```

Admin UI logs should include:

```text
root user ID
action
fic ID
guild ID
job ID
result
error ID
```

Full query text should not be logged by default.

---

# 69. Performance Targets

Suggested targets:

```text
Exact first result:
under 1 second normally

Fuzzy first result:
under 2 seconds normally

Scene first result:
under 3 seconds normally

Cached page navigation:
under 300 ms

Uncached page navigation:
under 1 second
```

The first result must not wait for every page to be fully rendered.

---

# 70. Accessibility

Buttons should use clear labels or universally understood symbols.

Avoid relying only on:

```text
colour
emoji
position
```

Search headings must contain text.

Disabled page indicator should show:

```text
2 / 37
```

rather than an unexplained icon.

---

# 71. Mobile Layout

The UI must remain usable on narrow Discord clients.

Guidelines:

* keep button labels short
* avoid too many buttons per row
* place secondary actions on another row
* avoid excessively long metadata blocks
* keep passage formatting simple
* test modals on mobile
* do not depend on hover text

Suggested navigation row:

```text
[⏮] [◀] [2/37] [▶] [⏭]
```

Suggested action row:

```text
[Jump] [Chapter] [New Search] [Close]
```

---

# 72. Backward Compatibility

The rewrite must preserve:

```text
!qff
!qfe
```

The semantic command is:

```text
!qfs
```

Commands with query text should continue working directly.

Commands without query text open modals.

Existing users should not be forced to use buttons if they prefer typing commands.

---

# 73. Public UI Acceptance Criteria

The public UI is complete when:

1. `!qff` performs fuzzy search.
2. `!qfe` performs exact search.
3. `!qfs` performs semantic scene search.
4. Each command opens its modal when no query is supplied.
5. Each search uses the fic connected to the current guild.
6. Normal users cannot select or change the fic.
7. Exact and fuzzy searches retain up to 100 results.
8. Scene search returns a bounded candidate set.
9. The first result is rendered without building every page.
10. Later pages are loaded lazily.
11. Pagination uses one edited message.
12. Result sessions are pinned to one fic version.
13. Only the requesting user may control the session.
14. Search text cannot trigger mentions.
15. Chapter links work when available.
16. Empty states offer relevant alternative search modes.
17. Expired sessions disable interaction.
18. Search errors do not expose stack traces.
19. Original story text is never rewritten.
20. The UI works on desktop and mobile.

---

# 74. Admin UI Acceptance Criteria

The administration UI is complete when:

1. only the configured root user can open it
2. the panel is delivered ephemerally
3. the root can ingest a fic by FFN ID or URL
4. ingestion creates a durable job
5. the root can inspect fic metadata
6. the root can trigger refresh
7. the root can trigger forced rebuild
8. the root can inspect versions
9. the root can rollback to a retained version
10. the root can connect a fic to a guild
11. the root can change a guild connection
12. the root can disconnect a guild
13. the root can inspect active and failed jobs
14. the root can retry eligible failed jobs
15. the root can inspect system health
16. all admin callbacks revalidate root authorization
17. destructive actions require confirmation
18. ingestion and refresh do not execute inside Discord callbacks
19. admin actions are logged
20. no credentials are displayed

---

# 75. Final UI Rules

```text
!qff
→ fuzzy quote search

!qfe
→ exact quote search

!qfs
→ semantic scene search
```

With a query:

```text
search immediately
```

Without a query:

```text
open the matching modal
```

Public users:

```text
search only the fic connected to their guild
```

Root user:

```text
manage fics, ingestion, refreshes, versions, jobs, and guild connections
```

Search results:

```text
Components V2 layout
→ one result at a time
→ lazy pagination
→ same message edited
→ original source text
```

The public interface does not include a fic selector.

The root administration interface is separate and ephemeral.

The UI presents search state.

The service layer performs search, ingestion, refresh, and storage operations.
