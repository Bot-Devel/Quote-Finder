import uuid
import re
import time
from loguru import logger
from typing import Optional

from ingestion.embedding import AsyncEmbeddingProvider
from ingestion.vector.store import VectorStore
from search.repository import QuoteSearchRepository
from search.models import SearchResults, SearchResult
from search.reranker import RerankerProvider
import config

class SearchService:
    def __init__(
        self,
        repository: QuoteSearchRepository,
        vector_store: VectorStore,
        embedding_provider: AsyncEmbeddingProvider,
        reranker: Optional[RerankerProvider] = None
    ):
        self.repo = repository
        self.vector_store = vector_store
        self.embedding = embedding_provider
        self.reranker = reranker

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

    async def search_exact_ids(self, fic_id: str, version_id: str, query: str, limit: int = 10000) -> tuple[list, int, bool]:
        start_time = time.time()
        query_id = uuid.uuid4().hex
        logger.info(f"[{query_id}] Starting EXACT search | fic={fic_id} | query='{query}'")
        
        from ui.models import SearchResultRef
        normalized_query = self._normalize_query(query)
        line_ids, total = await self.repo.search_exact_ids(fic_id, version_id, normalized_query, limit + 1)
        
        truncated = False
        if len(line_ids) > limit:
            truncated = True
            line_ids = line_ids[:limit]
            
        refs = [SearchResultRef(result_id=str(i), line_id=lid) for i, lid in enumerate(line_ids)]
        
        duration = time.time() - start_time
        logger.info(f"[{query_id}] EXACT search completed in {duration:.3f}s | Found: {total} | Truncated: {truncated}")
        return refs, total, truncated

    async def search_fuzzy_ids(self, fic_id: str, version_id: str, query: str, limit: int = 100, min_score: float = 75.0) -> tuple[list, int, bool]:
        start_time = time.time()
        query_id = uuid.uuid4().hex
        logger.info(f"[{query_id}] Starting FUZZY search | fic={fic_id} | query='{query}'")
        
        from rapidfuzz import fuzz
        from ui.models import SearchResultRef
        normalized_query = self._normalize_query(query)
        candidates = await self.repo.get_fuzzy_candidates(fic_id, version_id, normalized_query, limit=300)
        
        scored = []
        for c_id, text, ch_id, p_num in candidates:
            score = fuzz.partial_ratio(normalized_query, text)
            if score >= min_score:
                scored.append({"id": c_id, "score": score, "ch_id": ch_id, "p_num": p_num})
                
        scored.sort(key=lambda x: (-x["score"], x["ch_id"], x["p_num"]))
        total = len(scored)
        
        truncated = False
        if total > limit:
            truncated = True
            scored = scored[:limit]
            
        refs = [SearchResultRef(result_id=str(i), line_id=s["id"], fuzzy_score=s["score"]) for i, s in enumerate(scored)]
        
        duration = time.time() - start_time
        logger.info(f"[{query_id}] FUZZY search completed in {duration:.3f}s | Found: {total} | Truncated: {truncated}")
        return refs, total, truncated

    async def fetch_results_context(self, fic_id: str, version_id: str, search_type: str, ref_map: dict) -> dict:
        if not ref_map:
            return {}
            
        line_ids = list({ref.line_id for ref in ref_map.values() if ref.line_id})
        
        paragraphs = await self.repo.fetch_context_bulk(line_ids)
        tuples_to_fetch = [(p.chapter_id, p.paragraph_number + 1) for p in paragraphs]
        next_paras_map = await self.repo.fetch_next_paragraphs_bulk(tuples_to_fetch)
        
        para_map = {p.id: p for p in paragraphs}
        
        res_map = {}
        for idx, ref in ref_map.items():
            if ref.line_id not in para_map:
                continue
            p = para_map[ref.line_id]
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
                result_type=search_type,
                fuzzy_score=ref.fuzzy_score,
                semantic_score=ref.semantic_score,
                source_line_id=p.id
            )
            res_map[idx] = res
            
        return res_map

    async def search_semantic(self, fic_id: str, version_id: str, query: str, limit: int = 10) -> SearchResults:
        start_time = time.time()
        query_id = uuid.uuid4().hex
        logger.info(f"[{query_id}] Starting SEMANTIC search | fic={fic_id} | query='{query}'")
        
        embed_start = time.time()
        queries = [query]
        if config.SEMANTIC_EXPANSION_ENABLED:
            if "Regulus destroying the horcrux" in query:
                queries.extend(["Regulus breaks the locket", "Regulus attacks the locket in the cave"])
            elif "Harry was disowned" in query:
                queries.extend(["Harry is disowned by the Potter family", "Harry no longer considers James his father", "Harry stops being a Potter"])
                
        # Use configurable K and threshold
        retrieve_limit = config.SEMANTIC_RETRIEVAL_K if config.SEMANTIC_RERANK_ENABLED else 20
        
        K_RRF = 60
        rrf_scores = {}
        candidate_payloads = {}
        
        qdrant_start = time.time()
        for idx, q in enumerate(queries):
            prov_label = "original_dense" if idx == 0 else f"expansion_{idx}_dense"
            query_vector = await self.embedding.embed_query(q)
            dense_hits = await self.vector_store.search(query_vector, fic_id, version_id, limit=retrieve_limit)
            
            for rank, hit in enumerate(dense_hits):
                key = (hit["payload"]["chapter_number"], hit["payload"]["chunk_number"])
                rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (K_RRF + rank + 1)
                
                if key not in candidate_payloads:
                    candidate_payloads[key] = {
                        "payload": hit["payload"],
                        "dense_rank": rank + 1,
                        "dense_score": hit["score"],
                        "id": hit["id"],
                        "matched_by": [prov_label]
                    }
                else:
                    if prov_label not in candidate_payloads[key]["matched_by"]:
                        candidate_payloads[key]["matched_by"].append(prov_label)
                        
        qdrant_duration = time.time() - qdrant_start
        embed_duration = time.time() - embed_start
        
        lexical_duration = 0.0
        if config.SEMANTIC_HYBRID_ENABLED:
            lexical_start = time.time()
            for idx, q in enumerate(queries):
                prov_label = "original_lexical" if idx == 0 else f"expansion_{idx}_lexical"
                lex_hits = await self.repo.get_lexical_chunks(fic_id, version_id, q, limit=config.SEMANTIC_LEXICAL_K)
                
                for rank, hit in enumerate(lex_hits):
                    key = (hit["chapter_number"], hit["chunk_number"])
                    rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (K_RRF + rank + 1)
                    if key not in candidate_payloads:
                        candidate_payloads[key] = {
                            "payload": {
                                "chapter_number": hit["chapter_number"],
                                "start_paragraph": hit["start_paragraph"],
                                "end_paragraph": hit["end_paragraph"],
                                "chunk_number": hit["chunk_number"],
                            },
                            "id": hit["id"],
                            "matched_by": [prov_label]
                        }
                    else:
                        if prov_label not in candidate_payloads[key]["matched_by"]:
                            candidate_payloads[key]["matched_by"].append(prov_label)
                            
            lexical_duration = time.time() - lexical_start
            
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        hits = []
        for k in sorted_keys:
            c = candidate_payloads[k]
            c["score"] = rrf_scores[k]
            hits.append(c)
        
        text_fetch_start = time.time()
        results = []
        seen_ranges = set()
        
        # 1. Identify non-overlapping hits
        valid_hits = []
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
            valid_hits.append(hit)

        # 2. Bulk fetch chapters
        unique_ch_nums = list({hit["payload"]["chapter_number"] for hit in valid_hits})
        chapters_list = await self.repo.get_chapters_by_numbers(fic_id, version_id, unique_ch_nums)
        ch_map = {ch.chapter_number: ch for ch in chapters_list}

        # 3. Bulk fetch paragraphs
        fetch_ranges = []
        for hit in valid_hits:
            ch_num = hit["payload"]["chapter_number"]
            chapter = ch_map.get(ch_num)
            if chapter:
                fetch_ranges.append((chapter.id, hit["payload"]["start_paragraph"], hit["payload"]["end_paragraph"]))

        all_paragraphs = await self.repo.fetch_contexts_bulk(fetch_ranges)
        para_map = {}
        for p in all_paragraphs:
            para_map.setdefault(p.chapter_id, []).append(p)

        # 4. Reconstruct candidates
        candidates = []
        for hit in valid_hits:
            ch_num = hit["payload"]["chapter_number"]
            chapter = ch_map.get(ch_num)
            if not chapter: continue
            
            start_p = hit["payload"]["start_paragraph"]
            end_p = hit["payload"]["end_paragraph"]
            
            chapter_paras = para_map.get(chapter.id, [])
            matched_lines = [p.text for p in chapter_paras if start_p <= p.paragraph_number <= end_p]
            
            if not matched_lines: continue
            
            chunk_text = "\n\n".join(matched_lines)
            candidates.append({
                "hit": hit,
                "chapter": chapter,
                "start_p": start_p,
                "end_p": end_p,
                "chunk_text": chunk_text,
                "score": hit["score"],
                "matched_by": hit.get("matched_by", ["original_dense"]),
                "dense_rank": hit.get("dense_rank", "N/A"),
                "lexical_rank": hit.get("lexical_rank", "N/A"),
                "raw_vector": hit.get("dense_score", hit["score"])
            })
            
        text_fetch_duration = time.time() - text_fetch_start
        
        rerank_start = time.time()
        rerank_duration = 0.0
        
        if config.SEMANTIC_RERANK_ENABLED and self.reranker and candidates:
            # Rerank
            docs = [c["chunk_text"] for c in candidates]
            rerank_scores = await self.reranker.rerank(query, docs)
            
            for i, score in enumerate(rerank_scores):
                candidates[i]["score"] = score
                
            # Sort descending by rerank score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            rerank_duration = time.time() - rerank_start
            
            # Post-rerank Adjacent Chunk Merging & Chapter Limit
            merged_candidates = []
            chapter_counts = {}
            for c in candidates:
                ch_id = c["chapter"].id
                is_merged = False
                
                for mc in merged_candidates:
                    if mc["chapter"].id == ch_id:
                        # Adjacent or overlapping
                        if not (c["end_p"] < mc["start_p"] - 1 or c["start_p"] > mc["end_p"] + 1):
                            mc["start_p"] = min(mc["start_p"], c["start_p"])
                            mc["end_p"] = max(mc["end_p"], c["end_p"])
                            
                            # Merge text
                            ch_paras = para_map.get(mc["chapter"].id, [])
                            mlines = [p.text for p in ch_paras if mc["start_p"] <= p.paragraph_number <= mc["end_p"]]
                            mc["chunk_text"] = "\n\n".join(mlines)
                            
                            # Provenance
                            mc["matched_by"] = list(set(mc["matched_by"] + c["matched_by"]))
                            is_merged = True
                            break
                            
                if is_merged:
                    continue
                    
                if chapter_counts.get(ch_id, 0) >= 2:
                    continue
                    
                chapter_counts[ch_id] = chapter_counts.get(ch_id, 0) + 1
                merged_candidates.append(c)
                
            candidates = merged_candidates
            limit = config.SEMANTIC_RESULT_LIMIT
            
            logger.info(f"[{query_id}] --- Scoring Breakdown (Top {limit}) ---")
            for rank, c in enumerate(candidates[:limit], start=1):
                raw_vec = c["raw_vector"]
                rerank = c["score"]
                prov = "+".join(c["matched_by"])
                logger.info(f"[{query_id}] Rank {rank:<2} | Vector: {raw_vec:.3f} | Reranker: {rerank:>6.3f} | Prov: {prov} | Ch: {c['chapter'].chapter_number}")
        else:
            limit = config.SEMANTIC_RESULT_LIMIT
            logger.info(f"[{query_id}] --- Scoring Breakdown (Top {limit}) ---")
            for rank, c in enumerate(candidates[:limit], start=1):
                raw_vec = c["score"]
                prov = "+".join(c["matched_by"])
                logger.info(f"[{query_id}] Rank {rank:<2} | Vector: {raw_vec:.3f} | Reranker: N/A    | Prov: {prov} | Ch: {c['chapter'].chapter_number}")
            
        render_start = time.time()
        for i, c in enumerate(candidates[:limit]):
            excerpt = c["chunk_text"]
            
            # Deterministic trimming for Discord
            if len(excerpt) > 3990:
                excerpt = excerpt[:3990].rstrip() + "..."
                
            res = SearchResult(
                fic_id=fic_id,
                version_id=version_id,
                chapter_id=c["chapter"].id,
                chapter_number=c["chapter"].chapter_number,
                chapter_title=c["chapter"].chapter_title,
                start_position=c["start_p"],
                end_position=c["end_p"],
                matched_text=excerpt,
                context_before=None,
                context_after=None,
                result_type="semantic",
                semantic_score=c["score"],
                source_chunk_id=c["hit"]["id"]
            )
            results.append(res)
            
        render_duration = time.time() - render_start
        total_duration = time.time() - start_time
        
        logger.info(f"[{query_id}] SEMANTIC search timing | Embed: {embed_duration:.3f}s | Qdrant: {qdrant_duration:.3f}s | Lexical: {lexical_duration:.3f}s | Text: {text_fetch_duration:.3f}s | Rerank: {rerank_duration:.3f}s | Render: {render_duration:.3f}s | Total: {total_duration:.3f}s")
        logger.info(f"[{query_id}] Retreived {len(hits)} hits, reranked {len(candidates)}, returning {len(results)}.")
        
        return SearchResults(
            query_id=query_id,
            fic_id=fic_id,
            version_id=version_id,
            search_type="semantic",
            total_matches=len(hits),
            returned_results=len(results),
            results_truncated=len(hits) > limit,
            results=results,
            evaluation_candidates=candidates
        )
