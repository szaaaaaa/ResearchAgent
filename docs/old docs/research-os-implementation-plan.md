# Research OS 开发落地实施方案

> 日期：2026-03-08

## 1. 文档目标

本文档基于 [multi-agent-two-stage-paper-architecture.md](/c:/Users/ziang/Desktop/ResearchAgent/docs/multi-agent-two-stage-paper-architecture.md)，回答一个更具体的问题：

`如何把当前仓库按最小风险、可持续迁移的方式，落地为一个 Research Operating System。`

本文档不是概念说明，而是开发实施方案。重点包括：

1. 先做什么，后做什么
2. 每一阶段改哪些模块
3. 每一阶段交付什么能力
4. 如何避免一边重构一边把现有系统打坏

---

## 2. 实施总原则

### 2.1 不推倒重来，做受控迁移

当前仓库已经具备以下可复用基础：

- `providers/`
- `executors/`
- `plugins/`
- `infra/`
- `ingest/`
- `rag/`
- `stages/`
- `reviewers/`
- 现有 `CLI + run outputs + tracing/events`

因此本次实施不采用“大爆炸重写”，而采用：

`保留下层能力层，重构上层主抽象。`

### 2.2 先 skill 化，再多 agent 化

正确顺序是：

1. 先定义 artifact
2. 先把现有 stage/reviewer 提升为 skill
3. 再引入薄 runtime
4. 再引入 role-based multi-agent
5. 最后再接代码生成和实验执行闭环

不建议的顺序是：

1. 直接在当前厚 graph 上叠多 agent
2. 每个 agent 自带一套私有逻辑
3. 最后再想办法复用能力

### 2.3 统一认知内核，分离角色差异

`frontier reasoning model` 在本方案中作为统一认知内核，并支持在 `Gemini 3 Pro / ChatGPT 5.4 / Claude` 之间切换。

角色差异不通过“每个 agent 一套模型栈”实现，而通过以下四项实现：

- role policy
- allowed skills
- artifact contract
- runtime budget

### 2.4 Provider Adapter 必须先于模型切换落地

为了保证 `Gemini 3 Pro / ChatGPT 5.4 / Claude` 可切换，模型能力必须先收敛成统一 provider 接口。

推荐最小接口：

```python
class LLMProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse: ...
    def stream(self, request: ModelRequest): ...
    def call_tools(self, request: ToolCallRequest) -> ToolCallResponse: ...
```

并分别实现：

- `OpenAIProvider`
- `GeminiProvider`
- `ClaudeProvider`

同时统一：

- message schema
- tool schema
- structured output contract
- trace event contract

这样 role、skill、artifact 都不需要感知底层模型供应商。

### 2.5 每次只引入一个新的主抽象

实施过程中只按以下顺序逐步引入主抽象：

1. `artifact`
2. `skill`
3. `role agent`
4. `runtime policy`

不要在同一个里程碑中同时重写：

- graph
- state
- stages
- reviewers
- UI
- runner

否则风险过高，定位困难。

---

## 3. 当前仓库到目标系统的映射

## 3.1 当前仓库的真实结构

当前仓库已经接近一个可演进的基础设施底座：

- [executor_router.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/core/executor_router.py)：能力调用路由
- [bootstrap.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/plugins/bootstrap.py)：插件和执行器装配
- [planning.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/planning.py)：规划能力
- [retrieval.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/retrieval.py)：检索能力
- [indexing.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/indexing.py)：论文解析与索引能力
- [analysis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/analysis.py)：阅读分析能力
- [synthesis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/synthesis.py)：综述与综合能力
- [experiments.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/experiments.py)：实验规划能力
- [reporting.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/reporting.py)：报告写作能力
- [retrieval_reviewer.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/retrieval_reviewer.py)：检索质量审查
- [experiment_reviewer.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/experiment_reviewer.py)：实验设计审查
- [post_report_review.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/post_report_review.py)：报告审查

问题不在于“没有能力模块”，而在于：

- 顶层主抽象仍然是 `graph node`
- 协作载体仍然是大而全的 `ResearchState`
- stage/reviewer 还没有成为一等 skill

## 3.2 目标映射关系

