# Dynamic Research OS Product Requirements Document
> Date: 2026-03-12
> Status: Draft v1

## 1. Overview

Dynamic Research OS is a planner-driven multi-agent research system.

The system keeps `planner + 6 agents`, but removes the old fixed execution pipeline. The planner dynamically decides which subset of the following six execution roles should be used for a given user request:

- `conductor`
- `researcher`
- `experimenter`
- `analyst`
- `writer`
- `reviewer`

The default execution rule is:

`role -> skill -> tool`

Where:

- `planner` performs local planning rather than one-shot full-workflow planning
- `skill` is a reusable task unit
- `tool` is the lowest-level execution unit, primarily MCP tools and approved execution backends
- tools are discovered at startup from configured MCP servers and exposed through a modular `ToolGateway`

## 2. Problem Statement

The current system already shows some signs of dynamic routing, but real execution still depends heavily on the legacy fixed-stage logic and hardcoded role behavior.

This creates several problems:

- `planner` is not yet the single true owner of workflow decisions
- roles are still partially tied to hardcoded logic rather than planner-scheduled execution units
- the system is difficult to extend with user-defined `skills`
- `review` behavior is still shaped by the legacy architecture instead of planner intent
- recovery from execution failure is not fully contract-driven

## 3. Product Goal

Build a new research runtime with the following properties:

- `planner` is the only component that decides workflow structure
- the six agents are retained as execution identities, not as hardcoded pipeline stages
- each role executes work through `skills`
- each `skill` executes low-level actions through `tools`
- users can add arbitrary new `skills` through a standard package layout
- `review` is optional and planner-inserted instead of mandatory and hardcoded

## 4. Non-Goals

The first version does not aim to:

- preserve the legacy stage graph or compatibility execution path
- keep the old hardcoded `critic gate`
- let roles directly orchestrate arbitrary tools by default
- allow runtime configuration mutation
- support unrestricted shell behavior or destructive commands

## 5. Core Product Principles

### 5.1 Planner-Led Workflow

`planner` decides:

- which roles are needed
- execution order and dependencies
- whether `reviewer` should be inserted

### 5.2 Role-Level Routing, Tool-Level Execution

- dynamic routing happens at the role layer
- real execution happens at the tool layer, through `skills`
- `planner` routes roles and skills, but does not directly schedule raw tools

### 5.3 Local Planning

`planner` only needs to plan the next short segment of work, typically `2-4` nodes, rather than planning the full run upfront.

### 5.4 Strict Contracts

The runtime must rely on explicit `DAG` and `artifact contract` definitions instead of implicit Python branching.

### 5.5 User-Extensible Skills

Users should be able to add new `skills` without modifying the core runtime, as long as the skill package follows the required structure and contract.

## 6. User Stories

- As a user, I want to provide only a research request and let the system decide which roles are needed.
- As a user, I want the system to stop early when the task is already complete, instead of mechanically running every role.
- As a user, I want `reviewer` to appear only when it is truly needed.
- As a user, I want the system to discover and use a new `skill` as long as I place it in the correct directory structure.
- As a user, I want the system to clearly show what it is doing, what it produced, and why it replanned.
- As a user, I want the system to operate under strict permissions and reject dangerous commands and arbitrary deletion.

## 7. Roles and Boundaries

| Role | Primary Responsibility | Explicitly Forbidden |
| --- | --- | --- |
| `conductor` | Decompose work, organize context, define handoff goals | Must not replace `writer` and write the final report |
| `researcher` | Search, collect, read, and structure research materials | Must not act as the final writer |
| `experimenter` | Design and execute experiment-related skills | Must not take over the general literature review flow |
| `analyst` | Analyze results, compare evidence, interpret results | Must not own global workflow decisions |
| `writer` | Produce final deliverables from existing outputs | Must not secretly redo upstream research |
| `reviewer` | Review artifacts, identify issues, provide verdicts | Must not directly rewrite artifacts |

## 8. Functional Requirements

### 8.1 Planning

- `FR-1` The system must include a dedicated `planner` that generates local role DAGs
- `FR-2` `planner` must be able to choose any subset of the six roles
- `FR-3` `planner` must be able to omit `reviewer` entirely for a run
- `FR-4` `planner` must be able to insert `reviewer` proactively instead of relying on hardcoded flow
- `FR-5` Within the maximum iteration budget, `planner` must be able to terminate early when the goal is already satisfied

### 8.2 Execution

