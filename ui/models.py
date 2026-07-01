from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import asyncio
from typing import Optional, Dict, List, Tuple
from search.models import SearchResult


@dataclass
class SearchResultRef:
    result_id: str
    line_id: Optional[str] = None
    chunk_id: Optional[str] = None
    fuzzy_score: Optional[float] = None
    semantic_score: Optional[float] = None


@dataclass
class SearchSession:
    session_id: str
    owner_user_id: int
    guild_id: int
    channel_id: int
    message_id: Optional[int]

    fic_id: str
    version_id: str
    search_type: str

    result_refs: List[SearchResultRef]
    total_results: int
    current_index: int = 0
    results_truncated: bool = False

    page_cache: Dict[int, SearchResult] = field(default_factory=dict)
    loading_windows: Dict[Tuple[int, int], asyncio.Task] = field(default_factory=dict)
    page_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=5)
    )
