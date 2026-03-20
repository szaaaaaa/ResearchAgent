# Dynamic Research OS 技术改造与迁移方案
> 日期：2026-03-12
> 状态：Draft v1
> 分阶段实施路线图：[`docs/dynamic-research-os-phase-roadmap.md`](dynamic-research-os-phase-roadmap.md)

## 1. 目标

用新的 `planner` 主导运行时，彻底替换旧的固定阶段执行路径。

这次迁移是一次真正的切换，不是兼容层包装。目标系统保留 `planner + 6 roles`，但移除旧的硬编码工作流逻辑，替换为：

- 局部角色 `DAG` 规划
- 角色通过 `skills` 执行
- `skills` 通过 `tools` 执行
- `planner` 决定是否插入 `reviewer`
- 基于 `observation` 的重规划闭环

## 2. 硬约束

新运行时必须满足以下约束：

- 保留以下 6 个执行角色：
  - `conductor`
  - `researcher`
  - `experimenter`
  - `analyst`
  - `writer`
  - `reviewer`
- 在角色层动态路由
- 在工具层实际执行
- 采用局部规划，而不是全局一次性规划
- 保持 `planner` 与 `executor` 分离
- 只保留两类长期运行时约束：
  - 预算限制
  - 权限限制
- 不允许运行时覆盖配置
- 不允许危险命令和任意删除文件

## 3. 旧实现删除策略

迁移目标不允许依赖旧主执行链路。

新运行时稳定后，以下旧逻辑必须删除，而不是继续保留在兼容模式下：

- 旧 graph 主入口
- 旧 stage-based orchestration
- 旧硬编码角色执行分支
- 旧 mandatory critic 路径
- 旧 stage wrapper 执行路径

切换完成后计划删除的模块：

- [`src/agent/graph.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/graph.py)
- [`src/agent/runtime/orchestrator.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/runtime/orchestrator.py)
- [`src/agent/runtime/router.py`](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/runtime/router.py)
- 旧 `src/agent/stages/*`
- 旧 `src/agent/skills/wrappers/*`
- 旧 `src/agent/roles/*` 中的硬编码执行逻辑

可复用但需要迁移适配的底层能力包括：

- retrieval backend 实现
- ingest backend 实现
- provider adapter
- 通用 IO 工具

### 3.1 重写边界

运行时架构本身必须重写。以下层不允许继续复用旧系统实现：

- planner / executor 主控制流
- 角色路由与角色执行逻辑
- skill 的发现、注册、调用链路
- tool 的发现、注册表、网关结构
- 运行时 contract、事件 schema、策略执行层
- bootstrap、import 副作用注册、旧 provider gateway 路径

只允许在严格条件下复用最低层叶子实现：

- 复用代码必须被迁移或包裹到 `src/dynamic_os/` 新模块之后
- planner、executor、roles、skills 不得直接 import 旧模块
- 旧 registry、bootstrap、兼容入口不得继续存活
- 被复用的叶子代码只能算内部实现细节，不能继续构成架构依赖
- 对外公开模型仍然必须是 MCP-first discovery 和新的 runtime contracts

## 4. 目标架构

### 4.1 组件总览

建议将新运行时放入一个新的命名空间，例如：

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

### 4.2 核心组件

- `planner`
  - 读取用户请求、状态快照、artifacts、observations
  - 生成局部 `DAG`
  - 决定是否插入 `reviewer`
  - 决定是否终止任务

- `executor`
  - 执行 planner 生成的 ready 节点
  - 不自行修改 `DAG`
  - 产出 artifacts 与 observations

- `role registry`
  - 存储 6 个角色定义
  - 定义每个角色默认允许的 `skills`
  - 用角色规格替代旧的硬编码角色类

- `skill registry`
  - 发现内置与用户自定义 `skills`
  - 校验 `skill.yaml`
  - 加载 `run.py`
  - 检查角色适配关系

- `tool registry`
  - 在启动时发现已配置 `MCP` 服务暴露的工具能力
  - 存储规范化后的工具元数据
  - 向运行时能力视图暴露可用工具清单

- `tool gateway`
  - 提供统一工具执行层
  - 以多文件拆分实现，避免重新变成单文件大杂烩
  - 以 `MCP` 工具能力为优先，并接入允许的执行后端

- `policy engine`
  - 执行预算策略与权限策略
  - 阻止危险命令与受保护路径写入

- `artifact store`
  - 持久化正式输出，供下游节点使用

