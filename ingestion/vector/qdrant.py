from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from .store import VectorStore
from ..models import ParsedChunk

import config

class QdrantStore(VectorStore):
    def __init__(self, url: str, api_key: str | None = None, collection_name: str = "quote_finder"):
        self.client = AsyncQdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.batch_size = config.QDRANT_BATCH_SIZE

    async def create_collection_if_not_exists(self, dimensions: int) -> None:
        exists = await self.client.collection_exists(self.collection_name)
        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )

    async def upsert_chunks(self, fic_id: str, version_id: str, chunks: list[ParsedChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        points = []
        import uuid
        for chunk, embedding in zip(chunks, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{version_id}_{chunk.number}"))

            payload = {
                "fic_id": fic_id,
                "version_id": version_id,
                "chapter_number": chunk.chapter_number,
                "chunk_number": chunk.number,
                "start_paragraph": chunk.start_paragraph,
                "end_paragraph": chunk.end_paragraph,
            }

            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        if points:
            for i in range(0, len(points), self.batch_size):
                batch = points[i:i + self.batch_size]
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

    async def delete_version(self, version_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="version_id",
                        match=MatchValue(value=version_id)
                    )
                ]
            )
        )

    async def delete_fic(self, fic_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="fic_id",
                        match=models.MatchValue(value=fic_id)
                    )
                ]
            )
        )

    async def search(self, vector: list[float], fic_id: str, version_id: str, limit: int) -> list[dict]:
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="fic_id",
                        match=models.MatchValue(value=fic_id)
                    ),
                    models.FieldCondition(
                        key="version_id",
                        match=models.MatchValue(value=version_id)
                    )
                ]
            ),
            limit=limit,
            with_payload=True
        )
        return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in results]
