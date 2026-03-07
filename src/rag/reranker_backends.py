from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from src.common.rag_config import retrieval_device

_LOCAL_CROSS_ENCODER_BACKENDS = {"local_crossencoder", "crossencoder", "local"}


def _normalize_backend_name(backend_name: str) -> str:
    raw = str(backend_name or "local_crossencoder").strip().lower()
    if raw in _LOCAL_CROSS_ENCODER_BACKENDS:
        return "local_crossencoder"
    if raw == "disabled":
        return "disabled"
    return raw


def _resolve_local_device(cfg: Dict[str, Any] | None) -> str:
    requested = retrieval_device(cfg or {})
    if requested != "auto":
        return requested
    try:
        import torch
    except Exception:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@lru_cache(maxsize=4)
def _get_local_reranker(model_name: str, device: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device)


def rerank_hits(
    query: str,
    hits: List[Dict[str, Any]],
    *,
    model_name: str,
    backend_name: str = "local_crossencoder",
    cfg: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if not hits:
        return []

    backend = _normalize_backend_name(backend_name)
    if backend == "disabled" or not model_name:
        return list(hits)
    if backend != "local_crossencoder":
        raise ValueError(f"Unsupported reranker backend '{backend_name}'")

    model = _get_local_reranker(model_name, _resolve_local_device(cfg))
    pairs = [(query, hit["text"]) for hit in hits]
    scores = model.predict(pairs)

    reranked: List[Dict[str, Any]] = []
    for hit, score in zip(hits, scores):
        entry = dict(hit)
        entry["reranker_score"] = float(score)
        reranked.append(entry)
    reranked.sort(key=lambda item: item["reranker_score"], reverse=True)
    return reranked
