"""Backward-compatible state exports.

Prefer importing typed schemas from ``src.agent.core.schemas`` directly.
"""
from __future__ import annotations

from src.agent.core.schemas import AnalysisResult, PaperRecord, ResearchState, RunMetrics, WebResult

__all__ = [
    "ResearchState",
    "PaperRecord",
    "WebResult",
    "AnalysisResult",
    "RunMetrics",
]
