import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastembed import TextEmbedding
from typing import Iterable

from .provider import EmbeddingProvider
import config


class LocalFastEmbedProvider:
    """
    Synchronous implementation of the FastEmbed provider.
    Runs locally using ONNX.
    """

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: str = config.EMBEDDING_CACHE_DIR,
        threads: int = 1,
        batch_size: int = config.EMBEDDING_BATCH_SIZE,
    ) -> None:
        self._provider_name = "local_fastembed"
        self._model_name = model_name
        self._model_revision = None
        self._dimensions = 384
        self._batch_size = batch_size

        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir,
            threads=threads,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_revision(self) -> str | None:
        return self._model_revision

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
        vectors: Iterable = self._model.embed(texts, batch_size=self._batch_size)
        return [vector.tolist() for vector in vectors]

    def embed_query_sync(self, text: str) -> list[float]:
        vector = next(self._model.query_embed(text))
        return vector.tolist()


class AsyncEmbeddingProvider(EmbeddingProvider):
    """
    Asynchronous wrapper around LocalFastEmbedProvider that safely
    executes the CPU-bound embedding tasks in a thread pool.
    """

    def __init__(
        self,
        sync_provider: LocalFastEmbedProvider,
        executor: ThreadPoolExecutor,
    ) -> None:
        self._provider = sync_provider
        self._executor = executor

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    @property
    def model_revision(self) -> str | None:
        return self._provider.model_revision

    @property
    def dimensions(self) -> int:
        return self._provider.dimensions

    async def embed_documents(
        self, texts: list[str], progress_callback=None
    ) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        macro_batch_size = 250
        all_vectors = []
        total = len(texts)

        for i in range(0, total, macro_batch_size):
            batch_texts = texts[i : i + macro_batch_size]
            batch_vectors = await loop.run_in_executor(
                self._executor,
                self._provider.embed_documents_sync,
                batch_texts,
            )
            all_vectors.extend(batch_vectors)

            if progress_callback:
                # Fire and forget progress to avoid blocking
                current = min(i + macro_batch_size, total)
                asyncio.create_task(progress_callback(current, total))

        return all_vectors

    async def embed_query(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._provider.embed_query_sync,
            text,
        )

    async def health_check(self) -> bool:
        try:
            # A simple query embed as a health check
            await self.embed_query("health check")
            return True
        except Exception:
            return False