目标系统中：

- `stages/` 主要演进为 `skills`
- `reviewers/` 主要演进为 `critique skills`
- `graph.py` 演进为薄 runtime workflow
- `ResearchState` 演进为 runtime context + artifact registry view

---

## 4. 目标系统分层

实施后系统推荐分为 6 层：

1. `Interface Layer`
2. `Research Runtime Layer`
3. `Agent Role Layer`
4. `Skill Layer`
5. `Executor / Provider Layer`
6. `Infra Layer`

## 4.1 Interface Layer

职责：

- CLI
- UI
- run/resume/inspect
- artifact 浏览

现阶段建议保留现有 CLI，不优先重做 UI。

## 4.2 Research Runtime Layer

职责：

- run lifecycle
- checkpoint/resume
- artifact persistence
- policy enforcement
- HITL gate
- budget control

这层必须存在，但必须保持薄。

## 4.3 Agent Role Layer

推荐角色：

1. `Conductor`
2. `Researcher`
3. `Experimenter`
4. `Analyst`
5. `Writer`
6. `Critic`

角色层只负责：

- 解释任务
- 选择 skill
- 读取 artifact
- 触发审查和修订

角色层不直接承载底层业务能力实现。

## 4.4 Skill Layer

这是实施重点。

skill 是未来系统的核心资产。每个 skill 都应具备：

- 清晰输入
- 清晰输出
- 限定工具
- 可单独测试
- 可单独审查

## 4.5 Executor / Provider Layer

这一层需要明确拆成两部分：

1. `Provider Adapter`
   - OpenAI / Gemini / Claude 模型适配
2. `Executors`
   - search / parser / runner / retrieval 等系统能力

两者不能混在一起。

原因是：

- provider 负责模型兼容
- executor 负责工具和外部能力接入

只有这样，Research OS 才能切换模型而不重写 skills。

## 4.6 Infra Layer

这层继续保留：

- 检索
- PDF 解析
- embedding/reranking
- 本地/远程执行
- 外部 API

---

## 5. 第一个版本的边界

Research OS 不应该在第一版就追求“全自动 AI scientist”。

第一版的明确边界是：

1. 覆盖完整科研链路
2. 但允许部分节点为 HITL
3. 允许实验执行先以本地/SSH 受控模式存在
4. 允许代码生成先以 patch proposal 形式存在
5. 优先打通 artifact 流、skill 流、agent 协作流

第一版不追求：

1. 完整自动发表级 paper
2. 全自动多实验集群调度
3. 任意代码库零人工改造
4. 无限角色扩张

---

## 6. 实施阶段总览

建议按 6 个阶段推进：

1. `Phase 0`：基线冻结与重构边界确认
2. `Phase 1`：Artifact 层落地
3. `Phase 2`：Skill Runtime 落地
4. `Phase 3`：3-Agent Literature Review MVP
5. `Phase 4`：扩展到完整 Role-Based Multi-Agent
6. `Phase 5`：代码生成与实验执行闭环

每一阶段必须满足：

- 有明确交付物
- 有明确验收标准
- 有回退路径

---

## 7. Phase 0：基线冻结与重构边界确认

## 7.1 目标

在不引入新架构的前提下，明确“哪些行为必须保留”，避免后续迁移把当前能跑的东西打坏。

## 7.2 本阶段工作

1. 固定当前主流程能力边界
   - literature retrieval
   - paper indexing/parsing
   - source analysis
   - synthesis
   - experiment recommendation
   - report generation

2. 列出当前核心入口
   - CLI 入口
   - runtime 输出
   - graph 节点
   - reviewers

3. 定义迁移期间的兼容原则
   - CLI 不变
   - 原始 run artifacts 继续保留
   - 老 graph 在迁移期间仍可运行

## 7.3 交付物

1. 基线能力清单
2. 兼容性清单
3. 第一批 artifact 名单
4. 第一批 skill 名单

## 7.4 验收标准

1. 能明确回答“哪些模块先不动”
2. 能明确回答“第一阶段改动不触碰哪些关键路径”

---

## 8. Phase 1：Artifact 层落地

## 8.1 目标

