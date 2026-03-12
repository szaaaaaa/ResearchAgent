# Phase 0: Frozen Contracts & Interface Definitions
> Date: 2026-03-12
> Status: Frozen v1

This document defines all core contracts, interfaces, and event schemas required
before Phase 1 implementation can begin.

---

## 1. Design Decisions

### 1.1 Pydantic v2 as Contract Layer

All contracts use `pydantic.BaseModel` with strict validation. The existing
`TypedDict`-based schemas (`core/schemas.py`) are **not** reused for the new
runtime — they remain available for legacy code during transition.

Rationale:
- runtime validation with clear error messages
- JSON Schema export for frontend and planner structured-output
- immutable by default (`model_config = {"frozen": True}`)

### 1.2 State Model

The new runtime has **no monolithic `ResearchState` dict**. State is instead
composed of three orthogonal stores:

| Store | Contents | Access |
|-------|----------|--------|
| `ArtifactStore` | Formal versioned outputs | read by planner, executor, skills |
| `ObservationStore` | Execution feedback records | read by planner only |
| `PlanStore` | Historical RoutePlans | read by planner, executor |

The planner builds each new local DAG by reading from these stores plus the
original user request. Skills receive only the artifacts they declare as inputs.

### 1.3 Planner LLM Strategy

The planner calls the LLM with **structured output** (JSON mode /
function-calling), using the `RoutePlan` JSON Schema as the output schema.

The planner prompt template receives:
- user request
- current artifact summaries (type + id + producer, not full payloads)
- latest observations (if any)
- available roles and their allowed skills
- budget usage snapshot

The planner produces a `RoutePlan` object that passes Pydantic validation
before the executor accepts it.

### 1.4 Skill Execution Interface

Skills are Python callables with a fixed async signature:

```python
async def run(ctx: SkillContext) -> SkillOutput
```

Both built-in skills (registered programmatically) and user-defined skills
(discovered from `skills/<id>/run.py`) share this interface.

### 1.5 Concurrency Model

The executor processes ready nodes **sequentially** in v1. Nodes with no
dependency edges between them are executed in topological order but not in
parallel. This keeps the implementation simple while the DAG structure already
captures potential parallelism for future versions.

---

## 2. Contract: RoutePlan

The planner produces this contract. The executor consumes it.

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class FailurePolicy(str, Enum):
    replan = "replan"
    skip = "skip"
    abort = "abort"

class RoleId(str, Enum):
    conductor = "conductor"
    researcher = "researcher"
    experimenter = "experimenter"
    analyst = "analyst"
    writer = "writer"
    reviewer = "reviewer"

class PlanNode(BaseModel):
    model_config = {"frozen": True}

    node_id: str = Field(..., pattern=r"^node_[a-z0-9_]+$")
    role: RoleId
    goal: str = Field(..., min_length=1, max_length=500)
    inputs: list[str] = Field(default_factory=list,
        description="Artifact references: 'artifact:<type>:<id>'")
    allowed_skills: list[str] = Field(..., min_length=1)
    success_criteria: list[str] = Field(default_factory=list)
    failure_policy: FailurePolicy = FailurePolicy.replan
    expected_outputs: list[str] = Field(default_factory=list,
        description="Expected output artifact types")
    needs_review: bool = False

class EdgeCondition(str, Enum):
    on_success = "on_success"
    on_failure = "on_failure"
    always = "always"

class PlanEdge(BaseModel):
    model_config = {"frozen": True}

    source: str
    target: str
    condition: EdgeCondition = EdgeCondition.on_success

class RoutePlan(BaseModel):
    model_config = {"frozen": True}

    run_id: str
    planning_iteration: int = Field(..., ge=0)
    horizon: int = Field(..., ge=1, le=8)
    nodes: list[PlanNode] = Field(..., min_length=1, max_length=8)
    edges: list[PlanEdge] = Field(default_factory=list)
    planner_notes: list[str] = Field(default_factory=list)
    terminate: bool = False
