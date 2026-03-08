from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.agent.artifacts.base import Artifact
from src.agent.roles.base import RoleAgent, RolePolicy
from src.agent.runtime.policy import critic_action

if TYPE_CHECKING:
    from src.agent.runtime.context import RunContext


def _latest_artifact(artifacts: list[Artifact], artifact_type: str) -> Artifact | None:
    matches = [artifact for artifact in artifacts if artifact.artifact_type == artifact_type]
    if not matches:
        return None
    return matches[-1]


class CriticAgent(RoleAgent):
    def __init__(self, *, context: RunContext, state: dict[str, Any]) -> None:
        super().__init__(
            policy=RolePolicy(
                role_id="critic",
                system_prompt="Evaluate retrieval quality and decide pass, revise, or block.",
                allowed_skills=["critique_retrieval"],
                max_retries=int(state.get("_cfg", {}).get("reviewer", {}).get("retrieval", {}).get("max_retries", 1)),
                budget_limit_tokens=int(state.get("_cfg", {}).get("budget_guard", {}).get("max_tokens", 500000)),
            ),
            context=context,
            state=state,
        )

    def evaluate(self, artifacts: list[Any]) -> tuple[str, Artifact]:
        current_artifacts = [artifact for artifact in artifacts if isinstance(artifact, Artifact)]
        output_artifacts = self.execute("critique_retrieval", current_artifacts)
        current_artifacts.extend(output_artifacts)
        critique_report = _latest_artifact(output_artifacts, "CritiqueReport")
        if critique_report is None:
            raise RuntimeError("critique_retrieval must produce CritiqueReport")

        verdict = dict(critique_report.payload.get("verdict", {}))
        details = dict(critique_report.payload.get("details", {}))
        reviewer_log = list(self.state.get("review", {}).get("reviewer_log", []))
        reviewer_log.append(verdict)

        self.state["_artifact_objects"] = current_artifacts
        self.state["artifacts"] = [artifact.to_record() for artifact in current_artifacts]
        self.state.setdefault("review", {})
        self.state["review"]["retrieval_review"] = details
        self.state["review"]["reviewer_log"] = reviewer_log
        self.state["status"] = f"Critic {critic_action(verdict)}"
        return critic_action(verdict), critique_report
