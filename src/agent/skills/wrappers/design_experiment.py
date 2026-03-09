from __future__ import annotations

from typing import Any

from src.agent.core.artifact_utils import make_artifact, records_to_artifacts
from src.agent.skills.contract import SkillResult, SkillSpec
from src.agent.skills.wrappers import (
    get_artifact_records,
    get_base_state,
    get_cfg_for_stage,
    get_research_questions,
    get_topic,
)
from src.agent.stages.experiments import ingest_experiment_results, recommend_experiments

SPEC = SkillSpec(
    skill_id="design_experiment",
    purpose="Generate experiment plans or ingest submitted experiment results into reusable artifacts.",
    input_artifact_types=[],
    output_artifact_types=["ExperimentPlan", "ExperimentResults"],
)


def _has_existing_results(base_state: dict[str, Any]) -> bool:
    results = base_state.get("experiment_results", {})
    if not isinstance(results, dict):
        return False
    status = str(results.get("status") or "").strip().lower()
    raw_results = results.get("raw_results")
    return bool(results.get("runs") or raw_results not in (None, "", {}) or status not in {"", "pending"})


def _normalize_results_payload(
    *,
    update: dict[str, Any],
    base_state: dict[str, Any],
) -> dict[str, Any]:
    results = update.get("experiment_results", base_state.get("experiment_results", {}))
    payload = dict(results) if isinstance(results, dict) else {}
    if payload:
        return payload
    if bool(update.get("await_experiment_results", False)):
        return {
            "status": "pending",
            "runs": [],
            "summaries": [],
            "validation_issues": [],
        }
    return {
        "status": "skipped",
        "runs": [],
        "summaries": [],
        "validation_issues": [],
    }


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    del input_artifacts

    base_state = get_base_state(cfg)
    state = dict(base_state)
    state["artifacts"] = get_artifact_records(base_state)
    state["_cfg"] = get_cfg_for_stage(cfg)

    if _has_existing_results(base_state):
        update = ingest_experiment_results(state)
    else:
        update = recommend_experiments(state)

    plan_payload = update.get("experiment_plan", base_state.get("experiment_plan", {}))
    if not isinstance(plan_payload, dict):
        plan_payload = {}

    results_payload = _normalize_results_payload(update=update, base_state=base_state)
    source_inputs = get_research_questions(base_state)
    if not source_inputs:
        topic = get_topic(base_state)
        source_inputs = [topic] if topic else []

    artifacts = [
        make_artifact(
            artifact_type="ExperimentPlan",
            producer=SPEC.skill_id,
            payload=dict(plan_payload),
            source_inputs=source_inputs,
        ),
        make_artifact(
            artifact_type="ExperimentResults",
            producer=SPEC.skill_id,
            payload=results_payload,
            source_inputs=source_inputs,
        ),
    ]
    return SkillResult(success=True, output_artifacts=records_to_artifacts(artifacts))
