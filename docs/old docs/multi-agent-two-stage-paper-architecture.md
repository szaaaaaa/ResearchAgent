# ResearchAgent vNext: 从 RAG Agent 到 Research Operating System

> 日期：2026-03-08

## 1. 文档定位

本文档重新定义 `ResearchAgent` 的升级方向。

目标不再是继续把当前的 `RAG + graph` 主流程做厚，而是把系统升级为一个面向科研全流程的 `Research Operating System`，服务于最终目标：

`AI scientist assistant`

目标能力范围：

- `literature search`
- `paper parsing`
- `experiment planning`
- `code generation`
- `experiment running`
- `result analysis`
- `paper writing`

本文档重点回答三个问题：

1. `frontier reasoning model`、`skills`、`multi-agent` 三者分别承担什么职责
2. 它们应该如何组合成 Research OS
3. 当前仓库应该如何重构，而不是继续在现有 graph 上叠复杂度

---

## 2. 核心判断

### 2.1 不是“更大的 Agent”，而是“更好的分层”

当前项目的问题，不是能力不够，而是主抽象不对。

当前主抽象仍然是：

- `graph node`
- `stage`
- `reviewer gate`

这对单条研究报告流水线有效，但不适合作为长期演进到 `AI scientist assistant` 的基础。

Research OS 的主抽象应该改为：

- `agent role`
- `skill`
- `artifact`
- `runtime`

### 2.2 Frontier Reasoning Model、Skills、Multi-Agent 的关系

本文档采用如下假设：

- `frontier reasoning model` 是默认的前沿通用推理内核
- `skills` 是可复用、可组合、可测试的能力单元
- `multi-agent` 是角色分工与审查机制，不是能力重复实现

因此三者关系不是并列的，而是分层的：

1. `frontier reasoning model` 提供强推理、规划、综合、工具调用能力
2. `skills` 提供稳定的研究动作能力
3. `multi-agent` 通过不同角色调用不同 skill 组合，形成协作与对抗审查

一句话：

`大模型是脑，skills 是手，multi-agent 是组织结构，runtime 是操作系统。`

### 2.3 最重要的设计原则

1. 不把每个 agent 都做成一套私有逻辑
2. 不把 skills 仅当作外部平台提示词附件
3. 不让多 agent 直接建立在当前厚 graph 之上
4. 不把 Research OS 做成“无限角色 + 无限流程”的膨胀系统

---

## 3. Research OS 的目标架构

## 3.1 分层架构

```text
User / UI / CLI
    -> Research Runtime
        -> Agent Layer
            -> Skill Layer
                -> Executor / Provider Layer
                    -> Infra Layer
                        -> External Systems
```

### Layer 1: Research Runtime

职责：

- run lifecycle
- state / checkpoint / resume
- budget / timeout / retry policy
- artifact persistence
- HITL gate
- audit trail

说明：

这一层不能消失。
即使使用最强模型和 skills，也仍然需要最薄的一层 OS runtime 来维持任务可恢复、可追踪、可控。

### Layer 2: Agent Layer

职责：

- 角色分工
- 决策谁调用哪个 skill
- 解释 artifact
- 发起 critique / revision / block

这一层不是能力实现层，而是“角色与协作层”。

### Layer 3: Skill Layer

职责：

- 封装高频研究能力
- 接受结构化输入，输出结构化 artifact
- 可单独测试、单独升级、单独限权

这一层是未来系统的核心资产。

### Layer 4: Executor / Provider Layer

职责：

- skill 调用时的执行桥接
- 搜索、索引、检索、LLM、代码执行、远程实验等后端访问

这一层当前仓库已经有基础，不应推倒重写。

### Layer 5: Infra Layer

职责：

- Chroma / BM25 / PDF parsing / figure extraction / SSH runner / local runner / external APIs

这一层是底层能力设施。

---

## 4. Frontier Model 在系统中的位置

## 4.1 不把具体模型当作“一个最终产品”，而当作“默认认知内核”

`frontier reasoning model` 在本架构中不是一个具体 UI 产品概念，而是：

- 默认的通用 reasoning engine
- 默认的 planning / synthesis / critique engine
- 默认的 skill caller

也就是说：

- agent role 不等于不同模型
- 大多数角色可以共享同一个前沿模型
- 差异来自：`system prompt + role policy + allowed skills + artifact contract`

