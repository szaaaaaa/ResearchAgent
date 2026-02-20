# ResearchAgent 重构说明（最新）

## 1. 重构目标

本次重构目标：

1. 可替换外部能力：更换大模型、搜索、检索后端时，不改核心编排，只改 provider/plugin/config。
2. 配置驱动：策略、阈值、后端选择通过 YAML + CLI 管理。
3. 稳定内核：核心只负责编排与契约，外部依赖集中在 infra/plugins。
4. 可观测与可复现：每次运行可产出 run 元信息、结构化事件和指标。

## 2. 当前架构（已落地）

- `app`：`scripts/run_agent.py`、`scripts/smoke_test.py`
- `core`：`src/agent/core/interfaces.py`、`src/agent/core/schemas.py`、`src/agent/core/factories.py`、`src/agent/core/config.py`、`src/agent/core/events.py`
- `plugins`：`src/agent/plugins/llm/`、`src/agent/plugins/search/`、`src/agent/plugins/retrieval/`、`src/agent/plugins/registry.py`
- `infra`：`src/agent/infra/llm/`、`src/agent/infra/search/`、`src/agent/infra/retrieval/`、`src/agent/infra/indexing/`

## 3. 验收清单（逐条检查）

### 3.1 可替换后端

- `LLM/Search/Retrieval` 通过接口 + registry + factory 选择实现。
- 新增后端流程：新增插件文件 -> 注册 -> 改 YAML（无需改 graph 主流程）。
- 状态：已完成。

### 3.2 配置驱动

- `providers.llm/search/retrieval.backend` 已在 `configs/agent.yaml` 配置。
- 关键默认参数集中到 `core/config.py`，并在启动时 normalize。
- `run_agent` 支持 CLI 覆盖（含 `--seed`）。
- 状态：已完成。

### 3.3 状态与 Schema 契约

- `core/schemas.py` 已包含 `ResearchState/PaperRecord/WebResult/AnalysisResult/RunMetrics/SearchFetchResult`。
- 内部编排字段 `_cfg/_academic_queries/_web_queries` 已纳入契约定义。
- `state.py` 作为兼容导出层，统一指向 `core/schemas.py`。
- 状态：已完成。

### 3.4 可观测与可复现

- 运行目录产物：`config.snapshot.yaml`、`run_meta.json`、`metrics.json`、`events.log`、报告与状态文件。
- 节点级结构化事件：`node_start/node_end/node_error`。
- `run_meta` 包含 `seed` 与 `git_commit_hash`（可用时）。
- 状态：已完成。

### 3.5 测试

- 单测覆盖：配置、注册表、工厂/provider、节点辅助逻辑、节点流程、graph/runtime、events、schema、run_agent 工具函数。
- smoke：`scripts/smoke_test.py` 使用 mock provider，且支持无 `langgraph` 环境兜底执行。
- 状态：已完成。

## 4. 与原计划的对应关系

- Phase 1：LLM/Search gateway + 参数配置化（完成）
- Phase 2：registry/factory/interfaces/schemas/config normalize（完成）
- Phase 3：smoke + 合约测试 + run_dir 产物（完成）
- Phase 4：infra 层收敛、retrieval 插件化、结构化事件增强、可复现信息补齐（完成）

## 5. 最终结论

按本 README 的重构要求，当前版本已达成“重构完成”标准。

建议将后续新增能力统一按以下模式落地：

1. 新实现放入 `infra`（SDK/外部系统适配）与 `plugins`（可插拔后端）。
2. 只通过 `core/interfaces + core/factories + providers` 暴露给节点。
3. 所有新增策略参数先入 `configs/agent.yaml`，再在 `core/config.py` 做 normalize/校验。
4. 同步补最小单测与一条 smoke 路径。