先把系统的协作接口从“大而全 state”切换到“结构化 artifact”。

这是整个实施方案的第一关键阶段。

## 8.2 第一批核心 Artifacts

建议先落这 10 个：

1. `TopicBrief`
2. `SearchPlan`
3. `CorpusSnapshot`
4. `PaperNote`
5. `RelatedWorkMatrix`
6. `GapMap`
7. `ExperimentSpec`
8. `ExperimentResultBundle`
9. `ManuscriptDraft`
10. `CritiqueReport`

## 8.3 Artifact 最小字段

每个 artifact 第一版至少包含：

- `artifact_type`
- `artifact_id`
- `producer`
- `source_inputs`
- `payload`
- `created_at`

第一版先不要引入复杂 lineage 平台。

## 8.4 对当前仓库的改造方式

本阶段不要求立刻删除 `ResearchState`。

更合理的做法是：

1. 先让现有 stages 在输出时附带 artifact
2. runtime 同时保留原状态字段与 artifact 视图
3. 逐步让后续节点优先消费 artifact，而不是直接消费大 state

## 8.5 交付物

1. artifact schema 定义
2. artifact 序列化与落盘格式
3. 现有主流程的 artifact sidecar 输出

## 8.6 验收标准

1. 每次 run 至少能导出结构化 artifact
2. 后续步骤能读取 artifact 而不是只依赖临时 state
3. 失败恢复时可以从 artifact 继续，而不是只能从整条 graph 重跑

## 8.7 风险

1. schema 设计过重
2. state 与 artifact 双写不一致
3. 一次定义过多 artifact，导致迁移成本过高

## 8.8 控制策略

1. 只落第一批核心 artifact
2. 第一版不做复杂版本系统
3. artifact 只服务运行时，不先做平台化

---

## 9. Phase 2：Skill Runtime 落地

## 9.1 目标

把现有 `stages/` 和 `reviewers/` 提升为一等 skill。

## 9.2 Skill 的最小契约

每个 skill 至少定义：

- `skill_id`
- `purpose`
- `input_artifacts`
- `output_artifacts`
- `allowed_tools`
- `model_profile`
- `budget_policy`
- `validator`

## 9.3 第一批 Skill Catalog

### Literature

- `search_literature`
- `dedupe_and_rank_sources`
- `parse_paper_bundle`
- `extract_paper_notes`
- `build_related_work_matrix`
- `map_research_gaps`

### Experiment

- `design_experiment`
- `validate_experiment_spec`

### Writing

- `write_stage1_draft`
- `write_stage2_draft`
- `assemble_manuscript`

### Critique

- `critique_related_work`
- `critique_experiment_spec`
- `critique_results_and_claims`

## 9.4 对当前模块的映射

- [planning.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/planning.py) -> `query_plan`
- [retrieval.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/retrieval.py) -> `search_literature`
- [indexing.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/indexing.py) -> `parse_paper_bundle`
- [analysis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/analysis.py) -> `extract_paper_notes`
- [synthesis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/synthesis.py) -> `build_related_work_matrix`
- [experiments.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/experiments.py) -> `design_experiment`
- [reporting.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/reporting.py) -> `write_stage*_draft`

## 9.5 实施方式

本阶段不建议重写 stage 逻辑。

建议做法是：

1. 先加 skill wrapper
2. 内部继续调用现有 stage 实现
3. 在 wrapper 层收敛输入输出契约
4. reviewer 同样以 skill 形式暴露

这样做的好处是：

1. 复用现有逻辑
2. 降低改动面
3. 先完成主抽象迁移，再逐步内部替换实现

## 9.6 交付物

1. skill registry
2. skill contract
3. 第一批 skill wrapper
4. skill 级别测试入口

## 9.7 验收标准

1. 不跑 graph，也能独立执行单个 skill
2. skill 输入输出全部基于 artifact
3. reviewer 可以作为 critique skill 单独调用

---

## 10. Phase 3：3-Agent Literature Review MVP

## 10.1 目标

先落一个最小可用的 3-agent MVP，只覆盖文献综述链路：`Conductor + Researcher + Critic`。

这一阶段的意义是：