```

### Validation Rules

- Every `PlanEdge.source` and `PlanEdge.target` must refer to a `node_id`
  present in `nodes`.
- The graph formed by `edges` must be a DAG (no cycles).
- `allowed_skills` for each node must be a subset of that role's allowlist
  in the role registry.
- `horizon` must equal `len(nodes)`.

---

## 3. Contract: Observation

The executor produces this contract. The planner consumes it.

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class NodeStatus(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"
    needs_replan = "needs_replan"
    skipped = "skipped"

class ErrorType(str, Enum):
    tool_failure = "tool_failure"
    skill_error = "skill_error"
    timeout = "timeout"
    policy_block = "policy_block"
    input_missing = "input_missing"
    llm_error = "llm_error"
    none = "none"

class Observation(BaseModel):
    model_config = {"frozen": True}

    node_id: str
    role: RoleId
    status: NodeStatus
    error_type: ErrorType = ErrorType.none
    what_happened: str = ""
    what_was_tried: list[str] = Field(default_factory=list)
    suggested_options: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    produced_artifacts: list[str] = Field(default_factory=list,
        description="Artifact references: 'artifact:<type>:<id>'")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    duration_ms: float = 0.0
```

---

## 4. Contract: ArtifactRecord

Formal reusable output produced by skills. Stored in `ArtifactStore`.

```python
from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Any

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ArtifactRecord(BaseModel):
    artifact_id: str
    artifact_type: str
    producer_role: RoleId
    producer_skill: str
    schema_version: str = "1.0"
    content_ref: str = Field("",
        description="Path or key to full content, e.g. 'artifacts/pn_001.json'")
    payload: dict[str, Any] = Field(default_factory=dict)
    source_inputs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)
```

### Known Artifact Types (v1)

These types carry over from the existing system with minimal renaming:

| Artifact Type | Producer Role(s) | Description |
|---------------|-------------------|-------------|
| `TopicBrief` | conductor | Decomposed topic + scope |
| `SearchPlan` | conductor | Research questions + queries + routes |
| `SourceSet` | researcher | Collected paper + web source records |
| `PaperNotes` | researcher | Extracted per-paper analysis notes |
| `EvidenceMap` | researcher, analyst | Claim-evidence mapping |
| `GapMap` | researcher, analyst | Identified research gaps |
| `ExperimentPlan` | experimenter | Designed experiment spec |
| `ExperimentResults` | experimenter | Raw experiment run results |
| `ExperimentAnalysis` | analyst | Interpreted experiment findings |
| `PerformanceMetrics` | analyst | Aggregated metrics summary |
| `ResearchReport` | writer | Final deliverable document |
| `ReviewVerdict` | reviewer | Review assessment + issues |

---

## 5. Contract: SkillSpec

Machine-readable skill manifest. Every skill package must provide this as
`skill.yaml`.

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class SkillPermissions(BaseModel):
    model_config = {"frozen": True}

    network: bool = False
    filesystem_read: bool = False
    filesystem_write: bool = False
    remote_exec: bool = False
    sandbox_exec: bool = False

class SkillInputContract(BaseModel):
    model_config = {"frozen": True}

    required: list[str] = Field(default_factory=list,
        description="Required input artifact types or parameter names")
    optional: list[str] = Field(default_factory=list)

class SkillSpec(BaseModel):
    model_config = {"frozen": True}

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    version: str = "1.0.0"
    applicable_roles: list[RoleId] = Field(..., min_length=1)
    description: str
    input_contract: SkillInputContract = Field(default_factory=SkillInputContract)
    output_artifacts: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    permissions: SkillPermissions = Field(default_factory=SkillPermissions)
    timeout_sec: int = Field(120, ge=1, le=600)
```

---

## 6. Contract: RoleSpec

Role registry entry. Replaces hardcoded role classes.

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class RoleSpec(BaseModel):
    model_config = {"frozen": True}

    id: RoleId
    description: str
    system_prompt: str
    default_allowed_skills: list[str] = Field(default_factory=list)
    input_artifact_types: list[str] = Field(default_factory=list)
    output_artifact_types: list[str] = Field(default_factory=list)
    max_retries: int = Field(2, ge=0, le=5)
    forbidden: list[str] = Field(default_factory=list,
        description="Behaviors this role must NOT perform")
```