默认可接入的模型可以是：

- `Gemini 3 Pro`
- `ChatGPT 5.4`
- `Claude`

这里真正要绑定的不是某一家模型，而是一个可替换的模型接口。

## 4.2 为什么不建议“一角色一模型栈”

如果每个 agent 都有自己独立的一套模型、工具和逻辑，会带来：

1. 行为难以对齐
2. 成本难以控制
3. 问题难以归因
4. 角色演进越来越重

更好的做法是：

- 共享统一的 frontier model kernel
- 用 skill profile 和角色约束来形成差异

也就是说：

`同一个大脑，不同的手，不同的权限，不同的职责。`

## 4.3 模型切换的接口边界

为了支持 `Gemini 3 Pro / ChatGPT 5.4 / Claude` 可切换，模型层必须下沉到独立 provider adapter。

推荐边界：

```text
Agent / Skill
    -> LLMProvider
        -> OpenAIAdapter / GeminiAdapter / ClaudeAdapter
```

统一接口只暴露最小能力：

- `generate`
- `stream`
- `tool_call`
- `structured_output`

同时在 provider adapter 内部统一：

- message schema
- tool schema
- structured output contract
- trace event contract

这样 agent、skill、artifact 都不需要感知底层模型供应商。

## 4.4 哪些能力必须保持模型无关

以下能力必须保留在 Research OS 自己的 runtime / executors / infra 中，而不是绑定某家模型的 built-in tools：

- literature search
- paper parsing
- retrieval
- code execution
- experiment running
- artifact persistence

模型主要负责：

- reasoning
- planning
- critique
- structured generation
- skill selection

---

## 5. Multi-Agent 在 Research OS 中如何落地

## 5.1 不再沿用“无限 specialist agent”思路

当前升级方向不应是：

- 越来越多 agent
- 每个 agent 一点点能力
- agent 间自由群聊式协作

这会直接带来：

1. runtime 复杂度失控
2. 调试困难
3. 责任边界模糊
4. 角色之间大量重复能力

## 5.2 长期收敛为 6 个角色

为覆盖 Research OS 的核心能力，推荐收敛为以下 6 个逻辑角色：

1. `Conductor`
2. `Researcher`
3. `Experimenter`
4. `Analyst`
5. `Writer`
6. `Critic`

这是比此前 `5-agent 两阶段论文系统` 更贴近 `Research OS` 的版本，但仍然是收敛的，不是膨胀的。

## 5.3 第一阶段先做 3-Agent MVP

第一阶段不直接落完整 6 角色，而是先收敛成：

1. `Conductor`
2. `Researcher`
3. `Critic`

原因很直接：

1. 当前最先要跑通的是文献综述闭环
2. `Experimenter / Analyst / Writer` 依赖后续实验执行与写作链路
3. 3-agent MVP 已足够验证 skills、artifacts、critique loop 是否成立

第一阶段目标不是完整 Research OS，而是：

`先把 literature review / related work / gap analysis 跑通。`

### 1. Conductor

职责：

- topic intake
- task decomposition
- phase planning
- budget / policy control
- 决定下一步调用哪个 agent / skill

它是“控制平面”，不是内容生产者。

### 2. Researcher

职责：

- literature search
- paper parsing
- corpus curation
- related work synthesis
- gap mapping
- hypothesis candidate generation

它吸收当前仓库的：

- retrieval
- indexing
- analysis
- 部分 synthesis

### 3. Experimenter

职责：

- experiment planning
- code generation / code patch suggestion
- run spec generation
- 提交实验到 local / ssh runner

它不是简单的“写实验计划”，而是从 idea 进入可执行研究任务。

### 4. Analyst

职责：

- experiment result ingestion
- metrics normalization
- result interpretation
- table / figure summary
- consistency check with hypothesis

这一步必须从 `Experimenter` 独立出来，否则“设计实验”和“解释结果”会耦合过深。

### 5. Writer

职责：

- stage draft writing
- manuscript assembly
- abstract rewrite
- style normalization
- final paper writing

Writer 只负责写，不负责自证正确。

### 6. Critic

职责：

- challenge current artifacts
- catch unsupported claims
- detect weak novelty / weak experimental validity / overclaiming
- decide `pass` / `revise_then_continue` / `block`

