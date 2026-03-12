# Dynamic Research OS 分阶段实施路线图
> 日期：2026-03-12
> 状态：Draft v1

## 1. 目的

本文档定义后续实现必须遵守的阶段划分。

从现在开始，Dynamic Research OS 的实现不再按“零散功能”推进，而是按固定阶段分批落地。

## 2. 执行规则

- 任意时刻只允许一个主阶段处于进行中状态
- 新阶段开始前，上一阶段必须达到明确的完成门槛
- 每个阶段都应形成独立的一批代码提交
- 每个阶段都必须带对应测试，而不是只写代码骨架
- 若某阶段被阻塞，应先记录阻塞点，不得直接跳到下一阶段主线实现

## 3. 阶段总表

| 阶段 | 名称 | 目标 | 主体代码范围 | 产出类型 |
| --- | --- | --- | --- | --- |
| Phase 0 | Contract 冻结 | 固定架构边界和核心 schema | 文档、contract 草案 | 已完成 |
| Phase 1 | Runtime 基础骨架 | 建立 `src/dynamic_os/` 基础包、contracts、roles、storage、skill 基础加载骨架 | `contracts/` `roles/` `skills/` `storage/` | 代码骨架 + 单测 |
| Phase 2 | Tool 系统与策略层 | 建立 MCP-first 的 tool discovery、ToolRegistry、模块化 ToolGateway、PolicyEngine | `tools/` `policy/` | 工具层 + 单测 |
| Phase 3 | Planner | 建立局部 DAG 规划、review 决策、termination、structured output 校验 | `planner/` | planner 核心 + 单测 |
| Phase 4 | Executor | 建立节点执行、observation、replan loop、事件流 | `executor/` | executor 核心 + 集成测试 |
| Phase 5 | Built-in Skills 迁移 | 把首批内置 skills 迁到新接口 | `skills/builtins/` | skills + 单测 |
| Phase 6 | API 与前端切换 | 把 `/api/run` 和前端运行页切到新 runtime | `app.py` `src/server/` `frontend/` | 可运行链路 |
| Phase 7 | 旧实现删除与收口 | 删除旧主链路，完成最终切换 | `src/agent/` 旧链路及测试 | 清理 + 验证 |

## 4. 各阶段严格范围

### Phase 0：Contract 冻结

状态：已完成

已固定内容：

- 6 角色模型
- `role -> skill -> tool`
- MCP-first 工具思想
- startup discovery
- 非热插拔
- planner / executor 分离
- reviewer 改为 planner 插入

Phase 0 之后，不再允许随意漂移这些决策。

### Phase 1：Runtime 基础骨架

目标：

- 建立新的代码主目录 `src/dynamic_os/`
- 固定 contracts
- 固定角色注册表
- 固定 skill 发现 / 加载 / 注册骨架
- 固定 storage 抽象

本阶段必须实现：

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

本阶段不做：

- planner LLM 调用
- executor 主循环
- MCP 调用
- 前端切换

完成门槛：

- 所有 contract 可导入
- skill 目录扫描可工作
- role allowlist 可校验
- 内存版 stores 可工作
- 本阶段单测通过

### Phase 2：Tool 系统与策略层

目标：

- 建立 MCP-first 工具系统
- 建立 ToolRegistry
- 建立模块化 ToolGateway
- 建立 PolicyEngine

本阶段必须实现：

- `tools/discovery.py`
- `tools/registry.py`
- `tools/gateway/mcp.py`
- `tools/gateway/llm.py`
- `tools/gateway/search.py`
- `tools/gateway/retrieval.py`
- `tools/gateway/exec.py`
- `tools/gateway/filesystem.py`
- `policy/engine.py`

本阶段不做：

- planner DAG 生成
- executor loop
- built-in skill 迁移

完成门槛：

- 启动时工具发现可工作
- ToolRegistry 能给出规范化工具视图
- ToolGateway 对外接口稳定
- policy 拒绝测试通过
- 明确不支持热插拔

### Phase 3：Planner

目标：

- 建立 planner 核心
- 建立局部 DAG structured output
- 建立 review 决策与 terminate 决策

本阶段必须实现：

- `planner/planner.py`
- `planner/prompts.py`
- `planner/meta_skills.py`
- planner schema 校验
- planner retry once 逻辑

本阶段不做：

- 真正执行 skill
- 主循环切换 API

完成门槛：

- planner 能输出合法局部 DAG
- planner 不能直接碰 raw tools
- reviewer 插入是可选行为
- planner 单测通过

### Phase 4：Executor

目标：

- 建立 executor 主循环
- 打通 `planner -> executor -> observation -> planner`
- 打通事件流

本阶段必须实现：

- `executor/executor.py`
- `executor/node_runner.py`
- ready 节点选择
- observation 生成
- SSE 事件发射

本阶段不做：

- 大规模 built-in skill 迁移
- 前端切换

完成门槛：

- mock skill 可跑完整闭环
- 失败时回 planner，而不是隐藏 fallback
- 事件流完整
- executor 集成测试通过

### Phase 5：Built-in Skills 迁移

目标：

- 将首批内置 skills 迁到新 skill 接口

首批建议：

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

完成门槛：

- 每个 skill 均包含 `skill.yaml` `skill.md` `run.py`
- 每个 skill 只通过 `ctx.tools` 调能力
- 内置 skill 单测通过
- 最小研究链路可跑通

### Phase 6：API 与前端切换

目标：

- `/api/run` 接入新 runtime
- 前端运行页反映真实动态路由

本阶段必须实现：

- `app.py` 或 `src/server/` 对接新 runtime
- CLI 入口切换
- 局部 DAG 视图
- skill / tool / observation / replan 时间线

完成门槛：

- API 主链路只进入新 runtime
- 前端不再暗示旧固定阶段
- UI 能展示 reviewer 插入与 policy block

### Phase 7：旧实现删除与收口

目标：

- 删除旧主链路
- 去掉兼容路径
- 完成最终切换

本阶段必须完成：

- 删除旧 orchestrator / router / graph
- 删除旧 stages / wrappers / reviewers
- 删除导入旧主链路的测试
- 验证新主链路不再依赖旧执行系统

完成门槛：

- 新运行时单一路径成立
- 不再存在旧 runtime 主入口依赖
- 无旧依赖不变量测试通过

## 5. 后续实施顺序

从现在开始，默认按以下顺序推进：

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7

除非文档被明确修改，否则不跨阶段主线开发。

## 6. 每阶段提交规则

每阶段至少应拆成以下几类提交：

- `contracts / registry / gateway` 类结构提交
- `runtime logic` 类实现提交
- `tests` 提交
- `docs` 同步提交

禁止做法：

- 一个 commit 混入多个阶段主线
- 先切 API 再补 runtime 核心
- 先改前端表现再补后端事件协议

## 7. 当前状态

当前推荐立即进入：

`Phase 1：Runtime 基础骨架`

原因：

- 架构边界已经固定
- phase roadmap 已明确
- 还没有新的 runtime 骨架代码
- 继续讨论高层设计的收益已经开始下降

## 8. 一句话规则

后续实现一律按阶段推进，先打 runtime 骨架，再打 tool 层，再打 planner/executor，再迁 skills，最后切 API 和删除旧实现。
