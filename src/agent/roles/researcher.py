from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.agent.artifacts.base import Artifact
from src.agent.core.config import DEFAULT_CORE_MIN_A_RATIO
from src.agent.core.evidence import _build_evidence_audit_log
from src.agent.roles.base import RoleAgent, RolePolicy

if TYPE_CHECKING:
    from src.agent.runtime.context import RunContext


def _latest_artifact(artifacts: list[Artifact], artifact_type: str) -> Artifact | None:
    matches = [artifact for artifact in artifacts if artifact.artifact_type == artifact_type]
    if not matches:
        return None
    return matches[-1]


class ResearcherAgent(RoleAgent):
    def __init__(self, *, context: RunContext, state: dict[str, Any]) -> None:
        super().__init__(
            policy=RolePolicy(
                role_id="researcher",
                system_prompt="Execute literature-review skills in conductor-planned order.",
                allowed_skills=[
                    "search_literature",
                    "parse_paper_bundle",
                    "extract_paper_notes",
                    "build_related_work_matrix",
                ],
                max_retries=int(state.get("_cfg", {}).get("reviewer", {}).get("retrieval", {}).get("max_retries", 1)),
                budget_limit_tokens=int(state.get("_cfg", {}).get("budget_guard", {}).get("max_tokens", 500000)),
            ),
            context=context,
            state=state,
        )

    def execute_plan(self, skill_ids: list[str], artifacts: list[Any]) -> list[Artifact]:
        current_artifacts = [artifact for artifact in artifacts if isinstance(artifact, Artifact)]
        for skill_id in skill_ids:
            output_artifacts = self.execute(skill_id, current_artifacts)
            current_artifacts.extend(output_artifacts)
            self.state["_artifact_objects"] = current_artifacts
            self.state["artifacts"] = [artifact.to_record() for artifact in current_artifacts]
            self._apply_skill_outputs(skill_id, output_artifacts, current_artifacts)
        return current_artifacts

    def _apply_skill_outputs(
        self,
        skill_id: str,
        output_artifacts: list[Artifact],
        all_artifacts: list[Artifact],
    ) -> None:
        if skill_id in {"search_literature", "parse_paper_bundle"}:
            corpus_snapshot = _latest_artifact(output_artifacts, "CorpusSnapshot")
            if corpus_snapshot is None:
                raise RuntimeError(f"{skill_id} must produce CorpusSnapshot")
            self.state["papers"] = list(corpus_snapshot.payload.get("papers", []))
            self.state["web_sources"] = list(corpus_snapshot.payload.get("web_sources", []))
            self.state["indexed_paper_ids"] = list(corpus_snapshot.payload.get("indexed_paper_ids", []))
            self.state["status"] = f"Skill {skill_id} completed"
            return

        if skill_id == "extract_paper_notes":
            new_analyses = [dict(artifact.payload) for artifact in output_artifacts if artifact.artifact_type == "PaperNote"]
            existing_analyses = list(self.state.get("analyses", []))
            existing_findings = list(self.state.get("findings", []))
            new_findings: list[str] = []
            for analysis in new_analyses:
                prefix = "Web" if str(analysis.get("source_type", "")).lower() == "web" else "Paper"
                title = str(analysis.get("title", "Unknown"))
                for finding in analysis.get("key_findings", []):
                    new_findings.append(f"[{prefix}: {title}] {finding}")
            self.state["analyses"] = existing_analyses + new_analyses
            self.state["findings"] = existing_findings + new_findings
            self.state["status"] = f"Skill {skill_id} completed"
            return

        if skill_id == "build_related_work_matrix":
            related_work = _latest_artifact(output_artifacts, "RelatedWorkMatrix")
            gap_map = _latest_artifact(output_artifacts, "GapMap")
            search_plan = _latest_artifact(all_artifacts, "SearchPlan")
            if related_work is None or gap_map is None or search_plan is None:
                raise RuntimeError("build_related_work_matrix must produce RelatedWorkMatrix and GapMap")
            cfg = self.state.get("_cfg", {})
            source_rank_cfg = cfg.get("agent", {}).get("source_ranking", {})
            core_min_a_ratio = float(source_rank_cfg.get("core_min_a_ratio", DEFAULT_CORE_MIN_A_RATIO))
            claim_map = list(related_work.payload.get("claims", []))
            research_questions = list(search_plan.payload.get("research_questions", []))
            self.state["synthesis"] = str(related_work.payload.get("narrative", ""))
            self.state["claim_evidence_map"] = claim_map
            self.state["evidence_audit_log"] = _build_evidence_audit_log(
                research_questions=research_questions,
                claim_map=claim_map,
                core_min_a_ratio=core_min_a_ratio,
            )
            self.state["gaps"] = list(gap_map.payload.get("gaps", []))
            self.state["status"] = f"Skill {skill_id} completed"
