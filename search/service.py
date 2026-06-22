import uuid
import re
import time
from loguru import logger
from typing import Optional

from ingestion.embedding import AsyncEmbeddingProvider
from ingestion.vector.store import VectorStore
from search.repository import QuoteSearchRepository
from search.models import SearchResults, SearchResult

class SearchService:
    def __init__(
        self,
        repository: QuoteSearchRepository,
        vector_store: VectorStore,
        embedding_provider: AsyncEmbeddingProvider
    ):
        self.repo = repository
        self.vector_store = vector_store
        self.embedding = embedding_provider

    def _normalize_query(self, query: str) -> str:
        # Same logic as parsing, lowercased
        text = query.lower()
        # simplified normalizer for quotes
        text = re.sub(r'[""‘’]', "'", text)
        text = re.sub(r'["“”]', '"', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def _fetch_context(self, chapter_id: str, start_para: int, end_para: int, prev_lines: int, next_lines: int):
        s_para = max(1, start_para - prev_lines)
        e_para = end_para + next_lines
        return await self.repo.fetch_paragraph_context(chapter_id, s_para, e_para)

    async def search_exact(self, fic_id: str, version_id: str, query: str, limit: int = 100) -> SearchResults:
        start_time = time.time()
        query_id = uuid.uuid4().hex
        normalized_query = self._normalize_query(query)
        logger.info(f"[{query_id}] Starting EXACT search | fic={fic_id} | query='{query}' (normalized='{normalized_query}')")
        
        paragraphs, total = await self.repo.search_exact(fic_id, version_id, normalized_query, limit + 1)
        db_duration = time.time() - start_time
        logger.debug(f"[{query_id}] DB exact match took {db_duration:.3f}s. Found {total} total matches.")
        
        truncated = False
        if len(paragraphs) > limit:
            truncated = True
            paragraphs = paragraphs[:limit]
            total = limit + 1 # At least
            
        # Bulk fetch context
        context_start_time = time.time()
        tuples_to_fetch = [(p.chapter_id, p.paragraph_number + 1) for p in paragraphs]
        next_paras_map = await self.repo.fetch_next_paragraphs_bulk(tuples_to_fetch)
        context_duration = time.time() - context_start_time
        logger.debug(f"[{query_id}] Bulk fetched {len(next_paras_map)} contexts in {context_duration:.3f}s.")
            
        results = []
        for p in paragraphs:
            next_p = next_paras_map.get((p.chapter_id, p.paragraph_number + 1))
            context_after = next_p.text if next_p else None
                
            res = SearchResult(
                fic_id=fic_id,
                version_id=version_id,
                chapter_id=p.chapter_id,
                chapter_number=p.chapter.chapter_number,
                chapter_title=p.chapter.chapter_title,
                start_position=p.paragraph_number,
                end_position=p.paragraph_number,
                matched_text=p.text,
                context_before=None,
                context_after=context_after,
                result_type="exact",
                source_line_id=p.id
            )
            results.append(res)
            
        total_duration = time.time() - start_time
        logger.info(f"[{query_id}] EXACT search completed in {total_duration:.3f}s | Returned {len(results)}/{total} matches.")
            
        return SearchResults(
            query_id=query_id,
            fic_id=fic_id,
            version_id=version_id,
            search_type="exact",
            total_matches=total,
            returned_results=len(results),
            results_truncated=truncated,
            results=results
        )

    async def search_fuzzy(self, fic_id: str, version_id: str, query: str, limit: int = 100, min_score: float = 75.0) -> SearchResults:
        from rapidfuzz import fuzz
        
        start_time = time.time()
        query_id = uuid.uuid4().hex
        normalized_query = self._normalize_query(query)
        logger.info(f"[{query_id}] Starting FUZZY search | fic={fic_id} | query='{query}' (normalized='{normalized_query}')")
        
        candidates = await self.repo.get_fuzzy_candidates(fic_id, version_id, normalized_query, limit=300)
        db_duration = time.time() - start_time
        logger.debug(f"[{query_id}] DB fuzzy candidates retrieval took {db_duration:.3f}s. Retrieved {len(candidates)} candidates.")
        
        fuzz_start = time.time()
        scored_candidates = []
        for c in candidates:
            score = fuzz.partial_ratio(normalized_query, c.normalized_text)
            if score >= min_score:
                scored_candidates.append((score, c))
                
        scored_candidates.sort(key=lambda x: (-x[0], x[1].chapter.chapter_number, x[1].paragraph_number))
        fuzz_duration = time.time() - fuzz_start
        logger.debug(f"[{query_id}] RapidFuzz scoring took {fuzz_duration:.3f}s. Filtered to {len(scored_candidates)} candidates.")
        
        truncated = False
        total = len(scored_candidates)
        if total > limit:
            truncated = True
            scored_candidates = scored_candidates[:limit]
            
        results = []
        for score, p in scored_candidates:
            context_paras = await self._fetch_context(p.chapter_id, p.paragraph_number, p.paragraph_number, 0, 1)
            context_after = None
            if len(context_paras) > 1:
                context_after = context_paras[1].text
                
            res = SearchResult(
                fic_id=fic_id,
                version_id=version_id,
                chapter_id=p.chapter_id,
                chapter_number=p.chapter.chapter_number,
                chapter_title=p.chapter.chapter_title,
                start_position=p.paragraph_number,
                end_position=p.paragraph_number,
                matched_text=p.text,
                context_before=None,
                context_after=context_after,
                result_type="fuzzy",
                fuzzy_score=score,
                source_line_id=p.id
            )
            results.append(res)
            
        total_duration = time.time() - start_time
        logger.info(f"[{query_id}] FUZZY search completed in {total_duration:.3f}s | Returned {len(results)}/{total} matches.")
            
        return SearchResults(
            query_id=query_id,
            fic_id=fic_id,
            version_id=version_id,
            search_type="fuzzy",
            total_matches=total,
            returned_results=len(results),
            results_truncated=truncated,
            results=results
        )

    async def search_semantic(self, fic_id: str, version_id: str, query: str, limit: int = 10) -> SearchResults:
        start_time = time.time()
        query_id = uuid.uuid4().hex
        logger.info(f"[{query_id}] Starting SEMANTIC search | fic={fic_id} | query='{query}'")
        
        embed_start = time.time()
        query_vector = await self.embedding.embed_query(query)
        embed_duration = time.time() - embed_start
        logger.debug(f"[{query_id}] Query embedding took {embed_duration:.3f}s.")
        
        qdrant_start = time.time()
        hits = await self.vector_store.search(query_vector, fic_id, version_id, limit=20)
        qdrant_duration = time.time() - qdrant_start
        logger.debug(f"[{query_id}] Qdrant search took {qdrant_duration:.3f}s. Retrieved {len(hits)} candidates.")
        
        results = []
        seen_ranges = set()
        
        for hit in hits:
            payload = hit["payload"]
            chapter_number = payload["chapter_number"]
            start_p = payload["start_paragraph"]
            end_p = payload["end_paragraph"]
            
            is_overlap = False
            for seen_ch, seen_s, seen_e in seen_ranges:
                if chapter_number == seen_ch:
                    if not (end_p < seen_s or start_p > seen_e):
                        is_overlap = True
                        break
            
            if is_overlap:
                continue
                
            seen_ranges.add((chapter_number, start_p, end_p))
            
            chapter = await self.repo.get_chapter_by_number(fic_id, version_id, chapter_number)
            if not chapter:
                continue
                
            context_paras = await self._fetch_context(chapter.id, start_p, end_p, 2, 2)
            
            matched_lines = []
            before_lines = []
            after_lines = []
            
            for p in context_paras:
                if p.paragraph_number < start_p:
                    before_lines.append(p.text)
                elif p.paragraph_number > end_p:
                    after_lines.append(p.text)
                else:
                    matched_lines.append(p.text)
                    
            res = SearchResult(
                fic_id=fic_id,
                version_id=version_id,
                chapter_id=chapter.id,
                chapter_number=chapter.chapter_number,
                chapter_title=chapter.chapter_title,
                start_position=start_p,
                end_position=end_p,
                matched_text="\n\n".join(matched_lines),
                context_before="\n\n".join(before_lines) if before_lines else None,
                context_after="\n\n".join(after_lines) if after_lines else None,
                result_type="semantic",
                semantic_score=hit["score"],
                source_chunk_id=hit["id"]
            )
            
            results.append(res)
            
            if len(results) >= limit:
                break
                
        total_duration = time.time() - start_time
        logger.info(f"[{query_id}] SEMANTIC search completed in {total_duration:.3f}s | Deduplicated to {len(results)} results.")
                
        return SearchResults(
            query_id=query_id,
            fic_id=fic_id,
            version_id=version_id,
            search_type="semantic",
            total_matches=len(hits),
            returned_results=len(results),
            results_truncated=len(hits) > limit,
            results=results
        )