### Default Role Registry (v1)

```yaml
- id: conductor
  description: Decompose work, organize context, define handoff goals
  default_allowed_skills:
    - plan_research
  input_artifact_types: []
  output_artifact_types: [TopicBrief, SearchPlan]
  forbidden:
    - Must not replace writer and write the final report

- id: researcher
  description: Search, collect, read, and structure research materials
  default_allowed_skills:
    - search_papers
    - fetch_fulltext
    - extract_notes
    - build_evidence_map
  input_artifact_types: [TopicBrief, SearchPlan]
  output_artifact_types: [SourceSet, PaperNotes, EvidenceMap, GapMap]
  forbidden:
    - Must not act as the final writer

- id: experimenter
  description: Design and execute experiment-related skills
  default_allowed_skills:
    - design_experiment
    - run_experiment
  input_artifact_types: [SearchPlan, EvidenceMap, GapMap]
  output_artifact_types: [ExperimentPlan, ExperimentResults]
  forbidden:
    - Must not take over the general literature review flow

- id: analyst
  description: Analyze results, compare evidence, interpret results
  default_allowed_skills:
    - analyze_metrics
    - build_evidence_map
  input_artifact_types: [SourceSet, PaperNotes, ExperimentResults]
  output_artifact_types: [ExperimentAnalysis, PerformanceMetrics, EvidenceMap]
  forbidden:
    - Must not own global workflow decisions

- id: writer
  description: Produce final deliverables from existing outputs
  default_allowed_skills:
    - draft_report
  input_artifact_types: [EvidenceMap, ExperimentAnalysis, PerformanceMetrics]
  output_artifact_types: [ResearchReport]
  forbidden:
    - Must not secretly redo upstream research

- id: reviewer
  description: Review artifacts, identify issues, provide verdicts
  default_allowed_skills:
    - review_artifact
  input_artifact_types: [SourceSet, ExperimentPlan, ResearchReport]
  output_artifact_types: [ReviewVerdict]
  forbidden:
    - Must not directly rewrite artifacts
```

---

## 7. Skill Execution Interface

### 7.1 SkillContext

The runtime constructs this and passes it to every skill invocation.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SkillContext:
    skill_id: str
    role_id: str
    run_id: str
    node_id: str
    goal: str
    input_artifacts: list[ArtifactRecord]
    config: dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = 120
```

### 7.2 SkillOutput

Every skill must return this.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class SkillOutput(BaseModel):
    success: bool
    output_artifacts: list[ArtifactRecord] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict,
        description="Optional metrics, logs, diagnostics")
```

### 7.3 Execution Entrypoint

Built-in skills implement:

```python
from dynamic_os.contracts.skill import SkillContext, SkillOutput

async def run(ctx: SkillContext) -> SkillOutput:
    ...
```

User-defined skills in `skills/<id>/run.py` must expose the same signature.

### 7.4 Mapping from Existing Skills

| Old Wrapper (`skills/wrappers/`) | New Skill ID | Target Role |
|----------------------------------|-------------|-------------|
| `plan_research.py` | `plan_research` | conductor |
| `search_literature.py` | `search_papers` | researcher |
| `parse_paper_bundle.py` | `fetch_fulltext` | researcher |
| `extract_paper_notes.py` | `extract_notes` | researcher |
| `build_related_work.py` | `build_evidence_map` | researcher, analyst |
| `design_experiment.py` | `design_experiment` | experimenter |
| `execute_experiment.py` | `run_experiment` | experimenter |
| `analyze_results.py` | `analyze_metrics` | analyst |
| `generate_report.py` | `draft_report` | writer |
| `critique_retrieval.py` | `review_artifact` | reviewer |
| `critique_claims.py` | `review_artifact` | reviewer |
| `critique_experiment.py` | `review_artifact` | reviewer |

---

## 8. Planner Prompt Contract

### 8.1 System Prompt Template

