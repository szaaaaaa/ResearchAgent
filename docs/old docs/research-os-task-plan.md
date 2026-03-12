# Research OS 开发任务清单

> 日期：2026-03-08

> 基线日期：2026-03-08
> 目标范围：先落 `3-agent literature review MVP`，并为 `Gemini 3 Pro / ChatGPT 5.4 / Claude` 预留统一模型接口

## 1. 目标

本任务清单只服务两个直接目标：

1. 跑通 `Conductor + Researcher + Critic` 的文献综述闭环
2. 让模型层可切换，而不影响 `skills / artifacts / runtime`

本轮明确不做：

- code generation
- experiment running
- result analysis
- full paper writing
- 完整 6-agent 落地

---

## 2. 时间表

### Phase 0

- 日期：2026-03-09 到 2026-03-10
- 目标：冻结 MVP 范围，确认接口和迁移边界

任务：

1. 固定 3-agent MVP 的输入输出边界
2. 固定第一批 artifacts
3. 固定第一批 literature skills
4. 固定 `LLMProvider` 最小接口
5. 固定迁移期间 CLI 兼容要求

交付物：

1. `3-agent MVP` 范围说明
2. `artifact` 清单
3. `skill` 清单
4. `provider interface` 草案

验收标准：

1. 能明确说清 MVP 跑到哪里结束
2. 能明确说清第一阶段不做什么

### Phase 1：Artifact 层

目标：先落 artifact 契约

任务（按文件）：

1. 新建 `src/agent/artifacts/__init__.py`
2. 新建 `src/agent/artifacts/base.py`
   - 定义 `ArtifactMeta` dataclass：`artifact_type`, `artifact_id`, `producer`, `source_inputs`, `created_at`
   - 定义 `Artifact` 基类：包含 `meta: ArtifactMeta` + `payload: Any`
3. 新建 `src/agent/artifacts/schemas.py`
   - 定义 `TopicBrief`：payload 包含 `topic: str`, `scope: dict`
   - 定义 `SearchPlan`：payload 包含 `research_questions: list`, `search_queries: list`, `query_routes: dict`
   - 定义 `CorpusSnapshot`：payload 包含 `papers: list[PaperRecord]`, `web_sources: list[WebResult]`, `indexed_paper_ids: list[str]`
   - 定义 `PaperNote`：payload 对应现有 `AnalysisResult` 字段
   - 定义 `RelatedWorkMatrix`：payload 包含 `narrative: str`, `claims: list[ClaimEvidenceEntry]`
   - 定义 `GapMap`：payload 包含 `gaps: list[str]`
   - 定义 `CritiqueReport`：payload 包含 `verdict: ReviewerVerdict`, `details: dict`
4. 新建 `src/agent/artifacts/registry.py`
   - `ArtifactRegistry` 类：`save(artifact)`, `load(artifact_id)`, `list_by_type(artifact_type)`, `get_latest(artifact_type)`
   - 落盘路径：`run_outputs/<run_id>/artifacts/<artifact_type>_<artifact_id>.json`
5. 新建 `src/agent/artifacts/serializers.py`
   - `to_json(artifact) -> str` / `from_json(json_str) -> Artifact`
6. 修改 `src/agent/stages/planning.py`
   - 在 `run_planning()` 返回值中附带 `_artifacts: [TopicBrief, SearchPlan]`
   - 不改变现有 state 字段的写入逻辑（双写）
7. 修改 `src/agent/stages/retrieval.py`
   - 在 `run_retrieval()` 返回值中附带 `_artifacts: [CorpusSnapshot]`
8. 修改 `src/agent/stages/analysis.py`
   - 在 `run_analysis()` 返回值中附带 `_artifacts: [PaperNote, ...]`
9. 修改 `src/agent/stages/synthesis.py`
   - 在 `run_synthesis()` 返回值中附带 `_artifacts: [RelatedWorkMatrix, GapMap]`
10. 修改 `src/agent/reviewers/retrieval_reviewer.py`
    - 在输出中附带 `_artifacts: [CritiqueReport]`