Critic 是质量控制层，不是内容生成层。

## 5.4 为什么没有单独的 Code Agent / Runner Agent

当前阶段不建议再把 `code generation` 和 `experiment running` 再拆成两个公开角色。

原因：

1. 会增加调度复杂度
2. 对当前项目阶段来说收益不高
3. 它们更适合作为 `Experimenter` 的 skill 组，而不是独立 agent

所以：

- `code generation` 是 skill
- `experiment running` 是 skill
- `Experimenter` 是调用它们的 agent

---

## 6. Skills 在 Research OS 中如何定义

## 6.1 Skills 不是“随手加一个工具说明”

Research OS 中的 skill 必须是一等能力单元。

每个 skill 至少需要有：

- `skill_id`
- `purpose`
- `input_artifacts`
- `output_artifacts`
- `allowed_tools`
- `model_profile`
- `budget_policy`
- `validation_rule`

也就是说，skill 必须是：

- 可调用
- 可复用
- 可替换
- 可测试
- 可审计

## 6.2 Skill 的粒度原则

不建议：

- 一函数一个 skill
- 一节点一个 skill
- 一角色一套私有 skill

建议粒度：

- 一类完整研究动作 = 一个 skill

例如：

- `search_literature`
- `parse_paper_bundle`
- `build_related_work_matrix`
- `design_experiment`
- `generate_research_code`
- `submit_experiment_run`
- `analyze_result_bundle`
- `write_manuscript_section`
- `critique_stage_draft`

## 6.3 第一批 Skill 必须严格对应现有实现

Skill catalog 可以前瞻性地规划更多条目，但代码中实际落地的第一批 skill 必须有现成的 stage/reviewer 支撑。以下是严格的 1:1 映射：

| Skill ID | 现有实现 | 入口函数 |
|---|---|---|
| `plan_research` | `stages/planning.py` | `run_planning()` |
| `search_literature` | `stages/retrieval.py` | `run_retrieval()` |
| `parse_paper_bundle` | `stages/indexing.py` | `run_indexing()` |
| `extract_paper_notes` | `stages/analysis.py` | `run_analysis()` |
| `build_related_work_matrix` | `stages/synthesis.py` | `run_synthesis()` |
| `design_experiment` | `stages/experiments.py` | `run_experiment_recommendation()` |
| `generate_report` | `stages/reporting.py` | `run_reporting()` |
| `critique_retrieval` | `reviewers/retrieval_reviewer.py` | `run_retrieval_review()` |
| `critique_experiment` | `reviewers/experiment_reviewer.py` | `run_experiment_review()` |
| `critique_claims` | `reviewers/post_report_review.py` | `review_claims_and_citations()` |

尚无实现的 skill（如 `dedupe_and_rank_sources`、`normalize_metrics`、`patch_existing_codebase`）只在 catalog 文档中列出，不在第一版代码中创建空壳。

## 6.3 推荐的第一批 Skill Catalog

### A. Literature Skills

- `search_literature`
- `dedupe_and_rank_sources`
- `parse_paper_bundle`
- `extract_paper_notes`
- `build_related_work_matrix`
- `map_research_gaps`

### B. Experiment Skills

- `design_experiment`
- `validate_experiment_spec`
- `generate_research_code`
- `patch_existing_codebase`
- `prepare_run_bundle`
- `submit_experiment_run`
- `ingest_experiment_results`

### C. Analysis Skills

- `normalize_metrics`
- `compare_against_baselines`
- `summarize_tables_and_figures`
- `analyze_hypothesis_support`
- `detect_result_anomalies`

### D. Writing Skills

- `write_stage1_draft`
- `write_stage2_draft`
- `assemble_manuscript`
- `rewrite_abstract`
- `polish_paper`

### E. Critique Skills

- `critique_related_work`
- `critique_experiment_spec`
- `critique_results_and_claims`
- `audit_claim_evidence_alignment`
- `decide_revision_or_block`

---

## 7. Agent 与 Skill 的关系

## 7.1 一个 agent 调一组 skills，而不是自带一套算法

推荐关系如下：