```text
You are the planner for a research operating system with six execution roles.

Your job: given a user request and current execution state, produce a local
execution DAG of 2-4 nodes. You do NOT plan the full run — only the next
meaningful segment.

## Available Roles
{role_registry_summary}

## Available Skills per Role
{skill_allowlist_summary}

## Current State
- Artifacts produced so far: {artifact_summary}
- Latest observations: {observation_summary}
- Budget usage: {budget_snapshot}
- Planning iteration: {iteration}

## Rules
1. Select the smallest set of roles needed for the next step.
2. Each node must specify allowed_skills from that role's allowlist.
3. Set needs_review=true only when output uncertainty is high, evidence
   conflicts, or a critical deliverable is about to be produced.
4. Set terminate=true when the user goal is fully satisfied.
5. Output valid JSON matching the RoutePlan schema.
```

### 8.2 Structured Output

The planner call uses the LLM provider's structured output / function-calling
mode with the `RoutePlan` JSON Schema as the response format. The raw LLM
response is validated through `RoutePlan.model_validate_json()` before use.

If validation fails, the planner retries once with the validation error
appended to the prompt. If the second attempt also fails, the planner emits
an Observation with `error_type=llm_error` and the system terminates the run.

---

## 9. Event Protocol (SSE)

All events are JSON objects sent over the existing SSE stream. Each event
has a `type` field for frontend dispatch.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class BaseEvent(BaseModel):
    ts: str
    run_id: str
    type: str

class PlanUpdateEvent(BaseEvent):
    type: str = "plan_update"
    planning_iteration: int
    plan: dict[str, Any]  # serialized RoutePlan

class NodeStatusEvent(BaseEvent):
    type: str = "node_status"
    node_id: str
    role: str
    status: str  # pending | running | success | failed | skipped

class SkillInvokeEvent(BaseEvent):
    type: str = "skill_invoke"
    node_id: str
    skill_id: str
    phase: str  # start | end | error

class ToolInvokeEvent(BaseEvent):
    type: str = "tool_invoke"
    node_id: str
    skill_id: str
    tool_id: str
    phase: str  # start | end | error

class ObservationEvent(BaseEvent):
    type: str = "observation"
    observation: dict[str, Any]  # serialized Observation

class ReplanEvent(BaseEvent):
    type: str = "replan"
    reason: str
    previous_iteration: int
    new_iteration: int

class ArtifactEvent(BaseEvent):
    type: str = "artifact_created"
    artifact_id: str
    artifact_type: str
    producer_role: str
    producer_skill: str

class PolicyBlockEvent(BaseEvent):
    type: str = "policy_block"
    blocked_action: str
    reason: str

class RunTerminateEvent(BaseEvent):
    type: str = "run_terminate"
    reason: str
    final_artifacts: list[str]
```

---

## 10. Policy Contract

### 10.1 BudgetPolicy

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class BudgetPolicy(BaseModel):
    max_planning_iterations: int = Field(10, ge=1)
    max_node_executions: int = Field(30, ge=1)
    max_tool_invocations: int = Field(200, ge=1)
    max_wall_time_sec: float = Field(600.0, ge=30.0)
    max_tokens: int = Field(500_000, ge=10_000)
```

### 10.2 PermissionPolicy

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class PermissionPolicy(BaseModel):
    allow_network: bool = True
    allow_filesystem_read: bool = True
    allow_filesystem_write: bool = True
    allow_sandbox_exec: bool = True
    allow_remote_exec: bool = False
    approved_workspaces: list[str] = Field(default_factory=list)
    blocked_commands: list[str] = Field(
        default_factory=lambda: [
            "rm -rf", "sudo", "su", "mkfs",
            "Remove-Item -Recurse -Force",
            "git reset --hard", "git checkout .",
        ]
    )
    blocked_path_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/.env", "**/credentials*", "**/secrets*",
        ]
    )
```

---

## 11. Storage Interfaces

### 11.1 ArtifactStore

```python
from __future__ import annotations
from typing import Protocol

class ArtifactStore(Protocol):
    def save(self, record: ArtifactRecord) -> None: ...
    def get(self, artifact_id: str) -> ArtifactRecord | None: ...
    def list_by_type(self, artifact_type: str) -> list[ArtifactRecord]: ...
    def list_all(self) -> list[ArtifactRecord]: ...
    def summary(self) -> list[dict[str, str]]:
        """Return [{artifact_id, artifact_type, producer_role}] for planner context."""
        ...