11. 修改 graph 节点（`graph.py` 或 `nodes.py`）
    - 节点函数在调用 stage 后，从返回值中提取 `_artifacts`，调用 `ArtifactRegistry.save()`

交付物：

1. artifact schema 初版（7 个 dataclass）
2. artifact 持久化格式（JSON 文件落盘）
3. run 输出中的 artifact sidecar

验收标准：

1. 一次 run 能在 `run_outputs/<run_id>/artifacts/` 下产出 JSON 文件
2. `ArtifactRegistry.load()` 能还原出与 state 字段一致的数据
3. 现有 graph 行为不受影响（双写不破坏原流程）

### Phase 2：Skill Runtime

目标：落 skill contract 和第一批 literature skills + graph 节点内部切换到 skill 调用

任务（按文件）：

1. 新建 `src/agent/skills/__init__.py`
2. 新建 `src/agent/skills/contract.py`
   - `SkillSpec` dataclass：`skill_id`, `purpose`, `input_artifact_types`, `output_artifact_types`, `allowed_tools`, `model_profile`, `budget_policy`
   - `SkillResult` dataclass：`success: bool`, `output_artifacts: list[Artifact]`, `error: str | None`
3. 新建 `src/agent/skills/registry.py`
   - `SkillRegistry` 类：`register(skill_id, spec, handler)`, `invoke(skill_id, input_artifacts, cfg) -> SkillResult`, `list() -> list[SkillSpec]`
4. 新建 `src/agent/skills/wrappers/plan_research.py`
   - 内部调用 `stages/planning.py` 的 `run_planning()`
   - 输入：topic string + cfg
   - 输出：`[TopicBrief, SearchPlan]`
5. 新建 `src/agent/skills/wrappers/search_literature.py`
   - 内部调用 `stages/retrieval.py` 的 `run_retrieval()`
   - 输入：`SearchPlan` artifact
   - 输出：`[CorpusSnapshot]`
6. 新建 `src/agent/skills/wrappers/parse_paper_bundle.py`
   - 内部调用 `stages/indexing.py` 的 `run_indexing()`
   - 输入：`CorpusSnapshot` artifact
   - 输出：`[CorpusSnapshot]`（含 indexed_paper_ids）
7. 新建 `src/agent/skills/wrappers/extract_paper_notes.py`
   - 内部调用 `stages/analysis.py` 的 `run_analysis()`
   - 输入：`CorpusSnapshot` artifact
   - 输出：`[PaperNote, ...]`
8. 新建 `src/agent/skills/wrappers/build_related_work.py`
   - 内部调用 `stages/synthesis.py` 的 `run_synthesis()`
   - 输入：`PaperNote[]` + `SearchPlan`
   - 输出：`[RelatedWorkMatrix, GapMap]`
9. 新建 `src/agent/skills/wrappers/critique_retrieval.py`
   - 内部调用 `reviewers/retrieval_reviewer.py` 的 `run_retrieval_review()`
   - 输入：`CorpusSnapshot`
   - 输出：`[CritiqueReport]`
10. 修改 `src/agent/plugins/bootstrap.py`
    - 在 `ensure_plugins_registered()` 中增加 skill 注册逻辑
11. 修改 `src/agent/graph.py`
    - 将 `plan_research` 节点内部从 `run_planning()` 改为 `skill_registry.invoke("plan_research")`
    - 将 `fetch_sources` 改为 `skill_registry.invoke("search_literature")`
    - 将 `index_sources` 改为 `skill_registry.invoke("parse_paper_bundle")`
    - 将 `analyze_sources` 改为 `skill_registry.invoke("extract_paper_notes")`
    - 将 `synthesize` 改为 `skill_registry.invoke("build_related_work_matrix")`
    - 将 `review_retrieval` 改为 `skill_registry.invoke("critique_retrieval")`
    - graph 拓扑和路由逻辑不变
12. 增加 skill 独立测试脚本
    - 不经过 graph，直接 `skill_registry.invoke("search_literature", [search_plan_artifact])` 能正常运行

交付物：

1. skill registry 初版
2. 10 个 skill wrapper（6 个 literature + 4 个待 Phase 5 的 stub）
3. graph 节点内部已切换为 skill 调用

