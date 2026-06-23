import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
from loguru import logger
import os
import resource

from fastembed.rerank.cross_encoder import TextCrossEncoder
import config

class RerankerProvider:
    @property
    def model_name(self) -> str:
        raise NotImplementedError

    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        raise NotImplementedError

class LocalFastEmbedReranker:
    def __init__(self, model_name: str = config.SEMANTIC_RERANK_MODEL, cache_dir: str = config.EMBEDDING_CACHE_DIR, threads: int = 1):
        self._model_name = model_name
        
        mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        logger.info(f"Loading CrossEncoder '{model_name}'. Memory before: {mem_before:.2f} MB")
        
        self._model = TextCrossEncoder(
            model_name=model_name,
            cache_dir=cache_dir,
            threads=threads
        )
        
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        logger.info(f"CrossEncoder loaded. Memory after: {mem_after:.2f} MB (+{mem_after - mem_before:.2f} MB)")

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank_sync(self, query: str, documents: List[str]) -> List[float]:
        if not documents:
            return []
        
        # TextCrossEncoder outputs an iterable of numpy arrays (or float)
        # We need to list-ify it and extract the float scores
        results = list(self._model.rerank(query, documents))
        
        # The result of rerank is an Iterable of numpy arrays or floats.
        # fastembed returns values. We need to parse them.
        scores = [float(score) for score in results]
        return scores

class AsyncRerankerProvider(RerankerProvider):
    def __init__(self, sync_provider: LocalFastEmbedReranker, executor: ThreadPoolExecutor):
        self._provider = sync_provider
        self._executor = executor

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        if not documents:
            return []
            
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._provider.rerank_sync,
            query,
            documents
        )