```

### 11.2 ObservationStore

```python
from __future__ import annotations
from typing import Protocol

class ObservationStore(Protocol):
    def save(self, obs: Observation) -> None: ...
    def list_latest(self, n: int = 5) -> list[Observation]: ...
    def list_by_node(self, node_id: str) -> list[Observation]: ...
```

### 11.3 PlanStore

```python
from __future__ import annotations
from typing import Protocol

class PlanStore(Protocol):
    def save(self, plan: RoutePlan) -> None: ...
    def get_latest(self) -> RoutePlan | None: ...
    def list_all(self) -> list[RoutePlan]: ...
```

---

## 12. Target Directory Layout (confirmed)

```
src/
  dynamic_os/
    __init__.py
    contracts/
      __init__.py
      route_plan.py      # RoutePlan, PlanNode, PlanEdge
      observation.py      # Observation, NodeStatus, ErrorType
      artifact.py         # ArtifactRecord
      skill_spec.py       # SkillSpec, SkillPermissions, SkillInputContract
      role_spec.py        # RoleSpec
      skill_io.py         # SkillContext, SkillOutput
      events.py           # all SSE event models
      policy.py           # BudgetPolicy, PermissionPolicy
    planner/
      __init__.py
      planner.py          # Planner class
      prompts.py          # planner prompt templates
      meta_skills.py      # build_local_dag, assess_review_need, etc.
    executor/
      __init__.py
      executor.py         # Executor class
      node_runner.py      # single-node execution logic
    roles/
      __init__.py
      registry.py         # RoleRegistry, loads role specs
      roles.yaml          # default role definitions
    skills/
      __init__.py
      registry.py         # SkillRegistry, discovery + validation
      builtins/           # built-in skill packages
        plan_research/
        search_papers/
        fetch_fulltext/
        extract_notes/
        build_evidence_map/
        design_experiment/
        run_experiment/
        analyze_metrics/
        draft_report/
        review_artifact/
    tools/
      __init__.py
      gateway.py          # ToolGateway, unified tool execution
    policy/
      __init__.py
      engine.py           # PolicyEngine, budget + permission checks
    storage/
      __init__.py
      memory.py           # In-memory implementations of all stores
      # future: persistent backends
skills/                   # user-defined skills (project root)
```

---

## 13. Reuse Map

Existing modules that will be reused (adapted, not rewritten):

| Existing Module | Reuse Target |
|-----------------|-------------|
| `plugins/llm/*` | `tools/gateway.py` LLM tool calls |
| `plugins/search/*` | `skills/builtins/search_papers/` |
| `plugins/retrieval/*` | `skills/builtins/fetch_fulltext/` |
| `providers/*` | `tools/gateway.py` provider adapters |
| `infra/search/*` | `skills/builtins/search_papers/` |
| `infra/retrieval/*` | `skills/builtins/fetch_fulltext/` |
| `infra/indexing/*` | `skills/builtins/extract_notes/` |
| `core/budget.py` | `policy/engine.py` (wrap existing `BudgetGuard`) |
| `core/events.py` | `contracts/events.py` (new event types, same emit pattern) |
| `artifacts/base.py` | `contracts/artifact.py` (migrate to Pydantic) |
| `core/secret_redaction.py` | reuse directly |
| `core/source_ranking.py` | reuse directly in search skills |

---

## 14. Phase 0 Checklist

- [x] RoutePlan contract defined
- [x] Observation contract defined
- [x] ArtifactRecord contract defined
- [x] SkillSpec contract defined
- [x] RoleSpec contract defined
- [x] SkillContext / SkillOutput interface defined
- [x] Planner prompt template and LLM strategy defined
- [x] SSE event protocol defined
- [x] BudgetPolicy / PermissionPolicy defined
- [x] Storage interfaces defined
- [x] Directory layout confirmed
- [x] Existing module reuse map completed
- [x] Skill migration mapping completed