验收标准：

1. 不跑 graph，也能独立调用单个 skill 并获得 artifact 输出
2. skill 输入输出全部基于 artifact
3. graph 改造后行为与改造前一致（回归测试通过）

### Phase 3：Provider 适配

目标：落统一模型接口

任务（按文件）：

1. 新建 `src/agent/providers/llm_adapter.py`
   - `ModelRequest` dataclass：`system_prompt`, `user_prompt`, `model`, `temperature`, `max_tokens`, `cfg`
   - `ModelResponse` dataclass：`content: str`, `usage: dict`, `model: str`
   - `LLMProvider` Protocol：`generate(request) -> ModelResponse`, `generate_structured(request, schema) -> T`
2. 新建 `src/agent/providers/gemini_adapter.py`
   - `GeminiProvider` 类，内部调用现有 `GeminiChatBackend.generate()`
   - `generate_structured()` 在 `generate()` 基础上加 JSON 解析（提取现有 stage 中的 `_parse_json_safe` 逻辑）
3. 新建 `src/agent/providers/openai_adapter.py`
   - `OpenAIProvider` 类，内部调用现有 `OpenAIChatBackend.generate()`
   - 结构与 `GeminiProvider` 对称
4. 修改 `src/agent/providers/llm_provider.py`
   - `call_llm()` 内部改为：查找已注册的 `LLMProvider` adapter → 调用 `adapter.generate()`
   - 保持 `call_llm()` 的外部签名不变（向后兼容）
5. 修改配置文件
   - 增加 `llm.provider` 配置项：`gemini`（默认）/ `openai` / `claude`
6. 不做的事：
   - 不实现 `ClaudeProvider`（无当前需求）
   - 不实现 `stream()` 和 `tool_call()`
   - 不修改 `plugins/llm/` 和 `infra/llm/` 的内部实现

交付物：

1. `LLMProvider` Protocol + `ModelRequest` / `ModelResponse`
2. `GeminiProvider` + `OpenAIProvider`
3. 模型切换配置项

验收标准：

1. `call_llm()` 在配置切换为 `openai` / `gemini` 时均能正常工作
2. skill wrapper 不直接 import 任何模型 SDK
3. `generate_structured()` 可替代各 stage 中的 `_parse_json_safe` 调用

### Phase 4：3-Agent 编排

目标：落 3-agent 文献综述编排

任务（按文件）：

1. 新建 `src/agent/roles/__init__.py`
2. 新建 `src/agent/roles/base.py`
   - `RolePolicy` dataclass：`role_id`, `system_prompt`, `allowed_skills: list[str]`, `max_retries`, `budget_limit_tokens`
   - `RoleAgent` 基类：`plan(context) -> list[str]`（返回要调用的 skill 序列）, `execute(skill_id, artifacts) -> list[Artifact]`
3. 新建 `src/agent/roles/conductor.py`
   - `ConductorAgent`：接收 topic，输出 `TopicBrief` + `SearchPlan`，规划 literature review 的 skill 调用顺序
4. 新建 `src/agent/roles/researcher.py`
   - `ResearcherAgent`：按 Conductor 规划的顺序，依次调用 literature skills
5. 新建 `src/agent/roles/critic.py`
   - `CriticAgent`：调用 `critique_retrieval`，返回 `pass` / `revise` / `block`
6. 新建 `src/agent/runtime/__init__.py`
7. 新建 `src/agent/runtime/orchestrator.py`
   - `ResearchOrchestrator` 类：
   - 主循环：`Conductor.plan() → Researcher.execute() → Critic.evaluate() → revise/pass`
   - revise 时：Critic 指出问题 → Conductor 决定重跑哪个 skill → Researcher 重新执行
   - 最多重试 `max_retries` 次
8. 新建 `src/agent/runtime/context.py`
   - `RunContext` dataclass：`run_id`, `topic`, `iteration`, `max_iterations`, `budget`, `artifact_registry`
9. 新建 `src/agent/runtime/policy.py`
   - 重试策略、budget guard、HITL gate
   - 从现有 `graph.py` 的路由逻辑中提取
