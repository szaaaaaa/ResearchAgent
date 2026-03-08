from __future__ import annotations

from dataclasses import dataclass

from src.agent.artifacts.registry import ArtifactRegistry
from src.agent.core.budget import BudgetGuard


@dataclass
class RunContext:
    run_id: str
    topic: str
    iteration: int
    max_iterations: int
    budget: BudgetGuard
    artifact_registry: ArtifactRegistry
