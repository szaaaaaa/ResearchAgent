from __future__ import annotations

from typing import Any, Dict, List

from src.agent.infra.retrieval.chroma_retriever import retrieve_chunks as infra_retrieve_chunks
from src.agent.plugins.registry import register_retriever_backend


class DefaultRetrieverBackend:
    def retrieve(
        self,
        *,
        persist_dir: str,
        collection_name: str,
        query: str,
        top_k: int,
        candidate_k: int | None,
        reranker_model: str | None,
        allowed_doc_ids: List[str] | None,
        cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return infra_retrieve_chunks(
            persist_dir=persist_dir,
            collection_name=collection_name,
            query=query,
            top_k=top_k,
            candidate_k=candidate_k,
            reranker_model=reranker_model,
            allowed_doc_ids=allowed_doc_ids,
        )


register_retriever_backend("default_retriever", DefaultRetrieverBackend())
