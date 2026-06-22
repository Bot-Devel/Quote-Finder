from typing import Protocol
from ..models import ParsedChunk

class VectorStore(Protocol):
    async def create_collection_if_not_exists(self, dimensions: int) -> None:
        ...

    async def upsert_chunks(self, fic_id: str, version_id: str, chunks: list[ParsedChunk], embeddings: list[list[float]]) -> None:
        ...

    async def delete_version(self, version_id: str) -> None:
        ...

    async def search(self, vector: list[float], fic_id: str, version_id: str, limit: int) -> list[dict]:
        ...

    async def delete_fic(self, fic_id: str) -> None:
        ...