- `FR-6` `executor` must only execute ready nodes and must not alter the plan by itself
- `FR-7` Roles must execute through `skills` by default instead of directly using low-level `tools`
- `FR-8` When execution is blocked or uncertain, `executor` must produce a structured `observation`
- `FR-9` `planner` must be able to consume `observation` data and output a revised plan

### 8.3 Skill System

- `FR-10` The system must automatically discover `skills` from `skills/<skill_id>/`
- `FR-11` Every `skill` package must include:
  - `skill.yaml`
  - `skill.md`
  - `run.py`
- `FR-12` Every `skill` must declare which roles may use it
- `FR-13` `planner` may only assign a `skill` that is allowed by that role's default allowlist
- `FR-14` Users must be able to add new `skills` without editing core runtime code

### 8.4 Tool Layer

- `FR-15` `skills` must be able to call `MCP tools` through `ToolGateway`
- `FR-16` The tool layer must be MCP-first and must discover tool capabilities from configured MCP servers at startup
- `FR-17` `ToolGateway` must be split by concern instead of becoming a single monolithic file
- `FR-18` `planner` must not directly assign or invoke raw tools; concrete tool choice happens inside `skill` execution
- `FR-19` The system must support code execution in sandboxed and explicitly approved remote environments
- `FR-20` The system may search the network and autonomously choose retrieval sources within policy limits
- `FR-21` v1 only requires startup discovery; hot-plugging or runtime reload of tools is out of scope

### 8.5 Safety and Policy

- `FR-22` The runtime must enforce a strict permission policy
- `FR-23` Dangerous commands must be blocked
- `FR-24` Arbitrary file deletion must be blocked
- `FR-25` Runtime configuration must be read-only
- `FR-26` The system must enforce a maximum iteration budget

## 9. Skill Package Format

The product-level `skill` package layout is:

```text
skills/
  arxiv_search/
    skill.yaml
    skill.md
    run.py
```

File meanings:

- `skill.yaml`
  - machine-readable specification
  - declares the `skill id`, version, applicable roles, input/output contract, allowed tools, and permission requirements
  - `allowed_tools` should reference normalized MCP-backed tool ids exposed through `ToolGateway`
- `skill.md`
  - human-readable documentation
  - explains when to use the skill, expected behavior, boundaries, and failure modes
- `run.py`
  - execution entrypoint
  - performs the task by calling allowed tools and returns structured outputs

## 10. How Planner Inserts Review

`review` is no longer a fixed stage.

Instead, review behavior should be driven by planner-usable meta-skills such as:

- `assess_review_need`
- `replan_from_observation`
- `decide_termination`

`planner` may choose to insert `reviewer` when:

- output uncertainty is high
- evidence conflicts
- a high-cost or high-risk node just completed
- a critical final deliverable is about to be produced
- execution becomes blocked or degraded

## 11. Safety Constraints

Allowed behavior:

- online search
- autonomous retrieval source choice
- reading and writing files inside approved workspaces
- sandboxed code execution
- execution on explicitly approved remote targets

Blocked behavior:

- destructive commands such as `rm -rf`
- privilege escalation commands such as `sudo`
- arbitrary file deletion
- overwriting configuration during runtime

## 12. UX and Visibility Requirements

The frontend must truthfully represent the new runtime instead of implying a fixed stage pipeline.

The runtime UI must show:

- local `DAG` view
- role node statuses
- `skill` invocation log
- `tool` invocation log
- `observation` and replan timeline
- inserted `reviewer` nodes
- `artifact` list and details
- policy rejection messages

The UI must no longer imply a fixed stage-based workflow.

## 13. Success Metrics

The first version is successful when:

- the main runtime no longer depends on the legacy fixed-stage execution path
- `planner` truly decides which roles run
- `reviewer` is no longer mandatory
- users can add `skills` through the standard package structure
- execution failures produce structured `observation` data instead of silent fallback
- the system always stays within budget and permission limits

## 14. Scope for v1

The first release must include:

- planner-driven local role DAG generation
- the six roles above
- role-based `skill allowlists`
- locally discoverable user `skills`
- startup MCP tool discovery and tool execution through a modular `ToolGateway`
- a `planner-observation-executor` replanning loop
- planner-inserted `reviewer`
- budget and permission enforcement

## 15. Explicit Product Decision

This product intentionally keeps the six-agent model.

It will not collapse into a generic single-agent `LLM + tools` runtime.

The key distinction is:

- `planner` owns workflow structure
- roles own bounded execution
- `skills` own reusable task logic
- `tools` own low-level action execution
