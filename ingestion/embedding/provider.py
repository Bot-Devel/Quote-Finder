from typing import Protocol

class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def model_revision(self) -> str | None:
        ...

    @property
    def dimensions(self) -> int:
        ...

    async def embed_documents(self, texts: list[str], progress_callback=None) -> list[list[float]]:
        ...

    async def embed_query(self, text: str) -> list[float]:
        ...

    async def health_check(self) -> bool:
        ...
