# Dynamic Research OS Technical Migration Plan
> Date: 2026-03-12
> Status: Draft v1
> Phased implementation roadmap: [`docs/dynamic-research-os-phase-roadmap.en.md`](dynamic-research-os-phase-roadmap.en.md)

## 1. Objective

Replace the legacy fixed-stage execution path with a new planner-led runtime.

This migration is a true cutover, not a compatibility wrapper. The target system keeps `planner + 6 roles`, but removes the old hardcoded workflow logic and replaces it with:

- local role `DAG` planning
- role execution through `skills`
- `skill` execution through `tools`
- planner-driven `reviewer` insertion
- observation-driven replanning

## 2. Hard Constraints

The new runtime must satisfy all of the following:

- keep the following 6 execution roles:
  - `conductor`
  - `researcher`
  - `experimenter`
  - `analyst`
  - `writer`
  - `reviewer`
- route dynamically at the role level
- execute at the tool level
- use local planning rather than full-run planning
- keep `planner` and `executor` separated
- retain only two permanent runtime constraint families:
  - budget limits
  - permission limits
- do not allow runtime config overwrite
- do not allow dangerous commands or arbitrary file deletion

## 3. Legacy Removal Policy

The migration target must not depend on the old primary execution path.

Once the new runtime is stable, the following legacy logic must be deleted rather than kept behind compatibility switches:

- old graph entrypoint
- old stage-based orchestration
- old hardcoded role execution branches
- old mandatory critic path
- old stage wrapper execution path

Modules scheduled for deletion after cutover:

- [`src/agent/graph.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/graph.py)
- [`src/agent/runtime/orchestrator.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/runtime/orchestrator.py)
- [`src/agent/runtime/router.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/runtime/router.py)
- old `src/agent/stages/*`
- old `src/agent/skills/wrappers/*`
- old hardcoded execution logic under `src/agent/roles/*`

Lower-level capabilities that may be reused after adaptation:

- retrieval backends
- ingest backends
- provider adapters
- common IO helpers

### 3.1 Rewrite Boundary

The runtime architecture itself must be rewritten. The following layers are not
eligible for reuse from the legacy system:

- planner / executor control flow
- role routing and role execution logic
- skill discovery, registration, and invocation flow
- tool discovery, tool registry, and tool gateway structure
- runtime contracts, event schema, and policy enforcement
- bootstrap, import-side-effect registration, and old provider gateway paths

Selective reuse is only allowed for leaf-level implementations, and only under
strict conditions:

- reused code must be moved behind new modules under `src/dynamic_os/`
- planner, executor, roles, and skills must not import legacy modules directly
- old registries, bootstrapping, and compatibility entrypoints must not survive
- reused leaf code is an internal implementation detail, not an architectural dependency
- MCP-first discovery and the new runtime contracts remain the public model

## 4. Target Architecture

### 4.1 Component Overview

The new runtime should live under a new namespace, for example:

```text
src/
  dynamic_os/
    planner/
    executor/
    contracts/
    policy/
    roles/
    skills/
    tools/
    storage/
```

### 4.2 Core Components

- `planner`
  - reads the user request, state snapshot, artifacts, and observations
  - produces local `DAG`s
  - decides whether to insert `reviewer`
  - decides whether to terminate

- `executor`
  - executes ready nodes from the planner `DAG`
  - never mutates the `DAG` by itself
  - produces artifacts and observations

- `role registry`
  - stores the six role definitions
  - defines the default allowed `skills` for each role
  - replaces old hardcoded role classes with role specifications

- `skill registry`
  - discovers built-in and user-defined `skills`
  - validates `skill.yaml`
  - loads `run.py`
  - checks role compatibility

- `tool registry`
  - discovers MCP tool capabilities from configured servers at startup
  - stores normalized tool metadata for runtime use
  - exposes available tool capabilities to the runtime capability view

- `tool gateway`
  - provides a unified tool execution layer
  - is split across multiple modules instead of becoming a single monolithic file
  - connects to MCP-first tool capabilities and approved execution backends

- `policy engine`
  - enforces budget and permission policies
  - blocks dangerous commands and protected path writes

- `artifact store`
  - persists formal outputs for downstream use

- `observation store`
  - persists execution blocks, risks, uncertainty, and replanning context

## 5. Role Model

The six roles stay, but they should no longer be implemented as six fully separate hardcoded workflow branches.

Instead, each role should become a runtime specification containing:

- `role id`
- role prompt/profile
- default allowed `skills`
- expected input artifact types
- expected output artifact types

Conceptual role spec example:

```yaml
id: researcher
description: Search, collect, read, and structure research materials
default_allowed_skills:
  - search_papers
  - fetch_fulltext
  - extract_notes
  - build_evidence_map
input_artifacts:
  - TopicBrief
  - SearchQuerySet
output_artifacts:
  - SourceSet
  - PaperNotes
```

## 6. Planning Model

### 6.1 Local Planning

`planner` should only generate a local `DAG`, typically `2-4` nodes.

Reasons:

- cheaper
- more stable
- better for quick replanning under execution uncertainty
- better aligned with observation-driven loops

### 6.2 Planner Responsibilities

`planner` is responsible for:

- selecting roles
- selecting execution order and dependencies
- choosing allowed `skills` for a node from that role's allowlist
- routing through skills rather than directly selecting raw tools
- deciding whether to insert `reviewer`
- deciding whether to terminate
- replanning based on `observation`

`planner` must not:

- directly execute low-level tools as the main runtime path
- mutate configuration
- bypass permission policy

## 7. Execution Model

The runtime default execution rule is:

`planner -> executor -> role node -> skill -> tool`

`planner` selects role nodes and allowed skills. Concrete tool choice happens inside `skill` execution through `ToolGateway`.

### 7.1 Executor Responsibilities

- receive a `DAG` from `planner`
- identify ready nodes
- execute nodes through generic role execution logic
- collect artifacts
- collect observations
- return control to `planner` when replanning is required

### 7.2 Failure Handling

`executor` must not silently invent a hidden recovery path.

When execution is blocked, it must:

- record what happened
- record what has already been tried
- provide candidate recovery options
- recommend one action
- return control to `planner`

## 8. Core Contracts

### 8.1 RoutePlan Contract

Local `DAG contract` produced by `planner`:

```json
{
  "run_id": "run_123",
  "planning_iteration": 2,
  "horizon": 3,
  "nodes": [
    {
      "node_id": "node_research_1",
      "role": "researcher",
      "goal": "Collect and extract notes from high-signal papers about retrieval planning.",
      "inputs": ["artifact:TopicBrief:tb_1"],
      "allowed_skills": ["search_papers", "fetch_fulltext", "extract_notes"],
      "success_criteria": ["at_least_5_relevant_sources", "at_least_5_note_records"],
      "failure_policy": "replan",
      "expected_outputs": ["SourceSet", "PaperNotes"],
      "needs_review": false
    }
  ],
  "edges": [
    {
      "source": "node_research_1",
      "target": "node_analysis_1",
      "condition": "on_success"
    }
  ],
  "planner_notes": [
    "Do not insert reviewer yet; first confirm retrieval quality."
  ]
}
```

### 8.2 Observation Contract

Structured report from `executor` back to `planner`:

```json
{
  "node_id": "node_research_1",
  "role": "researcher",
  "status": "needs_replan",
  "error_type": "tool_failure",
  "what_happened": "The primary scholarly source repeatedly returned rate limits.",
  "what_was_tried": ["retry_once", "fallback_source_attempt"],
  "suggested_options": ["switch_source", "narrow_query", "insert_reviewer"],
  "recommended_action": "switch_source",
  "produced_artifacts": ["artifact:SourceSet:ss_1"],
  "confidence": 0.62
}
```

### 8.3 Artifact Contract

Formal reusable output:

```json
{
  "artifact_id": "pn_001",
  "type": "PaperNotes",
  "producer_role": "researcher",
  "producer_skill": "extract_notes",
  "schema_version": "1.0",
  "content_ref": "artifacts/pn_001.json",
  "metadata": {
    "paper_count": 6
  }
}
```

### 8.4 SkillSpec Contract

Machine-readable `skill manifest`:

```yaml
id: arxiv_search
name: Arxiv Search
version: 1.0.0
applicable_roles:
  - researcher
description: Search arXiv and return normalized paper candidates
input_contract:
  required:
    - query
output_artifacts:
  - SourceSet
allowed_tools:
  - mcp.search.arxiv
permissions:
  network: true
  filesystem_read: false
  filesystem_write: false
  remote_exec: false
timeout_sec: 60
```

## 9. Skill Package Standard

The runtime must discover `skills` from the following structure:

```text
skills/
  <skill_id>/
    skill.yaml
    skill.md
    run.py
```

### 9.1 Required Files

- `skill.yaml`
  - canonical manifest
- `skill.md`
  - planner- and developer-readable documentation
- `run.py`
  - execution entrypoint

### 9.2 Required Fields

`skill.yaml` must contain at least:

- `id`
- `name`
- `version`
- `applicable_roles`
- `description`
- `input_contract`
- `output_artifacts`
- `allowed_tools`
- `permissions`
- `timeout_sec`

### 9.3 User-Defined Skill Rules

- user-added `skills` must declare `applicable_roles`
- `planner` may choose a `skill` only if:
  - the `skill` loads successfully
  - the `skill` belongs to that role's allowed range
  - the `skill` passes permission policy checks

## 10. Planner Meta-Skills

`reviewer` insertion must not be hardcoded as a runtime rule.

Therefore, `planner` should be given a set of planner-specific meta-skills such as:

- `build_local_dag`
- `replan_from_observation`
- `assess_review_need`
- `decide_termination`

This keeps review logic owned by `planner` instead of falling back to hardcoded flow rules.

## 11. Policy Engine

Only two long-term runtime policy families are retained:

- budget policy
- permission policy

### 11.1 Budget Policy

At minimum, it should include:

- maximum planning/execution iteration count
- maximum tool invocation count
- optional maximum wall-clock duration
- optional maximum model budget

### 11.2 Permission Policy

At minimum, it should include:

- allow online search
- allow autonomous retrieval source choice within policy limits
- allow file reads and writes only inside approved workspaces
- allow sandbox execution
- allow access only to explicitly approved remote execution targets
- reject dangerous commands
- reject arbitrary deletion behavior
- reject config overwrite

Examples of blocked commands:

- `rm -rf`
- `sudo`
- `su`
- destructive PowerShell deletion equivalents
- destructive `git reset / checkout` patterns without explicit approval

## 12. API and Frontend Migration

### 12.1 API

`/api/run` may keep the same outer route, but the internal implementation must switch to the new runtime.

The run stream should expose:

- route plan updates
- node status changes
- `skill` invocation events
- `tool` invocation events
- replanning events
- `observation` events
- `artifact` creation events

### 12.2 Frontend

The frontend must stop rendering the old fixed stage graph.

It should instead display:

- local `DAG`
- role node statuses
- inserted `reviewer` nodes
- `skill` timeline
- `tool` timeline
- `observation` timeline
- `artifact` panel

## 13. Suggested Directory Layout

```text
docs/
skills/
  <user_skill>/
src/
  dynamic_os/
    planner/
    executor/
    contracts/
    policy/
    roles/
    skills/
    tools/
    storage/
frontend/
```

## 14. Migration Phases

### Phase 0: Freeze Contracts (COMPLETED)

#### P0.1 Design Decisions

**Pydantic v2 as Contract Layer**

All contracts use `pydantic.BaseModel` with strict validation. The existing
`TypedDict`-based schemas (`core/schemas.py`) are **not** reused for the new
runtime — they remain available for legacy code during transition.

Rationale:
- runtime validation with clear error messages
- JSON Schema export for frontend and planner structured-output
- immutable by default (`model_config = {"frozen": True}`)

**State Model**

The new runtime has **no monolithic `ResearchState` dict**. State is instead
composed of three orthogonal stores:

| Store | Contents | Access |
|-------|----------|--------|
| `ArtifactStore` | Formal versioned outputs | read by planner, executor, skills |
| `ObservationStore` | Execution feedback records | read by planner only |
| `PlanStore` | Historical RoutePlans | read by planner, executor |

The planner builds each new local DAG by reading from these stores plus the
original user request. Skills receive only the artifacts they declare as inputs.

**Planner LLM Strategy**

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

**Skill Execution Interface**

Skills are Python callables with a fixed async signature:

```python
async def run(ctx: SkillContext) -> SkillOutput
```

Both built-in skills (registered programmatically) and user-defined skills
(discovered from `skills/<id>/run.py`) share this interface.

**Concurrency Model**

The executor processes ready nodes **sequentially** in v1. Nodes with no
dependency edges between them are executed in topological order but not in
parallel. This keeps the implementation simple while the DAG structure already
captures potential parallelism for future versions.

**Tool Extensibility Model**

Tools are discovered from configured MCP servers at process startup. The runtime
builds a `ToolRegistry` from discovered MCP capabilities and exposes them
through a modular `ToolGateway`.

v1 does **not** support hot-plugging or runtime tool reload. Adding or removing
tools requires a restart or explicit reload step.

#### P0.2 Contract: RoutePlan

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

Validation rules:

- Every `PlanEdge.source` and `PlanEdge.target` must refer to a `node_id`
  present in `nodes`.
- The graph formed by `edges` must be a DAG (no cycles).
- `allowed_skills` for each node must be a subset of that role's allowlist
  in the role registry.
- `horizon` must equal `len(nodes)`.

#### P0.3 Contract: Observation

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

#### P0.4 Contract: ArtifactRecord

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

Known artifact types (v1):

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

#### P0.5 Contract: SkillSpec

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

#### P0.6 Contract: RoleSpec

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

Default role registry (v1):

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

#### P0.7 Skill Execution Interface

**SkillContext** — the runtime constructs this and passes it to every skill invocation:

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
    tools: ToolGateway
    config: dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = 120
```

**SkillOutput** — every skill must return this:

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

**Execution entrypoint** — built-in and user-defined skills both implement:

```python
from dynamic_os.contracts.skill_io import SkillContext, SkillOutput

async def run(ctx: SkillContext) -> SkillOutput:
    ...
```

**Mapping from existing skills:**

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

#### P0.8 Planner Prompt Contract

System prompt template:

```text
You are the planner for a research operating system with six execution roles.

Your job: given a user request and current execution state, produce a small
local execution DAG, typically 2-4 nodes. You do NOT plan the full run - only the next
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

Structured output strategy:

The planner call uses the LLM provider's structured output / function-calling
mode with the `RoutePlan` JSON Schema as the response format. The raw LLM
response is validated through `RoutePlan.model_validate_json()` before use.

If validation fails, the planner retries once with the validation error
appended to the prompt. If the second attempt also fails, the planner emits
an Observation with `error_type=llm_error` and the system terminates the run.

#### P0.9 Event Protocol (SSE)

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

#### P0.10 Policy Contract

**BudgetPolicy:**

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

**PermissionPolicy:**

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

#### P0.11 Storage Interfaces

**ArtifactStore:**

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

**ObservationStore:**

```python
from __future__ import annotations
from typing import Protocol

class ObservationStore(Protocol):
    def save(self, obs: Observation) -> None: ...
    def list_latest(self, n: int = 5) -> list[Observation]: ...
    def list_by_node(self, node_id: str) -> list[Observation]: ...
```

**PlanStore:**

```python
from __future__ import annotations
from typing import Protocol

class PlanStore(Protocol):
    def save(self, plan: RoutePlan) -> None: ...
    def get_latest(self) -> RoutePlan | None: ...
    def list_all(self) -> list[RoutePlan]: ...
```

#### P0.12 Target Directory Layout (confirmed)

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
      registry.py         # ToolRegistry, discovered MCP tool metadata
      discovery.py        # startup MCP discovery
      gateway/
        __init__.py
        mcp.py            # MCP-backed tool calls
        llm.py            # LLM-facing tool facade
        search.py         # search tool facade
        retrieval.py      # retrieval and indexing facade
        exec.py           # sandbox and remote execution facade
        filesystem.py     # filesystem facade
    policy/
      __init__.py
      engine.py           # PolicyEngine, budget + permission checks
    storage/
      __init__.py
      memory.py           # In-memory implementations of all stores
      # future: persistent backends
skills/                   # user-defined skills (project root)
```

#### P0.13 ToolGateway Public API

`ToolGateway` is the **only** way skills access external capabilities. Both
built-in and user-defined skills use the same API. No skill may directly
import legacy modules.

Tool discovery is MCP-first. The runtime discovers tools from configured MCP
servers at startup, normalizes them into a `ToolRegistry`, and then exposes
them through the gateway. Tools never call skills back.

```python
from __future__ import annotations
from typing import Any

class ToolGateway:
    """Unified tool execution layer for all skills."""

    async def llm_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...

    async def search(
        self,
        query: str,
        *,
        source: str = "auto",
        max_results: int = 10,
    ) -> list[dict[str, Any]]: ...

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    async def index(
        self,
        documents: list[dict[str, Any]],
        *,
        collection: str = "default",
    ) -> None: ...

    async def execute_code(
        self,
        code: str,
        *,
        language: str = "python",
        timeout_sec: int = 60,
    ) -> dict[str, Any]: ...

    async def read_file(self, path: str) -> str: ...

    async def write_file(self, path: str, content: str) -> None: ...
```

All built-in skills must call `ctx.tools.*` instead of importing internal
modules. This ensures user-defined skills have identical capabilities.

#### P0.14 Clean-Break Principle

This migration is a **true cutover**. The runtime architecture is rebuilt under
`src/dynamic_os/`, and no module from `src/agent/` may remain in the new
planner / executor / role / skill / tool control flow.

Leaf-level implementations may be selectively ported or wrapped during
migration, but only as internal details behind the new modules:

| Capability | Old Module (to be deleted) | New Implementation |
|-----------|---------------------------|-------------------|
| LLM chat | `plugins/llm/*`, `providers/*` | `dynamic_os/tools/gateway/llm.py` |
| Web/academic search | `plugins/search/*`, `infra/search/*` | `dynamic_os/tools/gateway/search.py` |
| Document retrieval | `plugins/retrieval/*`, `infra/retrieval/*` | `dynamic_os/tools/gateway/retrieval.py` |
| Document indexing | `infra/indexing/*` | `dynamic_os/tools/gateway/retrieval.py` |
| Budget tracking | `core/budget.py` | `dynamic_os/policy/engine.py` |
| Event emission | `core/events.py` | `dynamic_os/contracts/events.py` |
| Artifact storage | `artifacts/*` | `dynamic_os/storage/memory.py` |
| Role definitions | `roles/*` | `dynamic_os/roles/registry.py` |
| Skill registry | `skills/*` | `dynamic_os/skills/registry.py` |
| Secret redaction | `core/secret_redaction.py` | `dynamic_os/policy/redaction.py` |

### Phase 1: Contracts + Skill Runtime Foundation

Implementation tasks:

- create `src/dynamic_os/` package structure as specified in Phase 0 layout
- implement all Pydantic contract models in `contracts/`
- implement `RoleRegistry` loading from `roles/roles.yaml`
- implement `SkillRegistry` with directory discovery (`skills/<id>/`) and `skill.yaml` validation
- implement `SkillContext` / `SkillOutput` runtime bridge
- implement in-memory `ArtifactStore`, `ObservationStore`, `PlanStore`
- support startup-only discovery for skills in v1; no hot-plugging or runtime reload
- write contract validation tests (all models round-trip, invalid data rejected)
- write skill discovery tests (valid package found, invalid package rejected)
- write role allowlist tests (skill assignment outside allowlist blocked)

Deliverables:

- all contract models importable from `dynamic_os.contracts`
- a working `SkillRegistry` that discovers and validates skill packages
- a working `RoleRegistry` with 6 default roles
- in-memory storage layer
- passing unit tests for all of the above

### Phase 2: Policy Engine + Tool Gateway

Implementation tasks:

- implement `PolicyEngine` consuming `BudgetPolicy` and `PermissionPolicy`
- implement `BudgetPolicy` enforcement from scratch
- implement command blacklist checking (pattern match against `blocked_commands`)
- implement protected path checking (glob match against `blocked_path_patterns`)
- implement startup `ToolRegistry` discovery from configured MCP servers
- implement `ToolGateway` as a modular package with public API: `llm_chat`, `search`, `retrieve`, `index`, `execute_code`, `read_file`, `write_file`
- enforce read-only config (policy engine rejects any config mutation attempt)
- write permission rejection tests (blocked commands, blocked paths, budget exhaustion)

Deliverables:

- `PolicyEngine` that blocks dangerous operations
- `ToolRegistry` with discovered MCP tool capabilities
- `ToolGateway` with full public API and modular internal structure
- passing policy tests

### Phase 3: New Planner

Implementation tasks:

- implement `Planner` class that reads from stores and produces `RoutePlan`
- implement planner prompt template (system prompt + role/skill/artifact/observation context injection)
- implement structured output call with `RoutePlan` JSON Schema
- implement DAG validation (node_id references, cycle detection, allowlist enforcement)
- implement one-retry-on-validation-failure logic
- implement planner meta-skills: `assess_review_need`, `decide_termination`
- implement termination logic (planner sets `terminate=true` when goal satisfied)
- write planner output schema tests (valid plans accepted, invalid plans rejected)
- write reviewer insertion tests (planner can insert reviewer, reviewer is never mandatory)

Deliverables:

- a `Planner` that emits valid, validated local DAGs
- planner meta-skills working
- passing planner unit tests

### Phase 4: New Executor + Replan Loop

Implementation tasks:

- implement `Executor` class that receives a `RoutePlan` and executes ready nodes
- implement topological sort for node execution order
- implement single-node execution: resolve role → select skill → build `SkillContext` → call `run()` → collect `SkillOutput`
- implement `Observation` generation on success, partial, and failure
- implement replan trigger: executor returns control to planner when `failure_policy=replan`
- implement the main loop: `planner → executor → observation → planner → ...`
- implement budget checking before each node execution
- emit SSE events at each step (`plan_update`, `node_status`, `skill_invoke`, `observation`, `replan`, `artifact_created`)
- write executor-observation-replan loop tests
- write budget exhaustion termination tests

Deliverables:

- an `Executor` that runs contract-defined role nodes through skills
- a complete planner-executor loop with observation-driven replanning
- SSE event emission working
- passing integration tests

### Phase 5: Built-In Skills Migration

Migrate existing skill wrappers to the new `async def run(ctx) -> SkillOutput` interface:

| Priority | Skill ID | Source Wrapper | Notes |
|----------|---------|---------------|-------|
| 1 | `plan_research` | `plan_research.py` | Rewrite LLM planning via `ctx.tools` |
| 1 | `search_papers` | `search_literature.py` | Rewrite via `ctx.tools.search()` |
| 1 | `fetch_fulltext` | `parse_paper_bundle.py` | Rewrite via `ctx.tools.retrieve()` |
| 1 | `extract_notes` | `extract_paper_notes.py` | Rewrite via `ctx.tools.index()` + `ctx.tools.llm_chat()` |
| 2 | `build_evidence_map` | `build_related_work.py` | LLM synthesis |
| 2 | `design_experiment` | `design_experiment.py` | LLM generation |
| 2 | `run_experiment` | `execute_experiment.py` | Sandbox execution |
| 2 | `analyze_metrics` | `analyze_results.py` | LLM analysis |
| 3 | `draft_report` | `generate_report.py` | LLM writing |
| 3 | `review_artifact` | `critique_*.py` | Merge 3 critique wrappers into 1 generic reviewer |

Each migrated skill must include `skill.yaml` + `skill.md` + `run.py`.

Deliverables:

- 10 built-in skills in `dynamic_os/skills/builtins/`
- a minimal but complete research loop running on the new runtime end-to-end
- passing integration test: user request → planner → executor → artifacts → report

### Phase 6: API + Frontend Cutover

Implementation tasks:

- wire `/api/run` to the new `dynamic_os` runtime (keep same outer route)
- wire CLI entrypoint (`scripts/run_agent.py`) to the new runtime
- replace old fixed route graph in frontend with local DAG visualization
- implement frontend components for:
  - local DAG view with role node statuses
  - skill invocation timeline
  - tool invocation timeline
  - observation + replan timeline
  - artifact panel
  - inserted reviewer node highlighting
  - policy rejection message display
- consume new SSE event types in frontend store

Deliverables:

- `/api/run` and CLI both enter only the new runtime
- frontend truthfully reflects dynamic runtime behavior
- no frontend reference to old fixed-stage pipeline

### Phase 7: Legacy Removal

Remove the following modules and their tests:

- `src/agent/graph.py`
- `src/agent/nodes.py`
- `src/agent/state.py`
- `src/agent/runtime/orchestrator.py`
- `src/agent/runtime/router.py`
- `src/agent/runtime/context.py` (replaced by `SkillContext`)
- `src/agent/runtime/policy.py` (replaced by `PolicyEngine`)
- `src/agent/stages/*`
- `src/agent/skills/wrappers/*`
- `src/agent/skills/base.py`, `contract.py`, `registry.py` (replaced by `dynamic_os/contracts/` and `dynamic_os/skills/registry.py`)
- `src/agent/roles/*` (replaced by `dynamic_os/roles/`)
- `src/agent/reviewers/*` (replaced by `review_artifact` skill)
- old tests: `test_app_model_catalogs.py`, `test_app_run_control.py`, and any test importing deleted modules

All modules under `src/agent/` are deleted. The entire old package tree is removed:

- `src/agent/` (complete removal)

The new runtime at `src/dynamic_os/` is fully self-contained with zero imports
from the old codebase.

Deliverables:

- a single-runtime codebase with no legacy execution paths
- all tests pass without importing deleted modules
- `git log` confirms clean removal

## 15. Testing Strategy

### Test Layers

| Layer | Scope | Phase |
|-------|-------|-------|
| Contract validation | All Pydantic models round-trip, invalid data rejected | 1 |
| Skill discovery | Valid packages found, invalid rejected, allowlist enforced | 1 |
| Policy rejection | Blocked commands, blocked paths, budget exhaustion | 2 |
| Planner output schema | Valid plans accepted, invalid rejected, DAG validation | 3 |
| Executor-observation-replan loop | Full loop with mock skills | 4 |
| Skill unit tests | Each built-in skill produces correct `SkillOutput` | 5 |
| End-to-end integration | User request → artifacts → report on new runtime | 5 |
| Frontend SSE | Events rendered correctly in UI | 6 |
| No-legacy invariant | New runtime never imports old `stages`, `graph`, or `orchestrator` | 7 |

### Critical Invariant Tests

- `planner` cannot assign a `skill` outside a role's allowlist
- `executor` cannot execute blocked commands
- runtime cannot overwrite configuration
- `reviewer` is optional and planner-inserted
- failed execution must return `Observation` instead of silent fallback
- the new main execution path must not import or call old `stages`, `graph`, or `orchestrator`
- planner LLM validation failure after retry must abort the run (not silently continue)
- budget exhaustion must terminate the run with `RunTerminateEvent`

## 16. Cutover Criteria

The new runtime should only be considered complete when:

- the main `/api/run` path enters only the new runtime
- the main CLI path enters only the new runtime
- the old orchestration path is deleted
- the codebase no longer depends on old workflow abstractions
- all contract models pass validation tests
- a full research loop completes end-to-end on the new runtime

## 17. Explicit Technical Decision

This migration does not target a generic single-agent `LLM + tools` runtime.

Its target is:

- one `planner`
- six bounded execution roles
- a reusable `skill` layer
- a `tool`-driven execution layer
- planner-owned `review` and `replan`

That is the intended replacement architecture.

## 18. Strict Implementation Appendix

This appendix consolidates the old strict implementation guide into the migration plan itself. From this point on, the migration plan serves as both architecture specification and implementation constraint document.

### 18.1 Code Organization Rules

- the new runtime main path may exist only under `src/dynamic_os/`
- the old `src/agent/` mainline must not continue to grow
- `ToolGateway` must be a unified facade with multiple internal files
- `skills` must be split into `discovery / loader / registry`
- `tools` must be split into `discovery / registry / gateway/*`

### 18.2 Module Boundaries

- `planner` owns planning, replanning, and review/termination decisions
- `executor` owns ready-node execution and `artifact` / `observation` collection
- `roles` store role specifications only and must not become six hardcoded workflows
- `skills` are the only task-level extensibility unit
- `tools` are the capability-level extensibility unit, not a second workflow system

### 18.3 Skill Rules

- every skill must include `skill.yaml`, `skill.md`, and `run.py`
- every skill must use external capability only through `ctx.tools`
- skills must not import legacy runtime entrypoints directly
- skills must not implement their own policy bypass logic
- built-in and user skills should follow the same loading model whenever possible

### 18.4 Tool Rules

- the tool layer must be `MCP-first`
- tools are discovered only at startup in v1
- hot-plugging is out of scope
- a `tool` must never call back into a `skill`
- individual skills must not each connect to MCP independently; all access goes through `ToolGateway`

### 18.5 Dependency Direction Rules

Required dependency direction:

```text
contracts <- planner
contracts <- executor
contracts <- roles
contracts <- skills
contracts <- tools

tools <- skills
skills <- executor
roles <- executor
planner <-> storage
executor <-> storage
policy <- planner/executor/tools
```

Forbidden:

- `planner -> raw tools`
- `tool -> skill`
- `contracts -> runtime logic`
- `src/dynamic_os/* -> src/agent/runtime/*`

### 18.6 Config and Policy Rules

- configuration must be frozen into a read-only run snapshot at startup
- runtime code must not overwrite config files, `.env`, or discovery results
- budget and permission enforcement belongs only in `PolicyEngine`
- skills and tools must not bypass policy internally

### 18.7 Test and PR Gates

No phase should be considered complete without:

- contract round-trip tests
- skill discovery / manifest validation tests
- role allowlist tests
- MCP tool discovery / ToolRegistry normalization tests
- ToolGateway permission rejection tests
- planner schema tests
- executor-observation-replan loop tests
- no-legacy invariant tests

Reject PRs that:

- keep adding features to the old `src/agent/` main path
- reconnect legacy bootstrap / registry logic into the new runtime
- turn `ToolGateway` into a single file
- hardcode the skill inventory instead of loading it
- claim plug-and-play support without manifest validation