| Agent | Skill 组合 |
|---|---|
| `Conductor` | `topic_intake`, `scope_budgeting`, `phase_planning`, `route_next_step` |
| `Researcher` | `search_literature`, `parse_paper_bundle`, `extract_paper_notes`, `build_related_work_matrix`, `map_research_gaps` |
| `Experimenter` | `design_experiment`, `validate_experiment_spec`, `generate_research_code`, `prepare_run_bundle`, `submit_experiment_run` |
| `Analyst` | `ingest_experiment_results`, `normalize_metrics`, `compare_against_baselines`, `analyze_hypothesis_support` |
| `Writer` | `write_stage1_draft`, `write_stage2_draft`, `assemble_manuscript`, `rewrite_abstract`, `polish_paper` |
| `Critic` | `critique_related_work`, `critique_experiment_spec`, `critique_results_and_claims`, `audit_claim_evidence_alignment`, `decide_revision_or_block` |

## 7.2 同一个 Skill 可被多个 Agent 复用

例如：

- `audit_claim_evidence_alignment` 可被 `Critic` 调用，也可被 `Writer` 在 final pass 前调用
- `normalize_metrics` 可被 `Analyst` 调用，也可被 `Experimenter` 在结果预处理时调用

这正是 skill 架构比 node 架构更稳定的原因。

---

## 8. Artifact 才是多 Agent 协作的真正接口

如果多 agent 直接共享一个巨大扁平 state，系统会很快失控。

所以 agent 之间不应该主要通过“读取全局 state 字段”协作，而应该主要通过 artifact 协作。

## 8.1 推荐核心 Artifacts

面向 Research OS，推荐最小核心 artifact 集如下：

1. `TopicBrief`
2. `SearchPlan`
3. `CorpusSnapshot`
4. `PaperNote[]`
5. `RelatedWorkMatrix`
6. `GapMap`
7. `HypothesisSet`
8. `ExperimentSpec`
9. `CodeChangeSet`
10. `RunBundle`
11. `ExperimentResultBundle`
12. `ResultAnalysis`
13. `ManuscriptDraft`
14. `CritiqueReport`

## 8.2 Artifact 设计原则

每个 artifact 至少应具备：

- `artifact_type`
- `artifact_id`
- `producer`
- `source_inputs`
- `payload`
- `validation_status`
- `timestamp`

这样做的意义是：

1. agent 协作边界清晰
2. easier resume / checkpoint
3. easier HITL
4. easier audit
5. easier skill testing

---

## 9. Research OS 的主流程

## 9.0 3-Agent MVP 主流程

```text
topic intake
  -> Conductor.plan
  -> Researcher.search_literature
  -> Researcher.parse_paper_bundle
  -> Researcher.extract_paper_notes
  -> Researcher.build_related_work_matrix
  -> Critic.critique_related_work
      -> revise or pass
  -> output literature review package
```

产出：

- `TopicBrief`
- `SearchPlan`
- `CorpusSnapshot`
- `PaperNote[]`
- `RelatedWorkMatrix`
- `GapMap`
- `CritiqueReport`

## 9.1 阶段 A：文献与问题形成

```text
topic intake
  -> Conductor.plan
  -> Researcher.search_literature
  -> Researcher.parse_paper_bundle
  -> Researcher.build_related_work_matrix
  -> Researcher.map_gaps
  -> Researcher.propose_hypotheses
  -> Critic.critique_stageA
      -> revise or pass
```

产出：

- `TopicBrief`
- `CorpusSnapshot`
- `RelatedWorkMatrix`
- `GapMap`
- `HypothesisSet`

## 9.2 阶段 B：实验设计与代码生成

```text
HypothesisSet
  -> Experimenter.design_experiment
  -> Experimenter.generate_research_code
  -> Critic.critique_experiment_spec
      -> revise or pass
```

产出：

- `ExperimentSpec`
- `CodeChangeSet`
- `RunBundle`

## 9.3 阶段 C：实验执行

```text
RunBundle
  -> Experimenter.submit_experiment_run
  -> runner(local / ssh)
  -> ingest_experiment_results
```

产出：

- `ExperimentResultBundle`

## 9.4 阶段 D：结果分析与写作

```text
ExperimentResultBundle
  -> Analyst.normalize_metrics
  -> Analyst.analyze_hypothesis_support
  -> Writer.write_stage2_draft
  -> Writer.assemble_manuscript
  -> Critic.critique_final_draft
      -> revise or pass
```

产出：

- `ResultAnalysis`
- `ManuscriptDraft`
- `FinalPaper`

