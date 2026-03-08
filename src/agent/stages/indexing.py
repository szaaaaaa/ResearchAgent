"""Indexing stage implementation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.agent.core.artifact_utils import append_artifacts, make_artifact, records_to_artifacts
from src.agent.core.executor import TaskRequest
from src.agent.core.executor_router import dispatch as _default_dispatch
from src.agent.core.schemas import ResearchState
from src.agent.core.state_access import to_namespaced_update, with_flattened_legacy_view
from src.common.rag_config import retrieval_effective_embedding_model, scoped_collection_name

logger = logging.getLogger(__name__)


def _paper_is_indexable(paper: Dict[str, Any]) -> bool:
    pdf_path = paper.get("pdf_path")
    return bool(pdf_path) and Path(str(pdf_path)).exists()


def _select_figure_enrichment_papers(
    state: Dict[str, Any],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []

    papers_by_uid = {
        str(paper.get("uid")): paper
        for paper in state.get("papers", [])
        if isinstance(paper, dict) and paper.get("uid") and _paper_is_indexable(paper)
    }
    figure_done = set(state.get("figure_indexed_paper_ids", []))
    ordered_uids: List[str] = []
    seen_uids: set[str] = set()

    def _push(uid: str) -> None:
        if not uid or uid in seen_uids or uid in figure_done or uid not in papers_by_uid:
            return
        seen_uids.add(uid)
        ordered_uids.append(uid)

    for entry in state.get("claim_evidence_map", []):
        if not isinstance(entry, dict):
            continue
        for evidence in entry.get("evidence", []):
            if isinstance(evidence, dict):
                _push(str(evidence.get("uid") or ""))

    analyses = sorted(
        [item for item in state.get("analyses", []) if isinstance(item, dict)],
        key=lambda item: float(item.get("relevance_score", 0.0) or 0.0),
        reverse=True,
    )
    for analysis in analyses:
        _push(str(analysis.get("uid") or ""))

    for paper in state.get("papers", []):
        if isinstance(paper, dict):
            _push(str(paper.get("uid") or ""))

    return [papers_by_uid[uid] for uid in ordered_uids[:limit]]


def index_sources(
    state: ResearchState,
    *,
    state_view: Callable[[ResearchState], Dict[str, Any]] | None = None,
    get_cfg: Callable[[ResearchState], Dict[str, Any]] | None = None,
    ns: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
    dispatch: Callable[..., Any] | None = None,
) -> Dict[str, Any]:
    """Index newly fetched PDFs and web content into separate collections."""
    state_view = state_view or with_flattened_legacy_view
    get_cfg = get_cfg or (lambda current_state: current_state.get("_cfg", {}))
    ns = ns or to_namespaced_update
    dispatch = dispatch or _default_dispatch

    state = state_view(state)
    cfg = get_cfg(state)
    root = Path(cfg.get("_root", "."))
    run_id = cfg.get("_run_id", "")
    persist_dir = str(
        (root / cfg.get("index", {}).get("persist_dir", "data/indexes/chroma")).resolve()
    )
    sqlite_path = str(
        (
            root / cfg.get("metadata_store", {}).get("sqlite_path", "data/metadata/papers.sqlite")
        ).resolve()
    )
    paper_collection = cfg.get("index", {}).get("collection_name", "papers")
    web_collection = cfg.get("index", {}).get("web_collection_name", "web_sources")
    embedding_model = retrieval_effective_embedding_model(cfg)
    paper_collection = scoped_collection_name(
        cfg,
        base_name=str(paper_collection),
        embedding_model=embedding_model,
    )
    web_collection = scoped_collection_name(
        cfg,
        base_name=str(web_collection),
        embedding_model=embedding_model,
    )
    chunk_size = cfg.get("index", {}).get("chunk_size", 1200)
    overlap = cfg.get("index", {}).get("overlap", 200)

    if run_id:
        init_result = dispatch(
            TaskRequest(
                action="init_run_tracking",
                params={"sqlite_path": sqlite_path},
            ),
            cfg,
        )
        if not init_result.success:
            logger.warning("run_tracking init failed: %s", init_result.error)

        session_result = dispatch(
            TaskRequest(
                action="upsert_run_session_record",
                params={
                    "sqlite_path": sqlite_path,
                    "run_id": run_id,
                    "topic": state.get("topic", ""),
                },
            ),
            cfg,
        )
        if not session_result.success:
            logger.warning("run_session upsert failed: %s", session_result.error)

    new_paper_ids: List[str] = []
    new_web_ids: List[str] = []
    new_figure_ids: List[str] = []

    iteration = int(state.get("iteration", 0) or 0)
    staged_cfg = cfg.get("agent", {}).get("staged_indexing", {})
    staged_enabled = bool(staged_cfg.get("enabled", True))
    fast_text_only_until_iteration = int(staged_cfg.get("fast_text_only_until_iteration", 0))
    first_pass_text_extraction = str(staged_cfg.get("first_pass_text_extraction", "pymupdf_only"))
    figure_enrichment_start_iteration = int(staged_cfg.get("figure_enrichment_start_iteration", 1))
    figure_top_papers = int(staged_cfg.get("figure_top_papers", 4))
    figure_globally_enabled = bool(cfg.get("ingest", {}).get("figure", {}).get("enabled", True))

    already_indexed = set(state.get("indexed_paper_ids", []))
    papers = state.get("papers", [])
    to_index = [
        paper
        for paper in papers
        if _paper_is_indexable(paper)
        and paper["uid"] not in already_indexed
    ]

    if to_index:
        ingest_overrides: Dict[str, Any] = {}
        if staged_enabled and iteration <= fast_text_only_until_iteration:
            ingest_overrides = {
                "figure_enabled": False,
                "text_extraction": first_pass_text_extraction,
            }
        task_result = dispatch(
            TaskRequest(
                action="index_pdf_documents",
                params={
                    "persist_dir": persist_dir,
                    "collection_name": paper_collection,
                    "pdfs": [paper["pdf_path"] for paper in to_index],
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "run_id": run_id,
                    "ingest_overrides": ingest_overrides,
                    "allow_existing_doc_updates": False,
                    "include_text_chunks": True,
                },
            ),
            cfg,
        )
        if task_result.success:
            new_paper_ids = task_result.data.get("indexed_docs", [])
        else:
            logger.error("PDF indexing failed: %s", task_result.error)

    if staged_enabled and figure_globally_enabled and iteration >= figure_enrichment_start_iteration:
        figure_candidates = _select_figure_enrichment_papers(state, limit=figure_top_papers)
        if figure_candidates:
            figure_result = dispatch(
                TaskRequest(
                    action="index_pdf_documents",
                    params={
                        "persist_dir": persist_dir,
                        "collection_name": paper_collection,
                        "pdfs": [paper["pdf_path"] for paper in figure_candidates],
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "run_id": run_id,
                        "allow_existing_doc_updates": True,
                        "include_text_chunks": False,
                    },
                ),
                cfg,
            )
            if figure_result.success:
                new_figure_ids = [str(paper["uid"]) for paper in figure_candidates]
            else:
                logger.error("Figure enrichment indexing failed: %s", figure_result.error)

    all_submitted_paper_ids = [Path(paper["pdf_path"]).stem for paper in to_index]
    if run_id and all_submitted_paper_ids:
        run_docs_result = dispatch(
            TaskRequest(
                action="upsert_run_doc_records",
                params={
                    "sqlite_path": sqlite_path,
                    "run_id": run_id,
                    "doc_uids": all_submitted_paper_ids,
                    "doc_type": "paper",
                },
            ),
            cfg,
        )
        if not run_docs_result.success:
            logger.warning("run_docs upsert (papers) failed: %s", run_docs_result.error)

    already_web = set(state.get("indexed_web_ids", []))
    web_sources = state.get("web_sources", [])
    to_index_web = [web_source for web_source in web_sources if web_source.get("body") and web_source["uid"] not in already_web]

    for web_source in to_index_web:
        doc_id = web_source["uid"]
        text = web_source["body"]
        if len(text.strip()) < 100:
            continue
        chunks_result = dispatch(
            TaskRequest(
                action="chunk_text",
                params={
                    "text": text,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                },
            ),
            cfg,
        )
        if not chunks_result.success:
            logger.error("Web chunking failed for %s: %s", doc_id, chunks_result.error)
            continue
        chunks = chunks_result.data.get("chunks", [])
        if not chunks:
            continue
        index_result = dispatch(
            TaskRequest(
                action="build_web_index",
                params={
                    "persist_dir": persist_dir,
                    "collection_name": web_collection,
                    "chunks": chunks,
                    "doc_id": doc_id,
                    "run_id": run_id,
                },
            ),
            cfg,
        )
        if index_result.success:
            new_web_ids.append(doc_id)
        else:
            logger.error("Web indexing failed for %s: %s", doc_id, index_result.error)

    if run_id and new_web_ids:
        run_docs_result = dispatch(
            TaskRequest(
                action="upsert_run_doc_records",
                params={
                    "sqlite_path": sqlite_path,
                    "run_id": run_id,
                    "doc_uids": new_web_ids,
                    "doc_type": "web",
                },
            ),
            cfg,
        )
        if not run_docs_result.success:
            logger.warning("run_docs upsert (web) failed: %s", run_docs_result.error)

    cumulative_paper_ids = list(
        dict.fromkeys(list(state.get("indexed_paper_ids", [])) + new_paper_ids)
    )
    cumulative_figure_ids = list(
        dict.fromkeys(list(state.get("figure_indexed_paper_ids", [])) + new_figure_ids)
    )
    cumulative_web_ids = list(
        dict.fromkeys(list(state.get("indexed_web_ids", [])) + new_web_ids)
    )
    new_artifacts = [
        make_artifact(
            artifact_type="CorpusSnapshot",
            producer="index_sources",
            payload={
                "papers": list(state.get("papers", [])),
                "web_sources": list(state.get("web_sources", [])),
                "indexed_paper_ids": cumulative_paper_ids,
            },
            source_inputs=[str(uid) for uid in new_paper_ids + new_web_ids],
        )
    ]
    return ns(
        {
            "indexed_paper_ids": cumulative_paper_ids,
            "figure_indexed_paper_ids": cumulative_figure_ids,
            "indexed_web_ids": cumulative_web_ids,
            "artifacts": append_artifacts(state.get("artifacts", []), new_artifacts),
            "_artifacts": records_to_artifacts(new_artifacts),
            "status": (
                f"Indexed {len(new_paper_ids)} new PDFs, {len(new_web_ids)} new web pages "
                f"(cumulative: {len(cumulative_paper_ids)} papers, {len(cumulative_web_ids)} web)"
                + (f"; figure-enriched {len(new_figure_ids)} priority papers" if new_figure_ids else "")
            ),
        }
    )
