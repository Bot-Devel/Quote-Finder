import asyncio
from datetime import datetime, timezone
from typing import Optional
from ui.models import SearchSession


class SearchSessionStore:
    def __init__(self):
        self._sessions: dict[str, SearchSession] = {}
        self._lock = asyncio.Lock()

    async def add(self, session: SearchSession):
        async with self._lock:
            self._sessions[session.session_id] = session

    async def get(self, session_id: str) -> Optional[SearchSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove(self, session_id: str):
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def cleanup(self):
        now = datetime.now(timezone.utc)
        async with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.expires_at < now]
            for sid in expired:
                del self._sessions[sid]
