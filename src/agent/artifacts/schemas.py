from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, TypedDict

from src.agent.artifacts.base import Artifact, ArtifactMeta
from src.agent.core.schemas import (
    AnalysisResult,
    ArtifactRecord,
    ClaimEvidenceEntry,
    PaperRecord,
    ReviewerVerdict,
    WebResult,
)


class TopicBriefPayload(TypedDict):
    topic: str
    scope: Dict[str, Any]


class SearchPlanPayload(TypedDict):
    research_questions: list[str]
    search_queries: list[str]
    query_routes: Dict[str, Dict[str, Any]]


class CorpusSnapshotPayload(TypedDict):
    papers: list[PaperRecord]
    web_sources: list[WebResult]
    indexed_paper_ids: list[str]


class RelatedWorkMatrixPayload(TypedDict):
    narrative: str
    claims: list[ClaimEvidenceEntry]


class GapMapPayload(TypedDict):
    gaps: list[str]


class CritiqueReportPayload(TypedDict):
    verdict: ReviewerVerdict
    details: Dict[str, Any]


class ExperimentPlanPayload(TypedDict, total=False):
    domain: str
    subfield: str
    task_type: str
    rq_experiments: list[Dict[str, Any]]


class ExperimentResultsPayload(TypedDict, total=False):
    status: str
    submitted_by: str
    submitted_at: str
    runs: list[Dict[str, Any]]
    summaries: list[Dict[str, Any]]
    validation_issues: list[str]


class ExperimentAnalysisPayload(TypedDict, total=False):
    summary: str
    key_findings: list[str]
    performance_metrics: Dict[str, Any]
    runs_analyzed: int
    research_questions: list[str]
    result_status: str
    submitted_at: str
    submitted_by: str


class PerformanceMetricsPayload(TypedDict, total=False):
    status: str
    run_count: int
    summary_count: int
    research_question_count: int
    research_questions: list[str]
    metric_stats: Dict[str, Dict[str, Any]]
    validation_issue_count: int
    validated: bool


class ResearchReportPayload(TypedDict, total=False):
    report: str
    report_critic: Dict[str, Any]
    repair_attempted: bool
    acceptance_metrics: Dict[str, Any]
    status: str


@dataclass(frozen=True)
class TopicBrief(Artifact):
    payload: TopicBriefPayload


@dataclass(frozen=True)
class SearchPlan(Artifact):
    payload: SearchPlanPayload


@dataclass(frozen=True)
class CorpusSnapshot(Artifact):
    payload: CorpusSnapshotPayload


@dataclass(frozen=True)
class PaperNote(Artifact):
    payload: AnalysisResult


@dataclass(frozen=True)
class RelatedWorkMatrix(Artifact):
    payload: RelatedWorkMatrixPayload


@dataclass(frozen=True)
class GapMap(Artifact):
    payload: GapMapPayload


@dataclass(frozen=True)
class CritiqueReport(Artifact):
    payload: CritiqueReportPayload


@dataclass(frozen=True)
class ExperimentPlanArtifact(Artifact):
    payload: ExperimentPlanPayload


@dataclass(frozen=True)
class ExperimentResultsArtifact(Artifact):
    payload: ExperimentResultsPayload


@dataclass(frozen=True)
class ExperimentAnalysisArtifact(Artifact):
    payload: ExperimentAnalysisPayload


@dataclass(frozen=True)
class PerformanceMetricsArtifact(Artifact):
    payload: PerformanceMetricsPayload


@dataclass(frozen=True)
class ResearchReportArtifact(Artifact):
    payload: ResearchReportPayload


_ARTIFACT_CLASS_BY_TYPE = {
    "TopicBrief": TopicBrief,
    "SearchPlan": SearchPlan,
    "CorpusSnapshot": CorpusSnapshot,
    "PaperNote": PaperNote,
    "RelatedWorkMatrix": RelatedWorkMatrix,
    "GapMap": GapMap,
    "CritiqueReport": CritiqueReport,
    "ExperimentPlan": ExperimentPlanArtifact,
    "ExperimentResults": ExperimentResultsArtifact,
    "ExperimentAnalysis": ExperimentAnalysisArtifact,
    "PerformanceMetrics": PerformanceMetricsArtifact,
    "ResearchReport": ResearchReportArtifact,
}


def artifact_from_record(record: ArtifactRecord) -> Artifact:
    meta = ArtifactMeta(
        artifact_type=str(record.get("artifact_type", "")),
        artifact_id=str(record.get("artifact_id", "")),
        producer=str(record.get("producer", "")),
        source_inputs=list(record.get("source_inputs", [])),
        created_at=str(record.get("created_at", "")),
    )
    payload = dict(record.get("payload", {}))
    artifact_cls = _ARTIFACT_CLASS_BY_TYPE.get(meta.artifact_type, Artifact)
    return artifact_cls(meta=meta, payload=payload)