---

## 10. 当前仓库如何映射到新架构

## 10.1 可以直接保留的层

这些层不应推倒：

- `plugins/`
- `providers/`
- `executors/`
- `infra/`
- `ingest/`
- `rag/`
- tracing / events / run outputs

原因：

它们本质上是 Skill Runtime 的底座，而不是旧 graph 的包袱。

## 10.2 应该被提升为 Skill 的现有模块

### 当前 `stages/` 更适合演进为 skill implementation

可映射为：

- [planning.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/planning.py) -> `query_plan` / `phase_plan`
- [retrieval.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/retrieval.py) -> `search_literature`
- [indexing.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/indexing.py) -> `parse_paper_bundle`
- [analysis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/analysis.py) -> `extract_paper_notes`
- [synthesis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/synthesis.py) -> `build_related_work_matrix` / `map_gaps`
- [experiments.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/experiments.py) -> `design_experiment` / `ingest_experiment_results`
- [reporting.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/reporting.py) -> `write_manuscript_section`

### 当前 `reviewers/` 更适合演进为 critique skills

可映射为：

- [retrieval_reviewer.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/retrieval_reviewer.py) -> `critique_related_work`
- [experiment_reviewer.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/experiment_reviewer.py) -> `critique_experiment_spec`
- [post_report_review.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/post_report_review.py) -> `critique_results_and_claims`

## 10.3 当前最需要被弱化的层

当前最需要弱化的是：

- [graph.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/graph.py)
- [schemas.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/core/schemas.py)

原因：

1. `graph.py` 仍然是系统主抽象
2. `ResearchState` 仍然是大而全的协作载体
3. 这两者都会限制 skill 化和多 agent 化

未来它们应变成：

- `graph` -> thin runtime workflow
- `ResearchState` -> run context + artifact registry view

## 10.4 graph.py 的具体过渡策略

当前 `graph.py` 包含 12 个 LangGraph 节点和复杂路由逻辑（retry、degrade、HITL pause）。不能一次替换，必须分三步过渡：

### Step 1：graph 节点内部调用 skill（而非直接调用 stage）

当前：

```text
graph node "fetch_sources" → 直接调用 retrieval.py 的 run_retrieval()
```

目标：

```text
graph node "fetch_sources" → 调用 skill_registry.invoke("search_literature", artifacts)
```

在这一步，graph 拓扑不变，但节点实现从"直接调 stage 函数"改为"通过 skill 调用"。这样 skill 的输入输出契约可以先固化，而 graph 的路由逻辑不受影响。

### Step 2：新 runtime orchestrator 替代 graph 的角色调度

当前 graph 的路由逻辑（如 `review_retrieval → retry/degrade/continue`）移入 `runtime/orchestrator.py`，由 Conductor role 驱动。

关键决策：新 runtime 仍然使用 LangGraph 作为底层执行引擎和 checkpoint 机制，但 graph 的拓扑由 orchestrator 动态生成，而不再是一个静态的硬编码 graph。

```text
当前：graph.py 静态定义 12 节点 + 所有边
目标：orchestrator 按 role policy 动态决定下一个 skill 调用
底层：仍用 LangGraph StateGraph 做 checkpoint/resume，但拓扑是 orchestrator 生成的
```

### Step 3：旧 graph 入口降级为兼容模式

迁移完成前，CLI 保留两条入口：

- `--mode=legacy`：走现有 graph.py（默认，直到 MVP 验证通过）
- `--mode=os`：走新 runtime orchestrator

MVP 验证通过后，默认切换到 `--mode=os`，`--mode=legacy` 保留一个版本周期后移除。

## 10.5 ResearchState 的分阶段瘦身策略

当前 `ResearchState` 包含 ~30 个字段，分布在 5 个 namespace 中。不能一次拆掉，需要区分两类字段：

### 产出类字段（应迁移到 artifact）

这些是 stage 的核心产出，应当由 artifact 承载：

