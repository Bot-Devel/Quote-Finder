from typing import Literal, Optional
from dataclasses import dataclass

SearchResultType = Literal["exact", "fuzzy", "semantic"]

@dataclass
class SearchResult:
    fic_id: str
    version_id: str

    chapter_id: str
    chapter_number: int
    chapter_title: Optional[str]

    start_position: int  # paragraph_number or start_paragraph
    end_position: int    # paragraph_number or end_paragraph

    matched_text: str
    context_before: Optional[str]
    context_after: Optional[str]

    result_type: SearchResultType

    fuzzy_score: Optional[float] = None
    semantic_score: Optional[float] = None

    source_line_id: Optional[str] = None
    source_chunk_id: Optional[str] = None

@dataclass
class SearchResults:
    query_id: str

    fic_id: str
    version_id: str

    search_type: SearchResultType

    total_matches: int
    returned_results: int
    results_truncated: bool

    results: list[SearchResult]
    
    # For evaluation
    evaluation_candidates: Optional[list] = None
