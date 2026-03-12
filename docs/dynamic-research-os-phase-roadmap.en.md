# Dynamic Research OS Phased Implementation Roadmap
> Date: 2026-03-12
> Status: Draft v1

## 1. Purpose

This document defines the implementation phases that must be followed from this point onward.

Dynamic Research OS should no longer advance as a loose collection of features. It should be implemented in fixed phases and shipped in batches.

## 2. Execution Rules

- only one primary phase may be actively in progress at a time
- a new phase must not start until the previous phase reaches its exit criteria
- every phase should result in its own batch of code commits
- every phase must include tests, not just skeleton code
- if a phase is blocked, the blocker should be documented instead of skipping to the next mainline phase

## 3. Phase Overview

| Phase | Name | Goal | Main Code Surface | Output Type |
| --- | --- | --- | --- | --- |
| Phase 0 | Contract Freeze | Freeze architecture boundaries and core schema | docs, contract drafts | completed |
| Phase 1 | Runtime Foundation | Create `src/dynamic_os/` base package, contracts, roles, storage, skill loading foundation | `contracts/` `roles/` `skills/` `storage/` | skeleton + unit tests |
| Phase 2 | Tool System and Policy | Build MCP-first tool discovery, ToolRegistry, modular ToolGateway, PolicyEngine | `tools/` `policy/` | tool layer + unit tests |
| Phase 3 | Planner | Build local DAG planning, review decisions, termination, structured output validation | `planner/` | planner core + unit tests |
| Phase 4 | Executor | Build node execution, observation, replan loop, event stream | `executor/` | executor core + integration tests |
| Phase 5 | Built-In Skills Migration | Move the first batch of built-in skills to the new interface | `skills/builtins/` | skills + tests |
| Phase 6 | API and Frontend Cutover | Switch `/api/run` and runtime UI to the new runtime | `app.py` `src/server/` `frontend/` | runnable path |
| Phase 7 | Legacy Removal and Final Cutover | Delete old mainline implementation and finish the switch | old `src/agent/` main path and tests | cleanup + verification |

## 4. Strict Scope by Phase

### Phase 0: Contract Freeze

Status: completed

Frozen decisions:

- six-role model
- `role -> skill -> tool`
- MCP-first tool model
- startup discovery
- no hot-plugging
- planner / executor separation
- reviewer inserted by planner

After Phase 0, these decisions should not drift casually.

### Phase 1: Runtime Foundation

Goal:

- create the new `src/dynamic_os/` root
- freeze contracts
- freeze role registry
- freeze skill discovery / loading / registration foundation
- freeze storage abstractions

Must include:

- `contracts/route_plan.py`
- `contracts/observation.py`
- `contracts/artifact.py`
- `contracts/skill_spec.py`
- `contracts/role_spec.py`
- `contracts/skill_io.py`
- `contracts/events.py`
- `contracts/policy.py`
- `roles/registry.py`
- `roles/roles.yaml`
- `skills/discovery.py`
- `skills/loader.py`
- `skills/registry.py`
- `storage/memory.py`

Out of scope:

- planner LLM calls
- executor main loop
- MCP execution
- frontend cutover

Exit criteria:

- all contracts are importable
- skill directory scanning works
- role allowlists are validated
- in-memory stores work
- phase tests pass

### Phase 2: Tool System and Policy

Goal:

- build an MCP-first tool system
- build ToolRegistry
- build a modular ToolGateway
- build PolicyEngine

Must include:

- `tools/discovery.py`
- `tools/registry.py`
- `tools/gateway/mcp.py`
- `tools/gateway/llm.py`
- `tools/gateway/search.py`
- `tools/gateway/retrieval.py`
- `tools/gateway/exec.py`
- `tools/gateway/filesystem.py`
- `policy/engine.py`

Out of scope:

- planner DAG generation
- executor loop
- large-scale built-in skill migration

Exit criteria:

- startup tool discovery works
- ToolRegistry exposes a normalized tool view
- ToolGateway public API is stable
- policy rejection tests pass
- no hot-plugging is clearly enforced

### Phase 3: Planner

Goal:

- build planner core
- build local DAG structured output
- build review and termination decisions

Must include:

- `planner/planner.py`
- `planner/prompts.py`
- `planner/meta_skills.py`
- planner schema validation
- planner retry-once logic

Out of scope:

- actual skill execution
- API cutover

Exit criteria:

- planner emits valid local DAGs
- planner never touches raw tools directly
- reviewer insertion remains optional
- planner tests pass

### Phase 4: Executor

Goal:

- build executor main loop
- connect `planner -> executor -> observation -> planner`
- connect event streaming

Must include:

- `executor/executor.py`
- `executor/node_runner.py`
- ready-node selection
- observation generation
- SSE event emission

Out of scope:

- large built-in skill migration
- frontend cutover

Exit criteria:

- a full loop runs with mock skills
- failures return to planner instead of hidden fallback
- event stream is complete
- executor integration tests pass

### Phase 5: Built-In Skills Migration

Goal:

- migrate the first batch of built-in skills to the new skill interface

Suggested first batch:

- `plan_research`
- `search_papers`
- `fetch_fulltext`
- `extract_notes`
- `build_evidence_map`
- `design_experiment`
- `run_experiment`
- `analyze_metrics`
- `draft_report`
- `review_artifact`

Exit criteria:

- every skill contains `skill.yaml` `skill.md` `run.py`
- every skill uses capability only through `ctx.tools`
- built-in skill tests pass
- the minimal research loop works end to end

### Phase 6: API and Frontend Cutover

Goal:

- connect `/api/run` to the new runtime
- make the runtime UI reflect actual dynamic routing

Must include:

- new runtime wiring in `app.py` or `src/server/`
- CLI entrypoint cutover
- local DAG view
- skill / tool / observation / replan timelines

Exit criteria:

- API main path enters only the new runtime
- frontend no longer implies old fixed stages
- UI can show reviewer insertion and policy blocks

### Phase 7: Legacy Removal and Final Cutover

Goal:

- delete the old main path
- remove compatibility paths
- finish the cutover

Must include:

- remove old orchestrator / router / graph
- remove old stages / wrappers / reviewers
- remove tests that import the old mainline path
- verify that the new main path no longer depends on the old execution system

Exit criteria:

- single-runtime path is real
- no old runtime main entrypoint dependencies remain
- no-legacy invariant tests pass

## 5. Default Implementation Order

From now on, implementation should proceed in this order:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7

Unless the documents are explicitly changed, do not do cross-phase mainline development.

## 6. Commit Rules per Phase

Each phase should normally include these commit categories:

- structure commits for `contracts / registry / gateway`
- runtime logic commits
- test commits
- synced docs commits

Forbidden:

- a single commit mixing multiple phase mainlines
- switching API first and filling runtime later
- changing frontend presentation before backend event contracts exist

## 7. Current Recommended Active Phase

The recommended next active phase is:

`Phase 1: Runtime Foundation`

Reason:

- the architecture boundary is already frozen
- the roadmap is now explicit
- the new runtime skeleton does not exist yet
- further high-level discussion has diminishing return

## 8. One-Sentence Rule

All further implementation should move phase by phase: runtime skeleton first, then tool layer, then planner/executor, then skills, then API/frontend, and finally legacy removal.