先用最小角色集验证 Research OS 的主抽象可运行，再扩展到更多角色。

## 10.2 设计

此时系统采用 3-agent 协作，但仍然维持很薄的 runtime。主流程只覆盖文献综述闭环：

1. `Conductor` 读取任务目标并规划文献综述范围
2. `Researcher` 调用 literature skills 生成综述 artifacts
3. `Critic` 审查 related work / gap analysis
4. runtime 决定 revise 或 pass

## 10.3 为什么必须先做这一步

如果跳过这一步直接上多 agent，会同时引入三种复杂度：

1. skill 编排复杂度
2. 角色协作复杂度
3. 运行时策略复杂度

这样很难定位问题到底在哪一层。

## 10.4 交付物

1. `Conductor + Researcher + Critic` 的最小角色策略
2. literature review artifact-first 流程
3. 与当前 CLI 兼容的 3-agent MVP 路径

## 10.5 验收标准

1. 能完成 topic -> literature search -> paper parsing -> related work -> critique 的主流程
2. 主流程不再直接绑定 graph 节点名
3. 运行结果以 artifact 为主，不再以临时 state 为主

---

## 11. Phase 4：扩展到完整 Role-Based Multi-Agent

## 11.1 目标

在 skill runtime 稳定后，再引入角色化多 agent。

## 11.2 推荐角色落地顺序

不要一次性上 6 个角色。

推荐顺序：

1. `Conductor`
2. `Researcher`
3. `Critic`
4. `Writer`
5. `Experimenter`
6. `Analyst`

原因：

1. `Conductor + Researcher + Critic` 已足够形成文献与问题形成闭环
2. `Writer` 可以基于已有 artifact 产出阶段文稿
3. `Experimenter` 和 `Analyst` 依赖更重的执行层和结果层

## 11.3 每个角色的最低职责

### Conductor

- 任务拆解
- phase 规划
- skill 调度
- runtime policy 决策

### Researcher

- 文献搜索
- 论文解析
- 知识综合
- gap 与 hypothesis 形成

### Critic

- 审查相关工作
- 审查实验设计
- 审查结果论断

### Writer

- 章节写作
- 文稿组装
- 摘要重写

### Experimenter

- 设计实验
- 生成代码改动建议
- 组装运行包

### Analyst

- 规范化指标
- 对比 baseline
- 分析 hypothesis 支持情况

## 11.4 实施方式

角色第一版不要拥有复杂的独立 memory。

角色之间通过 artifact 协作即可：

- `Conductor` 生产路由决策
- `Researcher` 生产知识 artifact
- `Critic` 生产 critique artifact
- `Writer` 生产 manuscript artifact
- `Experimenter/Analyst` 生产实验 artifact

## 11.5 交付物

1. role policy 定义
2. role -> allowed skills 映射
3. critique/revise/pass 控制机制

## 11.6 验收标准

1. 角色之间边界清晰
2. skill 不因角色增加而重复实现
3. critique 可以打回上游，而不是直接修改底层状态

---

## 12. Phase 5：代码生成与实验执行闭环

## 12.1 目标

把系统从“研究建议生成器”推进到“可执行研究助手”。

## 12.2 分两步走

### Step A：Code Proposal

先支持：

- 代码草案生成
- patch 建议
- 配置文件生成
- 运行脚本生成

但不立即默认自动提交运行。

### Step B：Controlled Execution

再支持：

- 本地 runner
- SSH runner
- 运行日志收集
- 结果回写
- 失败状态回写

## 12.3 为什么不能一步做到全自动

因为代码生成和实验执行是整个系统里风险最高的一层：

1. 会接触真实代码库
2. 会消耗真实算力和预算
3. 会带来运行失败、环境漂移、数据污染等问题

所以这层必须是受控执行层，而不是开放式 agent 自由执行。

## 12.4 交付物

1. `generate_research_code`
2. `patch_existing_codebase`
3. `prepare_run_bundle`
4. `submit_experiment_run`
5. `ingest_experiment_results`

## 12.5 验收标准

1. 能生成可审阅的实验代码改动
2. 能以受控方式提交实验
3. 能把实验结果重新转成 artifact 返回上游

---