| 当前 state 字段 | 目标 artifact |
|---|---|
| `research.papers[]` | `CorpusSnapshot.papers` |
| `research.web_sources[]` | `CorpusSnapshot.web_sources` |
| `research.analyses[]` | `PaperNote[]` |
| `research.synthesis` | `RelatedWorkMatrix.narrative` |
| `evidence.claim_evidence_map[]` | `RelatedWorkMatrix.claims` |
| `evidence.gaps[]` | `GapMap.gaps` |
| `planning.research_questions[]` | `SearchPlan.research_questions` |
| `planning.search_queries[]` | `SearchPlan.queries` |
| `report.report` | `ManuscriptDraft.content` |
| `review.retrieval_review` | `CritiqueReport` |
| `research.experiment_plan` | `ExperimentSpec` |

### 控制类字段（保留在 runtime context）

这些是运行时控制信号，不适合做成 artifact：

- `iteration` / `max_iterations` / `should_continue`
- `_retrieval_review_retries` / `_experiment_review_retries`
- `await_experiment_results`
- `status` / `error` / `run_id`
- `_cfg`

### 过渡期双写策略

Phase 1 期间，stage 同时写入 state 字段和 artifact。后续节点优先消费 artifact，找不到时 fallback 到 state。具体做法：

```python
# stage 输出时
result = run_retrieval(...)
artifact = CorpusSnapshot(papers=result["papers"], web_sources=result["web_sources"])
artifact_registry.save(artifact)
return {**result, "_artifacts": [artifact.artifact_id]}  # 双写
```

Phase 3 之后，新 runtime 只消费 artifact，不再读 state 产出类字段。state 中的产出类字段变为只写（仅为 legacy 兼容保留）。

## 10.6 当前 Provider 层与目标接口的差距分析

当前仓库已有的抽象（`core/interfaces.py`）：

```python
class LLMBackend(Protocol):
    def generate(*, system_prompt, user_prompt, model, temperature, cfg) -> str
```

目标接口要求四个方法：`generate`、`stream`、`tool_call`、`structured_output`。

差距分析：

| 能力 | 当前状态 | 差距 |
|---|---|---|
| `generate` | 已有，可用 | 无 |
| `stream` | 未抽象，Gemini 底层支持但未暴露 | 第一版可不做 |
| `tool_call` | 未抽象，Gemini/OpenAI 格式不同 | 第一版可不做，当前 stage 不依赖 tool calling |
| `structured_output` | 未抽象，JSON 解析散落在各 stage 的 `_parse_json_safe` 中 | **应在第一版统一** |

推荐第一版 provider 接口：

```python
class LLMProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse: ...
    def generate_structured(self, request: ModelRequest, schema: type[T]) -> T: ...
```

`stream` 和 `tool_call` 留到 Phase 5（实验执行闭环需要时再加）。

当前两个 backend 的适配成本：

- `OpenAIChatBackend`（`plugins/llm/openai_chat.py`）：包装 `infra/llm/openai_chat_client.py`，改动量小
- `GeminiChatBackend`（`plugins/llm/gemini_chat.py`）：包装 `infra/llm/gemini_chat_client.py`，改动量小

两者都只需要在现有 `generate()` 基础上加一层 `generate_structured()` 即可。不需要重写。

---

## 11. 最终推荐架构

## 11.1 推荐的系统表达

不再把系统定义为：

`一个自动研究 Agent`

而定义为：

`一个由 frontier model 驱动、由 skills 提供能力、由多 agent 提供角色分工、由 runtime 提供控制平面的 Research Operating System。`

## 11.2 推荐的正式架构表述

```text
Frontier Model Kernel
    + Research Skill Runtime
    + 6 Role Agents
    + Artifact-Centric Workflow
    + Controlled Experiment Execution Layer
    = Research Operating System
```

---

## 12. 明确不做什么

为了避免新一轮膨胀，本阶段明确不做：

1. 不做十几个 specialist agent
2. 不做自由群聊式 agent debate
3. 不做全量 runner 矩阵
4. 不把 skills 设计成零散提示词集合
5. 不继续围绕厚 graph 增量缝补

---

## 13. 结论

ResearchAgent 的正确升级方向，不是：

- 在当前 graph 上继续叠功能
- 先做复杂多 agent，再想怎么复用能力

而是：

1. 先把系统重定义为 `Research OS`
2. 先把能力抽象成 `skills`
3. 再让 `multi-agent` 成为 skills 的角色化调度层
4. 再由可切换的 `frontier reasoning model` 作为统一认知内核驱动整个系统

一句话总结：

`Research OS = Frontier Agent Kernel + Skills + Role-Based Multi-Agent + Artifact-Centric Runtime`
