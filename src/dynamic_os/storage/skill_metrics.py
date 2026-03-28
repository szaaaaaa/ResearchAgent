from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from src.dynamic_os.contracts.artifact import now_iso as _now_iso


@dataclass(frozen=True)
class SkillMetrics:
    skill_id: str
    execution_count: int
    success_count: int
    fail_count: int
    avg_duration_ms: float
    utility_score: float


_DEFAULT_UTILITY = 0.5
_ALPHA = 0.3


def _compute_new_utility(
    old_utility: float,
    status: str,
    confidence: float,
    duration_ms: float,
) -> float:
    raw_scores = {"success": 1.0, "partial": 0.5, "failed": 0.0, "needs_replan": 0.0, "skipped": 0.0}
    raw = raw_scores.get(status, 0.0)
    duration_penalty = min(0.2, max(0.0, (duration_ms - 10_000) / 50_000))
    new_score = raw * confidence - duration_penalty
    return max(0.0, min(1.0, _ALPHA * new_score + (1 - _ALPHA) * old_utility))


class SkillMetricsStore(Protocol):
    def record_execution(self, skill_id: str, status: str, confidence: float, duration_ms: float) -> None: ...
    def get_utility(self, skill_id: str) -> float: ...
    def get_all_metrics(self) -> dict[str, SkillMetrics]: ...


class InMemorySkillMetricsStore:
    def __init__(self) -> None:
        self._data: dict[str, SkillMetrics] = {}

    def record_execution(self, skill_id: str, status: str, confidence: float, duration_ms: float) -> None:
        prev = self._data.get(skill_id)
        if prev is None:
            prev = SkillMetrics(
                skill_id=skill_id,
                execution_count=0,
                success_count=0,
                fail_count=0,
                avg_duration_ms=0.0,
                utility_score=_DEFAULT_UTILITY,
            )

        new_count = prev.execution_count + 1
        new_avg = prev.avg_duration_ms + (duration_ms - prev.avg_duration_ms) / new_count
        is_success = status == "success"
        is_fail = status in ("failed", "needs_replan")

        self._data[skill_id] = SkillMetrics(
            skill_id=skill_id,
            execution_count=new_count,
            success_count=prev.success_count + (1 if is_success else 0),
            fail_count=prev.fail_count + (1 if is_fail else 0),
            avg_duration_ms=new_avg,
            utility_score=_compute_new_utility(prev.utility_score, status, confidence, duration_ms),
        )

    def get_utility(self, skill_id: str) -> float:
        entry = self._data.get(skill_id)
        return entry.utility_score if entry is not None else _DEFAULT_UTILITY

    def get_all_metrics(self) -> dict[str, SkillMetrics]:
        return dict(self._data)


class SqliteSkillMetricsStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record_execution(self, skill_id: str, status: str, confidence: float, duration_ms: float) -> None:
        row = self._conn.execute(
            "SELECT execution_count, success_count, fail_count, avg_duration_ms, utility_score "
            "FROM skill_metrics WHERE skill_id = ?",
            (skill_id,),
        ).fetchone()

        if row is None:
            old_count, old_success, old_fail, old_avg, old_utility = 0, 0, 0, 0.0, _DEFAULT_UTILITY
        else:
            old_count, old_success, old_fail, old_avg, old_utility = (
                row["execution_count"],
                row["success_count"],
                row["fail_count"],
                row["avg_duration_ms"],
                row["utility_score"],
            )

        new_count = old_count + 1
        new_avg = old_avg + (duration_ms - old_avg) / new_count
        is_success = status == "success"
        is_fail = status in ("failed", "needs_replan")
        new_utility = _compute_new_utility(old_utility, status, confidence, duration_ms)

        self._conn.execute(
            """INSERT INTO skill_metrics
                (skill_id, execution_count, success_count, fail_count, avg_duration_ms, utility_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_id) DO UPDATE SET
                execution_count = excluded.execution_count,
                success_count   = excluded.success_count,
                fail_count      = excluded.fail_count,
                avg_duration_ms = excluded.avg_duration_ms,
                utility_score   = excluded.utility_score,
                updated_at      = excluded.updated_at
            """,
            (
                skill_id,
                new_count,
                old_success + (1 if is_success else 0),
                old_fail + (1 if is_fail else 0),
                new_avg,
                new_utility,
                _now_iso(),
            ),
        )
        self._conn.commit()

    def get_utility(self, skill_id: str) -> float:
        row = self._conn.execute(
            "SELECT utility_score FROM skill_metrics WHERE skill_id = ?", (skill_id,),
        ).fetchone()
        return float(row["utility_score"]) if row is not None else _DEFAULT_UTILITY

    def get_all_metrics(self) -> dict[str, SkillMetrics]:
        rows = self._conn.execute("SELECT * FROM skill_metrics").fetchall()
        return {
            row["skill_id"]: SkillMetrics(
                skill_id=row["skill_id"],
                execution_count=row["execution_count"],
                success_count=row["success_count"],
                fail_count=row["fail_count"],
                avg_duration_ms=row["avg_duration_ms"],
                utility_score=row["utility_score"],
            )
            for row in rows
        }
