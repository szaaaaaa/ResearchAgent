"""Backward-compatible state exports.

Prefer importing typed schemas from ``src.agent.core.schemas`` directly.
"""
from __future__ import annotations

from src.agent.core.schemas import (
    AnalysisResult,
    EvidenceNamespace,
    PaperRecord,
    PlanningNamespace,
    ReportNamespace,
    ResearchNamespace,
    ResearchState,
    RunMetrics,
    WebResult,
)

__all__ = [
    "ResearchState",
    "ResearchNamespace",
    "PlanningNamespace",
    "EvidenceNamespace",
    "ReportNamespace",
    "PaperRecord",
    "WebResult",
    "AnalysisResult",
    "RunMetrics",
]
