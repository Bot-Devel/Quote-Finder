import re
import time
from loguru import logger
from search.models import SearchResult

async def focus_sentences(candidates, limit, query, query_id, reranker, config, fic_id, version_id):
    """
    Experimental sentence-focusing implementation.
    Removed from production search per requirements.
    """
    sentences_per_candidate = []
    flat_sentences = []
    for c in candidates[:limit]:
        chunk_text = c["chunk_text"]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk_text) if s.strip()]
        sentences_per_candidate.append(sentences)
        flat_sentences.extend(sentences)
        
    # Batch rerank all sentences
    if config.SEMANTIC_RERANK_ENABLED and reranker and flat_sentences:
        sentence_start = time.time()
        flat_scores = await reranker.rerank(query, flat_sentences)
        sentence_latency = time.time() - sentence_start
        logger.info(f"[{query_id}] Sentence focusing latency: {sentence_latency:.3f}s for {len(flat_sentences)} sentences")
    else:
        from rapidfuzz import fuzz
        flat_scores = [fuzz.token_set_ratio(query, s) for s in flat_sentences]

    score_idx = 0
    results = []
    for i, c in enumerate(candidates[:limit]):
        sentences = sentences_per_candidate[i]
        if not sentences:
            continue
            
        c_scores = flat_scores[score_idx:score_idx+len(sentences)]
        score_idx += len(sentences)
        
        best_idx = max(range(len(c_scores)), key=lambda j: c_scores[j])
        
        # Simple thresholding logic based on model or rapidfuzz
        threshold = 0.0 if config.SEMANTIC_RERANK_ENABLED else 40
        if c_scores[best_idx] > threshold:
            sentences[best_idx] = f"**{sentences[best_idx]}**"
            
        start_idx = max(0, best_idx - 3)
        end_idx = min(len(sentences), best_idx + 4)
        excerpt = " ".join(sentences[start_idx:end_idx])
        
        if start_idx > 0:
            excerpt = "... " + excerpt
        if end_idx < len(sentences):
            excerpt = excerpt + " ..."
            
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
    return results
