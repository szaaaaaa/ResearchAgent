from __future__ import annotations

from typing import Any

from src.agent.runtime.context import RunContext


def budget_guard_allows(context: RunContext) -> tuple[bool, str | None]:
    result = context.budget.check()
    if result.get("exceeded", False):
        return False, str(result.get("reason") or "Budget exceeded")
    return True, None


def critic_action(verdict: dict[str, Any]) -> str:
    action = str(verdict.get("action", "continue")).strip().lower()
    if action == "retry_upstream":
        return "revise"
    if action == "block":
        return "block"
    return "pass"


def can_retry(*, retries: int, max_retries: int, context: RunContext) -> bool:
    if retries >= max_retries:
        return False
    if context.iteration >= context.max_iterations:
        return False
    allowed, _ = budget_guard_allows(context)
    return allowed


def hitl_gate(state: dict[str, Any]) -> bool:
    return bool(state.get("await_experiment_results", False))