10. 修改 CLI 入口
    - 增加 `--mode` 参数：`legacy`（默认）/ `os`
    - `--mode=os` 时创建 `ResearchOrchestrator` 并执行
    - `--mode=legacy` 时走现有 `graph.py`

交付物：

1. 3 个 role 实现（Conductor + Researcher + Critic）
2. `ResearchOrchestrator` 编排器
3. `--mode=os` CLI 入口

验收标准：

1. `--mode=os` 能完成 `topic -> search -> parse -> analyze -> synthesize -> critique` 闭环
2. Critic 返回 `revise` 时，Researcher 能重跑对应 skill
3. 最终产出 `TopicBrief` + `SearchPlan` + `CorpusSnapshot` + `PaperNote[]` + `RelatedWorkMatrix` + `GapMap` + `CritiqueReport`
4. `--mode=legacy` 仍可正常运行（不受影响）

### Phase 5：验证与回归

目标：补齐测试，确保稳定

任务：

1. artifact 单元测试
   - 每个 artifact 的序列化/反序列化
   - `ArtifactRegistry` 的 save/load/list
2. skill 单元测试
   - 每个 wrapper 的独立调用
   - 输入 artifact 类型校验
   - 输出 artifact 类型校验
3. provider 适配测试
   - `GeminiProvider.generate()` + `generate_structured()`
   - `OpenAIProvider.generate()` + `generate_structured()`
   - 模型切换配置生效
4. orchestration 集成测试
   - Conductor → Researcher → Critic 完整流程
   - revise 路径测试
   - budget 超限测试
5. CLI smoke test
   - `--mode=legacy` 端到端
   - `--mode=os` 端到端
6. 回归对比
   - 对同一 topic，`--mode=legacy` 和 `--mode=os` 产出的 artifact 质量对比
   - 记录差异，判断是否可切换默认模式

交付物：

1. MVP 测试集
2. 一次端到端演示 run
3. 问题清单和后续升级建议

验收标准：

1. 文献综述 MVP 能稳定跑通
2. Gemini 是默认模型时不影响 artifacts 和 skills

### Buffer

- 日期：2026-03-30 到 2026-03-31
- 目标：只处理阻塞缺陷，不扩 scope

任务：

1. 修复阻塞性 bug
2. 收敛文档与配置
3. 为下一阶段 `Writer / Experimenter / Analyst` 做边界确认

---

## 3. 任务分组

## A. 架构任务

1. 定义 `artifact` 契约
2. 定义 `skill` 契约
3. 定义 `LLMProvider` 契约
4. 定义 `role policy` 契约

优先级：

`最高`

## B. 能力迁移任务

1. 把 literature stages 包成 skills
2. 把 retrieval reviewer 包成 critique skill
3. 让 artifact 成为主协作接口

优先级：

`最高`

## C. 编排任务

1. 实现 `Conductor`
2. 实现 `Researcher`
3. 实现 `Critic`
4. 实现 revise/pass loop
5. 接回 CLI

优先级：

`高`

## D. 模型适配任务

1. 默认接 `GeminiProvider`
2. 预留 `OpenAIProvider`
3. 预留 `ClaudeProvider`
4. 增加模型切换配置

优先级：

`高`

## E. 验证任务

1. artifact tests
2. skill tests
3. provider tests
4. orchestration tests
5. CLI smoke test

优先级：

`高`

---

## 4. 第一批 artifacts

每个 artifact 的最小字段为 `artifact_type` / `artifact_id` / `producer` / `source_inputs` / `payload` / `created_at`。

| Artifact | 数据来源（现有 state 字段） | producer |
|---|---|---|
| `TopicBrief` | `topic` + `planning.scope` | `plan_research` skill |
| `SearchPlan` | `planning.research_questions` + `planning.search_queries` + `planning.query_routes` | `plan_research` skill |
| `CorpusSnapshot` | `research.papers[]` + `research.web_sources[]` + `research.indexed_paper_ids[]` | `search_literature` + `parse_paper_bundle` skill |
| `PaperNote` | `research.analyses[]` 中的单条 `AnalysisResult` | `extract_paper_notes` skill |
| `RelatedWorkMatrix` | `research.synthesis` + `evidence.claim_evidence_map[]` | `build_related_work_matrix` skill |
| `GapMap` | `evidence.gaps[]` | `build_related_work_matrix` skill |
| `CritiqueReport` | `review.retrieval_review` / `review.experiment_review` / `review.claim_verdicts` | `critique_*` skills |