- `observation store`
  - 持久化执行阻塞、风险、不确定性、重规划上下文

## 5. 角色模型

6 个角色保留，但不再实现为 6 套完全不同的硬编码工作流分支。

相反，每个角色应变成一份运行时规格，包含：

- `role id`
- 角色提示词 / profile
- 默认允许的 `skills`
- 期望输入 `artifact` 类型
- 期望输出 `artifact` 类型

角色规格概念示例：

```yaml
id: researcher
description: 搜索、收集、阅读并结构化研究资料
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

## 6. 规划模型

### 6.1 局部规划

`planner` 每次只生成局部 `DAG`，通常为 `2-4` 个节点。

原因：

- 更便宜
- 更稳定
- 更适合在执行不确定性下快速重规划
- 更适合 observation 驱动的闭环

### 6.2 Planner 职责

`planner` 负责：

- 选择角色
- 选择执行顺序和依赖关系
- 从角色 allowlist 中选择节点允许的 `skills`
- 只通过 `skill` 路由能力，不直接选择原始 `tool`
- 决定是否插入 `reviewer`
- 决定是否终止
- 根据 `observation` 进行重规划

`planner` 不允许：

- 作为主运行路径直接执行底层工具
- 修改配置
- 绕过权限策略

## 7. 执行模型

运行时默认执行规则：

`planner -> executor -> role node -> skill -> tool`

`planner` 只选择角色节点和允许的 `skills`。具体工具选择发生在 `skill` 内部，并统一通过 `ToolGateway` 完成。

### 7.1 Executor 职责

- 接收 planner 生成的 `DAG`
- 找出当前 ready 节点
- 通过通用角色执行逻辑执行节点
- 收集 artifacts
- 收集 observations
- 在需要重规划时把控制权交还给 planner

### 7.2 失败处理

`executor` 不允许偷偷自愈出一条隐藏恢复路径。

当执行受阻时，必须：

- 记录发生了什么
- 记录已经尝试了什么
- 给出候选修复方案
- 推荐一个动作
- 把控制权交回 `planner`

## 8. 核心 Contract

### 8.1 RoutePlan Contract

`planner` 输出的局部 `DAG contract`：

```json
{
  "run_id": "run_123",
  "planning_iteration": 2,
  "horizon": 3,
  "nodes": [
    {
      "node_id": "node_research_1",
      "role": "researcher",
      "goal": "收集并提取与 retrieval planning 相关的高信号论文笔记",
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
    "先不插 reviewer，先确认检索质量。"
  ]
}
```

### 8.2 Observation Contract

`executor` 返回给 `planner` 的结构化汇报：

```json
{
  "node_id": "node_research_1",
  "role": "researcher",
  "status": "needs_replan",
  "error_type": "tool_failure",
  "what_happened": "主学术检索源连续返回 rate limit",
  "what_was_tried": ["retry_once", "fallback_source_attempt"],
  "suggested_options": ["switch_source", "narrow_query", "insert_reviewer"],
  "recommended_action": "switch_source",
  "produced_artifacts": ["artifact:SourceSet:ss_1"],
  "confidence": 0.62
}
```

### 8.3 Artifact Contract

正式可复用产物：

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

机器可读的 `skill manifest`：

```yaml
id: arxiv_search
name: Arxiv Search
version: 1.0.0
applicable_roles:
  - researcher
description: 搜索 arXiv 并返回标准化后的论文候选结果
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

## 9. Skill 包规范

系统必须从如下结构发现 `skill`：

```text
skills/
  <skill_id>/
    skill.yaml
    skill.md
    run.py
```

### 9.1 必需文件

- `skill.yaml`
  - 规范声明文件
- `skill.md`
  - 给 planner 和开发者阅读的说明文档
- `run.py`
  - 执行入口

### 9.2 必需字段

`skill.yaml` 至少必须包含：

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

### 9.3 用户自定义 Skill 规则

- 用户新增 `skill` 时必须声明 `applicable_roles`
- `planner` 只有在以下条件都满足时，才能选择某个 `skill`：
  - 该 `skill` 加载成功
  - 该 `skill` 属于该角色允许的范围
  - 该 `skill` 通过权限策略检查

## 10. Planner Meta-Skills

`reviewer` 的插入不能硬编码成运行时规则。

因此应提供给 `planner` 一组自己的元技能，例如：

- `build_local_dag`
- `replan_from_observation`
- `assess_review_need`
- `decide_termination`

这样 review 逻辑仍属于 `planner`，而不是重新回到硬编码流程。

## 11. Policy Engine

长期保留的运行时策略只有两类：

- 预算策略
- 权限策略

### 11.1 预算策略

至少应包含：

- 最大规划 / 执行迭代数
- 最大工具调用数
- 可选最大运行时长
- 可选最大模型预算

### 11.2 权限策略

至少应包含：

- 允许联网搜索
- 允许在权限范围内自主选择检索源
- 只允许在批准工作区内读写文件
- 允许沙箱执行
- 只允许访问显式批准的远端执行目标
- 拒绝危险命令
- 拒绝任意删除行为
- 拒绝覆盖配置

典型阻止命令示例：

- `rm -rf`
- `sudo`
- `su`
- PowerShell 中的破坏性删除等价命令
- 未经明确授权的破坏性 `git reset / checkout` 类命令

## 12. API 与前端改造

### 12.1 API

`/api/run` 可以保留外层入口路径，但内部必须切换到新运行时。

运行流应对外暴露：

- route plan 更新事件
- 节点状态变化
- `skill` 调用事件
- `tool` 调用事件
- 重规划事件
- `observation` 事件
- `artifact` 创建事件

### 12.2 前端

前端不应再展示旧的固定阶段图。

必须改成展示：

- 局部 `DAG`
- 角色节点状态
- 插入的 `reviewer` 节点
- `skill` 时间线
- `tool` 时间线
- `observation` 时间线
- `artifact` 面板

## 13. 建议目录结构

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

## 14. 迁移阶段

### Phase 0：冻结 Contract（已完成）

#### P0.1 设计决策

**Pydantic v2 作为合约层**

所有合约使用 `pydantic.BaseModel` 并启用严格校验。现有的 `TypedDict` 类型
schema（`core/schemas.py`）**不**复用到新运行时 — 它们在过渡期间仅供旧代码使用。

理由：
- 运行时校验 + 清晰错误信息
- JSON Schema 导出，供前端和 planner structured output 使用
- 默认不可变（`model_config = {"frozen": True}`）

**状态模型**

新运行时**没有单体 `ResearchState` dict**。状态由三个正交 store 组成：

| Store | 内容 | 访问方 |
|-------|------|--------|
| `ArtifactStore` | 正式版本化输出 | planner、executor、skills 可读 |
| `ObservationStore` | 执行反馈记录 | 仅 planner 可读 |
| `PlanStore` | 历史 RoutePlan | planner、executor 可读 |

Planner 通过读取这三个 store + 原始用户请求来构建新的局部 DAG。
Skill 只接收其声明的输入 artifact。

**Planner LLM 策略**

Planner 使用 **structured output**（JSON mode / function-calling）调用 LLM，
以 `RoutePlan` JSON Schema 作为输出 schema。

Planner prompt 模板接收：
- 用户请求
- 当前 artifact 摘要（type + id + producer，不含完整 payload）
- 最新 observation（如有）
- 可用角色及其允许的 skill
- 预算使用快照

Planner 产出 `RoutePlan` 对象，需通过 Pydantic 校验后 executor 才接受。

**Skill 执行接口**

Skill 是固定异步签名的 Python 可调用对象：

```python
async def run(ctx: SkillContext) -> SkillOutput
```

内置 skill（程序化注册）和用户自定义 skill（从 `skills/<id>/run.py` 发现）
共享同一接口。

**并发模型**

v1 中 executor **顺序**处理 ready 节点。无依赖边的节点按拓扑序执行但不并行。
这保持了实现简单，同时 DAG 结构已为未来版本保留了并行扩展空间。

**工具扩展模型**

工具在进程启动时从已配置的 `MCP` 服务中发现。运行时基于发现结果构建
`ToolRegistry`，并通过模块化的 `ToolGateway` 暴露统一调用入口。

v1 **不支持**运行时热插拔或热重载。新增或移除工具需要重启进程或显式 reload。

#### P0.2 合约：RoutePlan

Planner 产出此合约，executor 消费。

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

校验规则：

- 每个 `PlanEdge.source` 和 `PlanEdge.target` 必须引用 `nodes` 中存在的 `node_id`
- `edges` 构成的图必须是 DAG（无环）
- 每个节点的 `allowed_skills` 必须是该角色在角色注册表中 allowlist 的子集
- `horizon` 必须等于 `len(nodes)`

#### P0.3 合约：Observation

Executor 产出此合约，planner 消费。

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

#### P0.4 合约：ArtifactRecord

Skill 产出的正式可复用输出，存入 `ArtifactStore`。

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

已知 artifact 类型（v1）：

| Artifact 类型 | 产出角色 | 说明 |
|--------------|---------|------|
| `TopicBrief` | conductor | 拆解后的主题 + 范围 |
| `SearchPlan` | conductor | 研究问题 + 查询 + 路由 |
| `SourceSet` | researcher | 收集的论文 + 网页源记录 |
| `PaperNotes` | researcher | 按论文提取的分析笔记 |
| `EvidenceMap` | researcher, analyst | 证据-声明映射 |
| `GapMap` | researcher, analyst | 识别的研究空白 |
| `ExperimentPlan` | experimenter | 设计的实验规格 |
| `ExperimentResults` | experimenter | 原始实验运行结果 |
| `ExperimentAnalysis` | analyst | 解读的实验发现 |
| `PerformanceMetrics` | analyst | 汇总的指标摘要 |
| `ResearchReport` | writer | 最终交付文档 |
| `ReviewVerdict` | reviewer | 审查评估 + 问题 |

#### P0.5 合约：SkillSpec

机器可读的 skill manifest。每个 skill 包必须以 `skill.yaml` 提供。

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

#### P0.6 合约：RoleSpec

角色注册表条目，取代硬编码角色类。

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

默认角色注册表（v1）：

```yaml
- id: conductor
  description: 拆解任务、组织上下文、定义交接目标
  default_allowed_skills:
    - plan_research
  input_artifact_types: []
  output_artifact_types: [TopicBrief, SearchPlan]
  forbidden:
    - 不能替代 writer 写最终报告

- id: researcher
  description: 搜索、收集、阅读、整理研究资料
  default_allowed_skills:
    - search_papers
    - fetch_fulltext
    - extract_notes
    - build_evidence_map
  input_artifact_types: [TopicBrief, SearchPlan]
  output_artifact_types: [SourceSet, PaperNotes, EvidenceMap, GapMap]
  forbidden:
    - 不能充当最终成稿作者

- id: experimenter
  description: 设计并执行实验相关技能
  default_allowed_skills:
    - design_experiment
    - run_experiment
  input_artifact_types: [SearchPlan, EvidenceMap, GapMap]
  output_artifact_types: [ExperimentPlan, ExperimentResults]
  forbidden:
    - 不能接管通用文献综述主流程

- id: analyst
  description: 分析结果、比较证据、解释结果
  default_allowed_skills:
    - analyze_metrics
    - build_evidence_map
  input_artifact_types: [SourceSet, PaperNotes, ExperimentResults]
  output_artifact_types: [ExperimentAnalysis, PerformanceMetrics, EvidenceMap]
  forbidden:
    - 不能负责全局流程决策

- id: writer
  description: 根据已有产物生成最终交付物
  default_allowed_skills:
    - draft_report
  input_artifact_types: [EvidenceMap, ExperimentAnalysis, PerformanceMetrics]
  output_artifact_types: [ResearchReport]
  forbidden:
    - 不能偷偷补做上游研究

- id: reviewer
  description: 审查产物、指出问题、给出 verdict
  default_allowed_skills:
    - review_artifact
  input_artifact_types: [SourceSet, ExperimentPlan, ResearchReport]
  output_artifact_types: [ReviewVerdict]
  forbidden:
    - 不能直接重写产物
```

#### P0.7 Skill 执行接口

**SkillContext** — 运行时构建并传递给每次 skill 调用：

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

**SkillOutput** — 每个 skill 必须返回：

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

**执行入口** — 内置和用户自定义 skill 均实现：

```python
from dynamic_os.contracts.skill_io import SkillContext, SkillOutput

async def run(ctx: SkillContext) -> SkillOutput:
    ...
```

**现有 skill 迁移映射：**

| 旧 Wrapper（`skills/wrappers/`） | 新 Skill ID | 目标角色 |
|----------------------------------|-------------|---------|
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

#### P0.8 Planner Prompt 合约

系统提示词模板：

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

Structured output 策略：

Planner 调用使用 LLM provider 的 structured output / function-calling 模式，
以 `RoutePlan` JSON Schema 作为响应格式。原始 LLM 响应通过
`RoutePlan.model_validate_json()` 校验后才使用。

校验失败时，planner 将校验错误追加到 prompt 中重试一次。若第二次仍失败，
planner 产出 `error_type=llm_error` 的 Observation，系统终止运行。

#### P0.9 事件协议（SSE）

所有事件为 JSON 对象，通过现有 SSE 流发送。每个事件含 `type` 字段供前端分发。

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

#### P0.10 策略合约

**BudgetPolicy：**

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

**PermissionPolicy：**

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

#### P0.11 存储接口

**ArtifactStore：**

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

**ObservationStore：**

```python
from __future__ import annotations
from typing import Protocol

class ObservationStore(Protocol):
    def save(self, obs: Observation) -> None: ...
    def list_latest(self, n: int = 5) -> list[Observation]: ...
    def list_by_node(self, node_id: str) -> list[Observation]: ...
```

**PlanStore：**

```python
from __future__ import annotations
from typing import Protocol

class PlanStore(Protocol):
    def save(self, plan: RoutePlan) -> None: ...
    def get_latest(self) -> RoutePlan | None: ...
    def list_all(self) -> list[RoutePlan]: ...
```

#### P0.12 目标目录布局（已确认）

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
      events.py           # 所有 SSE 事件模型
      policy.py           # BudgetPolicy, PermissionPolicy
    planner/
      __init__.py
      planner.py          # Planner 类
      prompts.py          # planner prompt 模板
      meta_skills.py      # build_local_dag, assess_review_need 等
    executor/
      __init__.py
      executor.py         # Executor 类
      node_runner.py      # 单节点执行逻辑
    roles/
      __init__.py
      registry.py         # RoleRegistry，加载角色规格
      roles.yaml          # 默认角色定义
    skills/
      __init__.py
      registry.py         # SkillRegistry，发现 + 校验
      builtins/           # 内置 skill 包
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
      registry.py         # ToolRegistry，存放已发现的 MCP 工具元数据
      discovery.py        # 启动时 MCP 工具发现
      gateway/
        __init__.py
        mcp.py            # MCP 工具调用入口
        llm.py            # 面向 LLM 的工具门面
        search.py         # 搜索工具门面
        retrieval.py      # 检索与索引工具门面
        exec.py           # 沙箱与远端执行门面
        filesystem.py     # 文件系统门面
    policy/
      __init__.py
      engine.py           # PolicyEngine，预算 + 权限检查
    storage/
      __init__.py
      memory.py           # 所有 store 的内存实现
      # 未来：持久化后端
skills/                   # 用户自定义 skill（项目根目录）
```

#### P0.13 ToolGateway 公开 API

`ToolGateway` 是 skill 访问外部能力的**唯一**途径。内置和用户自定义 skill
使用相同的 API。任何 skill 不得直接 import 旧模块。

工具发现以 `MCP` 为优先。运行时在启动阶段发现已配置 `MCP` 服务提供的工具，
将其规范化写入 `ToolRegistry`，再通过 `ToolGateway` 对外暴露。`tool` 不会反向调用 `skill`。

```python
from __future__ import annotations
from typing import Any

class ToolGateway:
    """统一工具执行层，供所有 skill 使用。"""

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

所有内置 skill 必须通过 `ctx.tools.*` 调用，不得 import 内部模块。
这确保用户自定义 skill 拥有完全相同的能力。

#### P0.14 完全切断原则

本次迁移是**真正的切换**。新的运行时架构重建在 `src/dynamic_os/` 下，
`src/agent/` 不得继续出现在新的 planner / executor / role / skill / tool 主链路中。

迁移期间允许选择性迁移或包裹最低层叶子实现，但只能作为新模块背后的内部细节：

| 能力 | 旧模块（将被删除） | 新实现 |
|------|-------------------|--------|
| LLM 对话 | `plugins/llm/*`、`providers/*` | `dynamic_os/tools/gateway/llm.py` |
| 网页/学术搜索 | `plugins/search/*`、`infra/search/*` | `dynamic_os/tools/gateway/search.py` |
| 文档检索 | `plugins/retrieval/*`、`infra/retrieval/*` | `dynamic_os/tools/gateway/retrieval.py` |
| 文档索引 | `infra/indexing/*` | `dynamic_os/tools/gateway/retrieval.py` |
| 预算追踪 | `core/budget.py` | `dynamic_os/policy/engine.py` |
| 事件发射 | `core/events.py` | `dynamic_os/contracts/events.py` |
| Artifact 存储 | `artifacts/*` | `dynamic_os/storage/memory.py` |
| 角色定义 | `roles/*` | `dynamic_os/roles/registry.py` |
| Skill 注册 | `skills/*` | `dynamic_os/skills/registry.py` |
| 敏感信息脱敏 | `core/secret_redaction.py` | `dynamic_os/policy/redaction.py` |

### Phase 1：合约层 + Skill Runtime 基础层

实现任务：

- 创建 `src/dynamic_os/` 包结构（按 Phase 0 布局）
- 在 `contracts/` 下实现所有 Pydantic 合约模型
- 实现 `RoleRegistry`，从 `roles/roles.yaml` 加载
- 实现 `SkillRegistry`，含目录发现（`skills/<id>/`）与 `skill.yaml` 校验
- 实现 `SkillContext` / `SkillOutput` 运行时桥接
- 实现内存版 `ArtifactStore`、`ObservationStore`、`PlanStore`
- 编写合约校验测试（所有模型 round-trip、非法数据拒绝）
- 编写 skill 发现测试（合法包被找到、非法包被拒绝）
- 编写角色 allowlist 测试（allowlist 之外的 skill 分配被阻止）

交付物：

- 所有合约模型可从 `dynamic_os.contracts` 导入
- 可工作的 `SkillRegistry`，能发现和校验 skill 包
- 可工作的 `RoleRegistry`，含 6 个默认角色
- 内存存储层
- 以上所有组件的通过测试

### Phase 2：Policy Engine + Tool Gateway

实现任务：

- 实现 `PolicyEngine`，消费 `BudgetPolicy` 和 `PermissionPolicy`
- 从零实现 `BudgetPolicy` 执行逻辑
- 实现命令黑名单检查（模式匹配 `blocked_commands`）
- 实现受保护路径检查（glob 匹配 `blocked_path_patterns`）
- 实现启动时 `ToolRegistry`，发现已配置 `MCP` 服务暴露的工具能力
- 实现模块化 `ToolGateway`，公开 `llm_chat`、`search`、`retrieve`、`index`、`execute_code`、`read_file`、`write_file`
- 配置只读约束（policy engine 拒绝任何配置修改尝试）
- 编写权限拒绝测试（阻止命令、阻止路径、预算耗尽）

交付物：

- 能阻止危险操作的 `PolicyEngine`
- 含已发现 MCP 工具能力的 `ToolRegistry`
- 具备模块化内部结构的 `ToolGateway`
- 通过策略测试

### Phase 3：新 Planner

实现任务：

- 实现 `Planner` 类，从 store 读取数据并产出 `RoutePlan`
- 实现 planner prompt 模板（system prompt + 角色/skill/artifact/observation 上下文注入）
- 实现基于 `RoutePlan` JSON Schema 的 structured output 调用
- 实现 DAG 校验（node_id 引用、环检测、allowlist 约束）
- 实现校验失败重试一次的逻辑
- 实现 planner 元技能：`assess_review_need`、`decide_termination`
- 实现终止逻辑（planner 在目标满足时设 `terminate=true`）
- 编写 planner 输出 schema 测试（合法 plan 通过、非法 plan 拒绝）
- 编写 reviewer 插入测试（planner 可插入 reviewer，reviewer 非强制）

交付物：

- 能输出合法、经校验的局部 DAG 的 `Planner`
- planner 元技能可工作
- 通过 planner 单元测试

### Phase 4：新 Executor + 重规划闭环

实现任务：

- 实现 `Executor` 类，接收 `RoutePlan` 并执行 ready 节点
- 实现拓扑排序确定节点执行顺序
- 实现单节点执行：解析角色 → 选择 skill → 构建 `SkillContext` → 调用 `run()` → 收集 `SkillOutput`
- 实现成功、部分成功、失败三种情况的 `Observation` 生成
- 实现重规划触发：`failure_policy=replan` 时 executor 把控制权交还 planner
- 实现主循环：`planner → executor → observation → planner → ...`
- 实现每次节点执行前的预算检查
- 在每个步骤产出 SSE 事件（`plan_update`、`node_status`、`skill_invoke`、`observation`、`replan`、`artifact_created`）
- 编写 executor-observation-replan 闭环测试
- 编写预算耗尽终止测试

交付物：

- 能通过 skill 执行 contract 化角色节点的 `Executor`
- 完整的 planner-executor 闭环，含 observation 驱动的重规划
- SSE 事件产出可工作
- 通过集成测试

### Phase 5：内置 Skills 迁移

将现有 skill wrapper 迁移到新 `async def run(ctx) -> SkillOutput` 接口：

| 优先级 | Skill ID | 来源 Wrapper | 说明 |
|--------|---------|-------------|------|
| 1 | `plan_research` | `plan_research.py` | 通过 `ctx.tools` 重写 LLM 规划 |
| 1 | `search_papers` | `search_literature.py` | 通过 `ctx.tools.search()` 重写 |
| 1 | `fetch_fulltext` | `parse_paper_bundle.py` | 通过 `ctx.tools.retrieve()` 重写 |
| 1 | `extract_notes` | `extract_paper_notes.py` | 通过 `ctx.tools.index()` + `ctx.tools.llm_chat()` 重写 |
| 2 | `build_evidence_map` | `build_related_work.py` | LLM 综合分析 |
| 2 | `design_experiment` | `design_experiment.py` | LLM 生成 |
| 2 | `run_experiment` | `execute_experiment.py` | 沙箱执行 |
| 2 | `analyze_metrics` | `analyze_results.py` | LLM 分析 |
| 3 | `draft_report` | `generate_report.py` | LLM 写作 |
| 3 | `review_artifact` | `critique_*.py` | 合并 3 个 critique wrapper 为 1 个通用审查 skill |

每个迁移后的 skill 必须包含 `skill.yaml` + `skill.md` + `run.py`。

交付物：

- 10 个内置 skill 位于 `dynamic_os/skills/builtins/`
- 在新运行时上打通最小可用研究闭环
- 通过集成测试：用户请求 → planner → executor → artifacts → report

### Phase 6：API + 前端切换

实现任务：

- 将 `/api/run` 接入新 `dynamic_os` 运行时（保留外层路由）
- 将 CLI 入口（`scripts/run_agent.py`）接入新运行时
- 替换前端旧固定 route graph 为局部 DAG 可视化
- 实现前端组件：
  - 局部 DAG 视图 + 角色节点状态
  - skill 调用时间线
  - tool 调用时间线
  - observation + replan 时间线
  - artifact 面板
  - reviewer 插入节点高亮
  - 策略拒绝信息展示
- 前端 store 消费新 SSE 事件类型

交付物：

- `/api/run` 和 CLI 均只进入新运行时
- 前端如实反映动态运行时行为
- 前端不再引用旧固定 stage 流水线

### Phase 7：删除旧实现

删除以下模块及其测试：

- `src/agent/graph.py`
- `src/agent/nodes.py`
- `src/agent/state.py`
- `src/agent/runtime/orchestrator.py`
- `src/agent/runtime/router.py`
- `src/agent/runtime/context.py`（被 `SkillContext` 取代）
- `src/agent/runtime/policy.py`（被 `PolicyEngine` 取代）
- `src/agent/stages/*`
- `src/agent/skills/wrappers/*`
- `src/agent/skills/base.py`、`contract.py`、`registry.py`（被 `dynamic_os/contracts/` 和 `dynamic_os/skills/registry.py` 取代）
- `src/agent/roles/*`（被 `dynamic_os/roles/` 取代）
- `src/agent/reviewers/*`（被 `review_artifact` skill 取代）
- 旧测试：`test_app_model_catalogs.py`、`test_app_run_control.py` 以及所有导入已删除模块的测试

保留的模块（已在早期阶段适配）：

- `src/agent/plugins/*`
- `src/agent/infra/*`
- `src/agent/providers/*`
- `src/agent/artifacts/base.py`、`registry.py`（存储层内部使用）
- `src/agent/core/budget.py`、`events.py`、`secret_redaction.py`、`source_ranking.py`
- `src/agent/tracing/*`

交付物：

- 无旧执行路径的单一运行时代码库
- 所有测试通过，不导入已删除模块
- `git log` 确认干净删除

## 15. 测试策略

### 测试层次

| 层次 | 范围 | 所属阶段 |
|------|------|----------|
| 合约校验 | 所有 Pydantic 模型 round-trip、非法数据拒绝 | 1 |
| Skill 发现 | 合法包被找到、非法包被拒绝、allowlist 约束 | 1 |
| 策略拒绝 | 阻止命令、阻止路径、预算耗尽 | 2 |
| Planner 输出 schema | 合法 plan 通过、非法 plan 拒绝、DAG 校验 | 3 |
| Executor-observation-replan 闭环 | 含 mock skill 的完整闭环 | 4 |
| Skill 单元测试 | 每个内置 skill 产出正确 `SkillOutput` | 5 |
| 端到端集成 | 用户请求 → artifacts → report（新运行时） | 5 |
| 前端 SSE | 事件在 UI 正确渲染 | 6 |
| 无旧依赖不变量 | 新运行时不导入旧 `stages`、`graph`、`orchestrator` | 7 |

### 关键不变量测试

- `planner` 不能为角色分配 allowlist 之外的 `skill`
- `executor` 不能执行被阻止的命令
- 运行时不能覆盖配置
- `reviewer` 是可选且由 `planner` 插入
- 执行失败必须返回 `Observation`，不能静默 fallback
- 新主执行链路不得导入或调用旧 `stages`、`graph`、`orchestrator`
- Planner LLM 校验重试后仍失败必须终止运行（不能静默继续）
- 预算耗尽必须通过 `RunTerminateEvent` 终止运行

## 16. 切换标准

满足以下条件时，才算新运行时切换完成：

- `/api/run` 主执行路径只进入新运行时
- 主 CLI 执行路径只进入新运行时
- 旧 orchestration 路径被删除
- 代码库不再依赖旧工作流抽象
- 所有合约模型通过校验测试
- 完整研究闭环在新运行时上端到端跑通

## 17. 明确技术决策

这次迁移的目标不是一个通用的单智能体 `LLM + tools` 运行时。

它的目标是：

- 一个 `planner`
- 六个有边界的执行角色
- 一组可复用 `skills`
- 一个由 `tools` 驱动的执行层
- 由 `planner` 自己决定 `review` 与 `replan`

这就是本次替换后的目标架构。

## 18. 严格实现附录

本附录合并了原“严格代码落地指导”的核心约束。从现在开始，迁移方案本身同时承担架构说明和实现约束。

### 18.1 代码组织规则

- 新运行时主链路只能存在于 `src/dynamic_os/`
- 不允许在新运行时里继续扩展旧 `src/agent/` 主链路
- `ToolGateway` 必须是统一门面，但内部必须拆分到多个文件
- `skills` 必须拆成 `discovery / loader / registry`
- `tools` 必须拆成 `discovery / registry / gateway/*`

### 18.2 模块边界

- `planner` 只负责规划、重规划、review/terminate 决策
- `executor` 只负责执行 ready 节点、收集 `artifact` / `observation`
- `roles` 只保存角色规格，不得退化成 6 套硬编码流程
- `skills` 是唯一任务级扩展单元
- `tools` 是能力级扩展单元，不是第二套 workflow 系统

### 18.3 Skill 实现规则

- 每个 skill 必须包含 `skill.yaml`、`skill.md`、`run.py`
- 每个 skill 只能通过 `ctx.tools` 使用外部能力
- 不允许 skill 直接 import 旧运行时入口
- 不允许 skill 自己定义一套权限绕过逻辑
- 内置 skill 与用户 skill 应尽量遵循同一加载模型

### 18.4 Tool 实现规则

- 工具层必须 `MCP-first`
- v1 工具只允许在启动时发现
- 不支持运行时热插拔
- `tool` 不得反向调用 `skill`
- 不允许每个 skill 各自直连 MCP；统一通过 `ToolGateway`

### 18.5 依赖方向规则

必须保持以下依赖方向：

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

禁止：

- `planner -> raw tools`
- `tool -> skill`
- `contracts -> runtime logic`
- `src/dynamic_os/* -> src/agent/runtime/*`

### 18.6 配置与策略规则

- 配置必须在 run 启动时冻结成只读快照
- 运行时代码不得覆盖配置文件、`.env` 或 discovery 结果
- 权限与预算判断统一放在 `PolicyEngine`
- 不允许 skill 或 tool 私自绕过 policy

### 18.7 测试与 PR 门槛

未通过以下门槛，不得声称阶段完成：

- contract round-trip 测试
- skill discovery / manifest 校验测试
- role allowlist 测试
- MCP tool discovery / ToolRegistry 规范化测试
- ToolGateway 权限拒绝测试
- planner schema 测试
- executor-observation-replan 闭环测试
- 无旧依赖不变量测试

拒绝以下 PR：

- 继续往旧 `src/agent/` 主链路上加功能
- 在新 runtime 中偷接旧 bootstrap / registry
- 把 `ToolGateway` 做成单文件
- 把 skill 清单写成硬编码列表
- 没有 manifest 校验却声称支持即插即用
