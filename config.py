import os
from dotenv import load_dotenv

from pathlib import Path

load_dotenv()

HOME_DIR = Path.home()

ROOT_USER_ID = int(
    os.getenv("QUOTE_FINDER_ROOT_USER_ID") or os.getenv("ROOT_USER_ID") or "0"
)

# --- Ingestion & Provider Settings ---
INGESTION_TEMP_DIR = os.getenv(
    "INGESTION_TEMP_DIR", str(HOME_DIR / "quote-finder" / "tmp")
)
EMBEDDING_CACHE_DIR = os.getenv(
    "EMBEDDING_CACHE_DIR", str(HOME_DIR / "quote-finder" / "models")
)
INGESTION_MAX_EPUB_BYTES = int(
    os.getenv("INGESTION_MAX_EPUB_BYTES", "262144000")
)  # 250 MB
INGESTION_MAX_EXTRACTED_BYTES = int(
    os.getenv("INGESTION_MAX_EXTRACTED_BYTES", "1073741824")
)  # 1 GB
INGESTION_CONCURRENCY = int(os.getenv("INGESTION_CONCURRENCY", "1"))
INGESTION_KEEP_FAILED_DATA = (
    os.getenv("INGESTION_KEEP_FAILED_DATA", "false").lower() == "true"
)

# --- Semantic Chunking Parameters ---
CHUNK_TARGET_WORDS = int(os.getenv("CHUNK_TARGET_WORDS", "400"))
CHUNK_MIN_WORDS = int(os.getenv("CHUNK_MIN_WORDS", "200"))
CHUNK_MAX_WORDS = int(os.getenv("CHUNK_MAX_WORDS", "650"))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", "75"))

# --- Batch Size Settings ---
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", "128"))
DATABASE_BATCH_SIZE = int(os.getenv("DATABASE_BATCH_SIZE", "500"))

# --- Semantic Search & Reranking Settings ---
# --- Semantic Search & Reranking Settings ---
SEMANTIC_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
SEMANTIC_RERANK_ENABLED = (
    os.getenv("SEMANTIC_RERANK_ENABLED", "false").lower() == "true"
)
SEMANTIC_RERANK_MODEL = os.getenv(
    "SEMANTIC_RERANK_MODEL", "jinaai/jina-reranker-v1-tiny-en"
)
SEMANTIC_RETRIEVAL_K = int(os.getenv("SEMANTIC_RETRIEVAL_K", "30"))
SEMANTIC_RESULT_LIMIT = int(os.getenv("SEMANTIC_RESULT_LIMIT", "10"))

# Hybrid Search Config
SEMANTIC_HYBRID_ENABLED = (
    os.getenv("SEMANTIC_HYBRID_ENABLED", "false").lower() == "true"
)
SEMANTIC_LEXICAL_K = int(os.getenv("SEMANTIC_LEXICAL_K", "30"))

# Query Expansion Config
SEMANTIC_EXPANSION_ENABLED = (
    os.getenv("SEMANTIC_EXPANSION_ENABLED", "false").lower() == "true"
)
