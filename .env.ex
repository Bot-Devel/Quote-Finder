# --- Core Secrets ---
DISCORD_TOKEN=""
ROOT_USER_ID=""
DATABASE_URL="postgresql://user:password@hostname:5432/dbname"
QDRANT_URL="https://your-cluster-url.qdrant.tech"
QDRANT_API_KEY="<your-qdrant-api-key>"

# --- Ingestion & Provider Settings ---
# INGESTION_TEMP_DIR="/tmp/quote-finder"
# INGESTION_MAX_EPUB_BYTES="262144000" # 250 MB
# INGESTION_MAX_EXTRACTED_BYTES="1073741824" # 1 GB
# INGESTION_CONCURRENCY="1"
# INGESTION_KEEP_FAILED_DATA="false"

# --- Semantic Chunking Parameters ---
# CHUNK_TARGET_WORDS="400"
# CHUNK_MIN_WORDS="200"
# CHUNK_MAX_WORDS="650"
# CHUNK_OVERLAP_WORDS="75"

# --- Batch Size Settings ---
# EMBEDDING_BATCH_SIZE="32"
# QDRANT_BATCH_SIZE="128"
# DATABASE_BATCH_SIZE="500"