## 13. 建议的目录演进方案

以下是推荐的目标目录，不要求一次建齐：

```text
src/agent/
  core/
  executors/
  infra/
  plugins/
  providers/
  reviewers/        # 迁移期保留，作为 critique skill backend
  stages/           # 迁移期保留，作为 skill wrapper 的内部实现
  artifacts/        # 新增
  skills/           # 新增
  roles/            # 新增
  runtime/          # 新增
  graph.py          # 迁移期保留，最终降级为 legacy 兼容入口
```

## 13.1 目录职责与文件规划

### `artifacts/`

```text
artifacts/
  __init__.py
  base.py           # Artifact 基类、ArtifactMeta、序列化接口
  registry.py       # ArtifactRegistry：save / load / list / get_by_type
  schemas.py        # TopicBrief, SearchPlan, CorpusSnapshot, PaperNote,
                    #   RelatedWorkMatrix, GapMap, CritiqueReport 等 dataclass
  serializers.py    # JSON 序列化/反序列化，落盘到 run_outputs/<run_id>/artifacts/
```

### `skills/`

```text
skills/
  __init__.py
  contract.py       # SkillSpec dataclass、SkillResult dataclass
  registry.py       # SkillRegistry：register / invoke / list
  wrappers/
    __init__.py
    plan_research.py           # 包装 stages/planning.py
    search_literature.py       # 包装 stages/retrieval.py
    parse_paper_bundle.py      # 包装 stages/indexing.py
    extract_paper_notes.py     # 包装 stages/analysis.py
    build_related_work.py      # 包装 stages/synthesis.py
    design_experiment.py       # 包装 stages/experiments.py
    generate_report.py         # 包装 stages/reporting.py
    critique_retrieval.py      # 包装 reviewers/retrieval_reviewer.py
    critique_experiment.py     # 包装 reviewers/experiment_reviewer.py
    critique_claims.py         # 包装 reviewers/post_report_review.py
```

### `roles/`

```text
roles/
  __init__.py
  base.py           # RoleAgent 基类、RolePolicy dataclass
  conductor.py      # Conductor role：task decomposition、phase planning、skill routing
  researcher.py     # Researcher role：调用 literature skill 组
  critic.py         # Critic role：调用 critique skill 组、返回 pass/revise/block
```

### `runtime/`

```text
runtime/
  __init__.py
  orchestrator.py   # 主编排器：读取 Conductor 输出，调度 role → skill → artifact
  context.py        # RunContext：run_id、iteration、budget、控制信号
  checkpoint.py     # 基于 LangGraph checkpoint 的 resume 逻辑（复用，不重写）
  policy.py         # 重试策略、budget guard、HITL gate
```

## 13.2 当前模块的迁移原则

1. `stages/` 先保留
2. skill 第一版先包 stage
3. 后续再逐步把 stage 内逻辑内移到 skill implementation
4. `reviewers/` 第一版不消失，先作为 critique skill backend

## 13.3 3-Agent MVP 的明确边界

第一批只落：

- `Conductor`
- `Researcher`
- `Critic`

第一批只跑通：

- literature search
- paper parsing
- paper notes
- related work matrix
- gap analysis
- critique/revise

第一批明确不做：

- code generation
- experiment running
- result analysis
- full paper writing

---

## 14. 里程碑与优先级

## Milestone 1

目标：

- artifact schema 初版
- artifact 落盘
- run 结果携带 artifact

优先级：

`最高`

## Milestone 2

目标：

- skill contract
- skill registry
- 第一批 wrapper 技术跑通

优先级：

`最高`

## Milestone 3

目标：

- single orchestrator MVP
- 与现有 CLI 兼容

优先级：

`高`

## Milestone 4

目标：

- `Conductor + Researcher + Critic` literature review 闭环

优先级：

`高`

## Milestone 5

目标：

- `Writer`
- 阶段稿和成稿装配

优先级：

`中`

## Milestone 6

目标：

- `Experimenter + Analyst`
- code proposal
- controlled execution

优先级：

`中`

---

## 15. 测试与验收策略

## 15.1 测试分层

### 第一层：Artifact 测试

- schema 正确
- 可序列化
- 可恢复

