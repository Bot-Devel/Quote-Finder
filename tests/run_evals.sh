#!/bin/bash
set -e



echo "================================================="
echo "Experiment 1: Baseline (Dense 30, Tiny)"
export SEMANTIC_RETRIEVAL_K=30
export SEMANTIC_HYBRID_ENABLED=false
export SEMANTIC_EXPANSION_ENABLED=false
export SEMANTIC_RERANK_MODEL="jinaai/jina-reranker-v1-tiny-en"
.venv/bin/python eval_pipeline.py

echo "================================================="
echo "Experiment 2: Dense 50, Tiny"
export SEMANTIC_RETRIEVAL_K=50
.venv/bin/python eval_pipeline.py

echo "================================================="
echo "Experiment 3: Dense 50, BGE-m3"
export SEMANTIC_RERANK_MODEL="BAAI/bge-reranker-base"
.venv/bin/python eval_pipeline.py

echo "================================================="
echo "Experiment 4: Hybrid RRF, Tiny"
export SEMANTIC_RERANK_MODEL="jinaai/jina-reranker-v1-tiny-en"
export SEMANTIC_HYBRID_ENABLED=true
.venv/bin/python eval_pipeline.py

echo "================================================="
echo "Experiment 5: Hybrid RRF, BGE-m3"
export SEMANTIC_RERANK_MODEL="BAAI/bge-reranker-base"
.venv/bin/python eval_pipeline.py

echo "================================================="
echo "Experiment 6: Hybrid RRF + Expansion, BGE-m3"
export SEMANTIC_EXPANSION_ENABLED=true
.venv/bin/python eval_pipeline.py
