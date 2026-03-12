# Dynamic Research OS Technical Migration Plan
> Date: 2026-03-12
> Status: Draft v1

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

- `tool gateway`
  - provides a unified tool execution layer
  - connects to `MCP` and approved execution backends

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

> Full specification: [`docs/phase0-contracts.en.md`](phase0-contracts.en.md)

Completed items:

- `RoutePlan` contract — Pydantic model with `PlanNode`, `PlanEdge`, DAG validation rules
- `Observation` contract — structured executor-to-planner feedback with `NodeStatus`, `ErrorType`
- `ArtifactRecord` contract — formal versioned output with `producer_role`, `producer_skill`
- `SkillSpec` contract — machine-readable manifest with `applicable_roles`, `permissions`, `timeout_sec`
- `RoleSpec` contract — role registry entry with `default_allowed_skills`, `forbidden` behaviors
- `SkillContext` / `SkillOutput` — unified skill execution interface: `async def run(ctx: SkillContext) -> SkillOutput`
- Planner LLM strategy — structured output mode, `RoutePlan` JSON Schema as response format, one retry on validation failure
- SSE event protocol — 9 event types: `plan_update`, `node_status`, `skill_invoke`, `tool_invoke`, `observation`, `replan`, `artifact_created`, `policy_block`, `run_terminate`
- `BudgetPolicy` / `PermissionPolicy` — policy contracts with blocked commands and path patterns
- Storage interfaces — `ArtifactStore`, `ObservationStore`, `PlanStore` protocols
- Directory layout — confirmed `src/dynamic_os/` namespace
- Reuse map — identified which existing modules (`plugins/`, `infra/`, `providers/`, `core/budget.py`) carry over
- Skill migration mapping — 12 old wrappers mapped to 10 new skill IDs

Key design decisions frozen in Phase 0:

1. **No monolithic state** — the old `ResearchState` TypedDict is replaced by three orthogonal stores (artifact, observation, plan)
2. **Pydantic v2 for all contracts** — runtime validation, JSON Schema export for LLM structured output
3. **Sequential node execution in v1** — DAG captures parallelism structure, but executor runs nodes sequentially for now
4. **Planner structured output** — LLM response validated through `RoutePlan.model_validate_json()`, one retry on failure, then abort

### Phase 1: Contracts + Skill Runtime Foundation

Implementation tasks:

- create `src/dynamic_os/` package structure as specified in Phase 0 layout
- implement all Pydantic contract models in `contracts/`
- implement `RoleRegistry` loading from `roles/roles.yaml`
- implement `SkillRegistry` with directory discovery (`skills/<id>/`) and `skill.yaml` validation
- implement `SkillContext` / `SkillOutput` runtime bridge
- implement in-memory `ArtifactStore`, `ObservationStore`, `PlanStore`
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
- wrap existing `BudgetGuard` inside the new `BudgetPolicy` enforcement
- implement command blacklist checking (pattern match against `blocked_commands`)
- implement protected path checking (glob match against `blocked_path_patterns`)
- implement `ToolGateway` as unified execution layer connecting to existing `plugins/llm/*`, `plugins/search/*`, `plugins/retrieval/*`
- enforce read-only config (policy engine rejects any config mutation attempt)
- write permission rejection tests (blocked commands, blocked paths, budget exhaustion)

Deliverables:

- `PolicyEngine` that blocks dangerous operations
- `ToolGateway` that wraps existing provider adapters
- passing policy tests

### Phase 3: New Planner

Implementation tasks:

- implement `Planner` class that reads from stores and produces `RoutePlan`
- implement planner prompt template (system prompt + role/skill/artifact/observation context injection)
- implement structured output call via existing LLM adapters with `RoutePlan` JSON Schema
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
| 1 | `plan_research` | `plan_research.py` | Reuse existing LLM planning logic |
| 1 | `search_papers` | `search_literature.py` | Wrap `plugins/search/` |
| 1 | `fetch_fulltext` | `parse_paper_bundle.py` | Wrap `plugins/retrieval/` |
| 1 | `extract_notes` | `extract_paper_notes.py` | Wrap `infra/indexing/` + LLM |
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

Modules retained (adapted in earlier phases):

- `src/agent/plugins/*`
- `src/agent/infra/*`
- `src/agent/providers/*`
- `src/agent/artifacts/base.py`, `registry.py` (used internally by storage)
- `src/agent/core/budget.py`, `events.py`, `secret_redaction.py`, `source_ranking.py`
- `src/agent/tracing/*`

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