---

## 5. 第一批 skills

严格 1:1 对应现有 stage/reviewer 实现：

| Skill ID | 包装目标 | 入口函数 | 输入 artifact | 输出 artifact |
|---|---|---|---|---|
| `plan_research` | `stages/planning.py` | `run_planning()` | (topic string) | `TopicBrief` + `SearchPlan` |
| `search_literature` | `stages/retrieval.py` | `run_retrieval()` | `SearchPlan` | `CorpusSnapshot` (papers + web) |
| `parse_paper_bundle` | `stages/indexing.py` | `run_indexing()` | `CorpusSnapshot` | `CorpusSnapshot` (indexed) |
| `extract_paper_notes` | `stages/analysis.py` | `run_analysis()` | `CorpusSnapshot` | `PaperNote[]` |
| `build_related_work_matrix` | `stages/synthesis.py` | `run_synthesis()` | `PaperNote[]` + `SearchPlan` | `RelatedWorkMatrix` + `GapMap` |
| `critique_retrieval` | `reviewers/retrieval_reviewer.py` | `run_retrieval_review()` | `CorpusSnapshot` | `CritiqueReport` |

以下 skill 在文档 catalog 中列出但第一版不实现（无现有代码支撑）：

- `dedupe_and_rank_sources`
- `normalize_metrics`
- `patch_existing_codebase`
- `prepare_run_bundle`
- `submit_experiment_run`
- `polish_paper`

---

## 6. 第一批角色

| 角色 | 允许调用的 skills | 决策权限 |
|---|---|---|
| `Conductor` | `plan_research` | 任务拆解、scope 确认、决定下一步调哪个 role |
| `Researcher` | `search_literature`, `parse_paper_bundle`, `extract_paper_notes`, `build_related_work_matrix` | 执行文献检索和综述，不做审查 |
| `Critic` | `critique_retrieval` | 审查 CorpusSnapshot 和 RelatedWorkMatrix，返回 `pass` / `revise` / `block` |

角色实现的最小契约：

```python
@dataclass
class RolePolicy:
    role_id: str
    system_prompt: str
    allowed_skills: list[str]
    max_retries: int = 2
    budget_limit_tokens: int | None = None
```

---

## 7. 默认模型策略

- 默认模型：`Gemini 3 Pro`
- 兼容目标：`ChatGPT 5.4`、`Claude`
- 切换方式：通过 `LLMProvider` 和配置项切换

当前代码现状与差距：

| 组件 | 当前状态 | 需要做的 |
|---|---|---|
| `LLMBackend` Protocol | 已有（`core/interfaces.py`），只有 `generate()` | 加 `generate_structured()` |
| `GeminiChatBackend` | 已有（`plugins/llm/gemini_chat.py`） | 包装为 `GeminiProvider` |
| `OpenAIChatBackend` | 已有（`plugins/llm/openai_chat.py`） | 包装为 `OpenAIProvider` |
| `ClaudeProvider` | 不存在 | 推迟，有需求时再加 |
| `call_llm()` | 已有（`providers/llm_provider.py`），是全局入口 | 内部改为走 `LLMProvider` adapter |
| `stream` | 底层 SDK 支持，未暴露 | 推迟到 Phase 5 |
| `tool_call` | 未抽象 | 推迟到 Phase 5 |

明确要求：

1. skill 不直接调用具体模型 SDK
2. role 不直接绑定具体模型厂商
3. artifact 不包含模型供应商特定字段

---

## 8. graph.py 过渡任务

当前 graph.py 包含 12 个 LangGraph 节点。迁移期间需要以下具体任务：

### Phase 2 中执行

