# src/ingest/indexer.py
from __future__ import annotations

from typing import List, Dict, Any
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from src.ingest.chunking import Chunk


def build_chroma_index(
    *,
    persist_dir: str,
    collection_name: str,
    chunks: List[Chunk],
    doc_id: str,
    run_id: str = "",
) -> int:
    """Index chunks into Chroma.

    When ``run_id`` is provided (agent mode), performs a cross-run dedup check:
    if this ``doc_id`` is already present in the collection it is skipped
    entirely so documents are stored only once globally.
    """
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=persist_dir)

    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    col = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )

    # Cross-run dedup: if this doc is already in the collection, skip re-embedding.
    if run_id:
        try:
            existing = col.get(where={"doc_id": doc_id}, include=[], limit=1)
            if existing and existing.get("ids"):
                return 0  # already indexed globally, reuse existing chunks
        except Exception:
            pass  # get() failed — fall through and index normally

    ids = [f"{doc_id}:{c.chunk_id}" for c in chunks]
    docs = [c.text for c in chunks]
    metas: List[Dict[str, Any]] = [
        {
            "doc_id": doc_id,
            "chunk_id": c.chunk_id,
            "start_char": c.start_char,
            "end_char": c.end_char,
            "run_id": run_id,
        }
        for c in chunks
    ]

    col.add(ids=ids, documents=docs, metadatas=metas)
    return len(chunks)
