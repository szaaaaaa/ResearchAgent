from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from src.agent.artifacts.registry import ArtifactRegistry
from src.agent.core.budget import BudgetGuard
from src.agent.core.config import normalize_and_validate_config
from src.agent.core.events import emit_event
from src.agent.core.schemas import ResearchState
from src.agent.plugins.bootstrap import ensure_plugins_registered
from src.agent.roles import ConductorAgent, CriticAgent, ResearcherAgent
from src.agent.runtime.context import RunContext
from src.agent.runtime.policy import budget_guard_allows, can_retry, hitl_gate

logger = logging.getLogger(__name__)


def _build_initial_state(*, topic: str, cfg: dict[str, Any], run_id: str, max_iterations: int) -> ResearchState:
    return {
        "topic": topic,
        "artifacts": [],
        "planning": {},
        "research": {},
        "evidence": {},
        "review": {},
        "report": {},
        "iteration": 0,
        "max_iterations": max_iterations,
        "should_continue": False,
        "await_experiment_results": False,
        "_focus_research_questions": [],
        "status": "Starting Research OS orchestration",
        "error": None,
        "run_id": run_id,
        "_cfg": cfg,
        "_artifact_objects": [],
        "research_questions": [],
        "search_queries": [],
        "scope": {},
        "budget": {},
        "query_routes": {},
        "memory_summary": "",
        "papers": [],
        "indexed_paper_ids": [],
        "figure_indexed_paper_ids": [],
        "web_sources": [],
        "indexed_web_ids": [],
        "analyses": [],
        "findings": [],
        "gaps": [],
        "claim_evidence_map": [],
        "evidence_audit_log": [],
        "synthesis": "",
        "experiment_plan": {},
        "experiment_results": {},
        "report_critic": {},
        "repair_attempted": False,
        "acceptance_metrics": {},
        "_academic_queries": [],
        "_web_queries": [],
    }


class ResearchOrchestrator:
    def __init__(self, *, cfg: dict[str, Any], root: Path | str = ".", resume_run_id: str | None = None) -> None:
        self.cfg = normalize_and_validate_config(cfg)
        self.root = Path(root).resolve()
        bg_cfg = self.cfg.get("budget_guard", {})
        guard = BudgetGuard(
            max_tokens=int(bg_cfg.get("max_tokens", 500000)),
            max_api_calls=int(bg_cfg.get("max_api_calls", 200)),
            max_wall_time_sec=float(bg_cfg.get("max_wall_time_sec", 600)),
        )
        run_id = str(resume_run_id or uuid.uuid4())
        self.cfg["_root"] = str(self.root)
        self.cfg["_run_id"] = run_id
        self.cfg["_budget_guard"] = guard
        self.context = RunContext(
            run_id=run_id,
            topic="",
            iteration=0,
            max_iterations=int(self.cfg.get("agent", {}).get("max_iterations", 3)),
            budget=guard,
            artifact_registry=ArtifactRegistry.for_runtime(cfg=self.cfg, run_id=run_id),
        )

    def run(self, *, topic: str) -> ResearchState:
        ensure_plugins_registered()
        self.context.topic = topic
        state = _build_initial_state(
            topic=topic,
            cfg=self.cfg,
            run_id=self.context.run_id,
            max_iterations=self.context.max_iterations,
        )
        retries = 0

        while True:
            allowed, reason = budget_guard_allows(self.context)
            if not allowed:
                state["status"] = reason or "Budget exceeded"
                state["error"] = reason
                return state

            conductor = ConductorAgent(context=self.context, state=state)
            researcher = ResearcherAgent(context=self.context, state=state)
            critic = CriticAgent(context=self.context, state=state)

            planned_skills = conductor.plan(self.context)
            logger.info("[ResearchOrchestrator] Planned skills: %s", ", ".join(planned_skills))

            artifacts = list(state.get("_artifact_objects", []))
            artifacts = researcher.execute_plan(planned_skills, artifacts)
            decision, critique_report = critic.evaluate(artifacts)
            state["iteration"] = self.context.iteration
            state["artifacts"] = [artifact.to_record() for artifact in state.get("_artifact_objects", [])]

            emit_event(
                self.cfg,
                {
                    "event": "os_critic_decision",
                    "run_id": self.context.run_id,
                    "decision": decision,
                    "iteration": self.context.iteration,
                    "critique_artifact_id": critique_report.artifact_id,
                },
            )

            if decision == "pass":
                state["status"] = "Research OS orchestration completed"
                report_ns = state.setdefault("report", {})
                if isinstance(report_ns, dict) and not str(report_ns.get("report", "")).strip():
                    report_ns["report"] = str(state.get("synthesis", ""))
                return state

            if decision == "block":
                state["status"] = "Research OS orchestration blocked by critic"
                state["error"] = "Blocked by critic"
                report_ns = state.setdefault("report", {})
                if isinstance(report_ns, dict) and not str(report_ns.get("report", "")).strip():
                    report_ns["report"] = str(state.get("synthesis", ""))
                return state

            if hitl_gate(state):
                state["status"] = "Research OS orchestration paused for HITL"
                return state

            if not can_retry(retries=retries, max_retries=conductor.policy.max_retries, context=self.context):
                state["status"] = "Research OS orchestration exhausted revise budget"
                state["error"] = "Critic requested revise after retry budget exhaustion"
                report_ns = state.setdefault("report", {})
                if isinstance(report_ns, dict) and not str(report_ns.get("report", "")).strip():
                    report_ns["report"] = str(state.get("synthesis", ""))
                return state

            retries += 1
            self.context.iteration += 1
            state["iteration"] = self.context.iteration