1. 将 graph 节点 `plan_research` 内部从直接调 `run_planning()` 改为调 `skill_registry.invoke("plan_research")`
2. 将 `fetch_sources` 改为调 `skill_registry.invoke("search_literature")`
3. 将 `index_sources` 改为调 `skill_registry.invoke("parse_paper_bundle")`
4. 将 `analyze_sources` 改为调 `skill_registry.invoke("extract_paper_notes")`
5. 将 `synthesize` 改为调 `skill_registry.invoke("build_related_work_matrix")`
6. 将 `review_retrieval` 改为调 `skill_registry.invoke("critique_retrieval")`
7. 验证改造后 graph 行为与改造前一致（对同一 topic 产出相同 artifact）

### Phase 4 中执行

8. CLI 入口增加 `--mode` 参数：`legacy`（默认）/ `os`
9. `--mode=os` 走 `runtime/orchestrator.py`，不经过 graph.py
10. 端到端验证：两条路径对同一 topic 产出相同质量的 artifact

### MVP 验证通过后执行

11. `--mode=os` 改为默认
12. `--mode=legacy` 标记 deprecated
13. 一个版本周期后移除 graph.py legacy 入口

---

## 9. Definition Of Done

这一轮算完成的标准是：

1. 已有 `3-agent literature review MVP`
2. 默认模型为 `Gemini 3 Pro`
3. 能通过配置切换到其他 provider
4. literature review 闭环可运行
5. 产出结构化 artifact（每次 run 在 `run_outputs/<run_id>/artifacts/` 下生成 JSON 文件）
6. critique/revise 闭环存在（Critic 可返回 `revise` 触发 Researcher 重跑部分 skill）
7. CLI 入口仍可用（`--mode=legacy` 和 `--mode=os` 均可运行）
8. graph.py 节点内部已切换为通过 skill registry 调用
9. 所有 stage/reviewer 的原有逻辑未被修改，只被 skill wrapper 包装

---

## 10. 下一阶段入口

在本轮完成后，下一阶段再进入：

1. `Writer` — 基于 `RelatedWorkMatrix` + `GapMap` 产出 `ManuscriptDraft`
2. `Experimenter` — 基于 `GapMap` 产出 `ExperimentSpec` + `CodeChangeSet`
3. `Analyst` — 基于 `ExperimentResultBundle` 产出 `ResultAnalysis`
4. `generate_structured()` 扩展到支持 `stream` 和 `tool_call`
5. controlled experiment running（本地 runner + SSH runner）

前提是本轮不再扩 scope。

---

## 11. 附录：Artifact 与 ResearchState 字段的双写对照表

迁移期间，stage 同时写 state 和 artifact。以下是完整对照：

| Stage | 写入的 state 字段 | 同时产出的 artifact | 过渡结束后 state 字段处理 |
|---|---|---|---|
| `planning` | `planning.research_questions`, `planning.search_queries`, `planning.query_routes`, `planning.scope`, `planning.budget` | `TopicBrief`, `SearchPlan` | 产出类字段停写，`budget` 保留在 RunContext |
| `retrieval` | `research.papers[]`, `research.web_sources[]` | `CorpusSnapshot` | 产出类字段停写 |
| `indexing` | `research.indexed_paper_ids[]`, `research.figure_indexed_paper_ids[]` | `CorpusSnapshot` (updated) | 产出类字段停写 |
| `analysis` | `research.analyses[]` | `PaperNote[]` | 产出类字段停写 |
| `synthesis` | `research.synthesis`, `evidence.claim_evidence_map[]`, `evidence.gaps[]` | `RelatedWorkMatrix`, `GapMap` | 产出类字段停写 |
| `retrieval_reviewer` | `review.retrieval_review` | `CritiqueReport` | 产出类字段停写 |
| `experiments` | `research.experiment_plan` | (Phase 5 才产出 `ExperimentSpec`) | 暂不处理 |
| `reporting` | `report.report` | (Phase 5 才产出 `ManuscriptDraft`) | 暂不处理 |

始终保留在 runtime context（不迁移到 artifact）的字段：

- `iteration`, `max_iterations`, `should_continue`
- `_retrieval_review_retries`, `_experiment_review_retries`
- `await_experiment_results`
- `status`, `error`, `run_id`, `_cfg`