### 第二层：Skill 测试

- 单 skill 输入输出稳定
- tool 权限正确
- validator 正常工作

### 第三层：Runtime 测试

- critique/revise/pass 路径正常
- resume 正常
- artifact 流转正常

### 第四层：Role 协作测试

- role 之间只通过 artifact 协作
- skill 调用权限符合策略

### 第五层：端到端场景测试

- topic -> literature -> plan -> report
- topic -> experiment spec -> run bundle -> result analysis

## 15.2 验收原则

每一个里程碑必须回答两个问题：

1. 这个阶段新增了什么主能力
2. 这个阶段是否减少了对旧 graph/state 的耦合

如果不能同时回答这两个问题，就说明该里程碑没有真正推进架构转型。

---

## 16. 主要风险与规避策略

## 16.1 风险一：skill 颗粒度过碎

问题：

把每个函数都做成 skill，会立刻失控。

策略：

以“完成一个完整研究动作”为 skill 颗粒度，而不是以函数颗粒度。

## 16.2 风险二：多 agent 早于 skill runtime

问题：

先上多 agent 会把复杂度放大。

策略：

先完成 `artifact + skill + single orchestrator`，再上角色化。

## 16.3 风险三：artifact 设计过重

问题：

如果一开始就引入复杂 lineage/versioning，会拖慢整个实施。

策略：

第一版只做运行时需要的最小字段。

## 16.4 风险四：旧 graph 与新 runtime 双轨过久

问题：

长期双轨会形成两套真相。

策略：

每个里程碑都要明确”旧路径减少了哪一部分职责”。具体退出计划如下：

| 阶段 | graph.py 状态 | 说明 |
|---|---|---|
| Phase 0–1 | 完全保留，默认入口 | 只加 artifact sidecar 输出 |
| Phase 2 | 节点内部改调 skill | graph 拓扑不变，但节点实现走 skill registry |
| Phase 3 | 新增 `--mode=os` 入口 | 新 runtime orchestrator 可独立运行 MVP 流程 |
| Phase 4 | `--mode=os` 成为默认 | `--mode=legacy` 保留但不再迭代 |
| Phase 5 | 移除 legacy 入口 | graph.py 归档或删除 |

每个阶段结束时，必须验证”旧 graph 入口和新 runtime 入口对同一 topic 产出一致的 artifact”。

## 16.6 风险六：artifact 与 state 双写不一致

问题：

Phase 1–2 期间，stage 同时写 ResearchState 和 artifact。如果两者不一致，下游消费方会拿到矛盾数据。

策略：

1. artifact 从 state 产出字段直接构造，不做二次加工。即 `artifact.payload = state_field`，保证同源。
2. 增加 assertion：stage 输出后校验 `artifact.payload` 与对应 state 字段一致。
3. 只有在 Phase 3 新 runtime 验证通过后，才允许后续节点停止消费 state 产出字段。

## 16.7 风险七：provider 适配面过大

问题：

如果一次要实现 OpenAI / Gemini / Claude 三家完整 provider adapter，改动面过大。

策略：

1. 第一版只实现 `GeminiProvider`（当前默认模型）
2. `OpenAIProvider` 可同步实现，因为当前已有 `OpenAIChatBackend`
3. `ClaudeProvider` 推迟到有实际需求时再加
4. provider adapter 的核心工作不是重写 SDK 调用，而是在现有 backend 之上加一层统一的 `generate_structured()` 接口

## 16.5 风险五：代码生成与执行层失控

问题：

这层最容易引入真实代价和真实故障。

策略：

先 code proposal，后 controlled execution，最后再考虑更高自治。

---

## 17. 各 Phase 的具体代码改动清单

### Phase 1 改动清单（Artifact 层）

需要新增的文件：

1. `src/agent/artifacts/__init__.py`
2. `src/agent/artifacts/base.py` — `Artifact` 基类 + `ArtifactMeta` dataclass
3. `src/agent/artifacts/schemas.py` — 7 个 artifact dataclass
4. `src/agent/artifacts/registry.py` — `ArtifactRegistry` 类
5. `src/agent/artifacts/serializers.py` — JSON 序列化

需要修改的文件：

1. `src/agent/stages/planning.py` — `run_planning()` 输出时附带 `TopicBrief` + `SearchPlan` artifact
2. `src/agent/stages/retrieval.py` — `run_retrieval()` 输出时附带 `CorpusSnapshot` artifact
3. `src/agent/stages/analysis.py` — `run_analysis()` 输出时附带 `PaperNote[]` artifact
4. `src/agent/stages/synthesis.py` — `run_synthesis()` 输出时附带 `RelatedWorkMatrix` + `GapMap` artifact
5. `src/agent/reviewers/retrieval_reviewer.py` — 输出时附带 `CritiqueReport` artifact

不动的文件：

- `graph.py`（拓扑和路由不变）
- `core/schemas.py`（ResearchState 保持原样）
- 所有 `executors/`、`providers/`、`plugins/`、`infra/`

### Phase 2 改动清单（Skill Runtime）

需要新增的文件：

1. `src/agent/skills/__init__.py`
2. `src/agent/skills/contract.py` — `SkillSpec` + `SkillResult` dataclass
3. `src/agent/skills/registry.py` — `SkillRegistry` 类
4. `src/agent/skills/wrappers/` — 10 个 wrapper 文件（见 13.1 节）

需要修改的文件：

1. `src/agent/graph.py` — 12 个节点函数内部改为调用 `skill_registry.invoke()`
2. `src/agent/plugins/bootstrap.py` — 启动时注册 skill

不动的文件：

- `stages/` 内部逻辑不动（skill wrapper 调用它们）
- `reviewers/` 内部逻辑不动
- `core/schemas.py`

### Phase 3 改动清单（Provider 适配）

需要新增的文件：

1. `src/agent/providers/llm_adapter.py` — `LLMProvider` Protocol + `ModelRequest` / `ModelResponse` dataclass
2. `src/agent/providers/gemini_adapter.py` — 包装 `GeminiChatBackend`
3. `src/agent/providers/openai_adapter.py` — 包装 `OpenAIChatBackend`

需要修改的文件：

1. `src/agent/providers/llm_provider.py` — `call_llm()` 内部改为走 `LLMProvider` adapter
2. `src/agent/stages/runtime.py` — `llm_call()` 改为消费新 adapter 接口

不动的文件：

- `plugins/llm/` — backend 实现不变
- `infra/llm/` — SDK wrapper 不变

### Phase 4 改动清单（3-Agent 编排）

需要新增的文件：

1. `src/agent/roles/__init__.py`
2. `src/agent/roles/base.py` — `RoleAgent` 基类
3. `src/agent/roles/conductor.py`
4. `src/agent/roles/researcher.py`
5. `src/agent/roles/critic.py`
6. `src/agent/runtime/__init__.py`
7. `src/agent/runtime/orchestrator.py` — 3-agent 编排循环
8. `src/agent/runtime/context.py` — `RunContext`
9. `src/agent/runtime/policy.py` — retry / budget / HITL

需要修改的文件：

1. CLI 入口文件 — 增加 `--mode=os` 参数

不动的文件：

- `graph.py`（保留为 `--mode=legacy`）
- 所有下层模块

---

## 18. 推荐的实施顺序

如果只按最小可行路线推进，建议顺序如下：

1. 落 `artifact schema`
2. 落 `artifact persistence`
3. 落 `skill contract`
4. 用 wrapper 把 `stages/reviewers` skill 化
5. 做 `single orchestrator MVP`
6. 上 `Conductor + Researcher + Critic`
7. 上 `Writer`
8. 上 `Experimenter + Analyst`
9. 最后接代码 patch 与受控实验执行

这条路线的优点是：

1. 每一步都能落地
2. 每一步都能测试
3. 每一步都不会要求你先把整个系统推倒

---

## 18. 一句话执行建议

不要把当前项目理解为“要从单 agent 升级到多 agent”。

更准确的理解应该是：

`先把当前项目升级成一个 artifact-driven skill runtime，再让多 agent 成为这个 runtime 上层的角色化协作机制。`

这才是从 `RAG Agent` 走向 `Research Operating System` 的可实施路径。
