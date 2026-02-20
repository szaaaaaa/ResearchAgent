# ResearchAgent 重构对照说明

## 1. 目的

本文档用于清晰说明：

1. 重构前后结构差异（目录、依赖方向、职责边界）。
2. 功能实现方式如何从“耦合实现”升级为“可替换实现”。
3. 每一项改造如何一一对应到具体文件与能力。

## 2. 架构对照（重构前 vs 重构后）

| 维度 | 重构前 | 重构后 | 对应实现 |
|---|---|---|---|
| 核心流程与外部依赖关系 | `nodes.py` 里直接调用外部模块/SDK，编排与实现耦合 | 编排只调用 provider 接口，外部实现下沉到 `plugins/infra` | `src/agent/nodes.py`, `src/agent/providers/*`, `src/agent/plugins/*`, `src/agent/infra/*` |
| 可替换能力边界 | 更换 LLM/搜索/检索常需要改核心逻辑 | 通过接口 + 工厂 + 注册表切换，核心流程不改 | `src/agent/core/interfaces.py`, `src/agent/core/factories.py`, `src/agent/plugins/registry.py` |
| 配置管理 | 默认值分散在代码中，部分 magic number 隐式存在 | 启动时统一 normalize，关键参数在 YAML 管理，CLI 可覆盖 | `src/agent/core/config.py`, `configs/agent.yaml`, `scripts/run_agent.py` |
| 状态契约 | `state` 与运行时临时字段存在隐式约定 | `ResearchState` 和记录类集中在 `core/schemas.py`，内部字段显式化 | `src/agent/core/schemas.py`, `src/agent/state.py` |
| 可观测性 | 主要是普通日志 | 节点级结构化事件 + run 级产物 | `src/agent/core/events.py`, `src/agent/graph.py`, `scripts/run_agent.py` |
| 可复现性 | run 元信息不完整 | `seed`、`git_commit_hash`、配置快照、指标、事件落盘 | `scripts/run_agent.py` |
| 测试策略 | 覆盖不成体系 | 合同测试 + 节点逻辑测试 + 运行时测试 + smoke | `tests/*`, `scripts/smoke_test.py` |

## 3. 目录结构对照

### 3.1 重构前（核心问题）

- `src/agent/graph.py`: 编排流程。
- `src/agent/nodes.py`: 既写业务逻辑，又直接触达检索/索引/外部依赖。
- `scripts/run_agent.py`: 运行入口，配置和产物管理较薄。
- 缺少清晰的 `core/plugins/infra` 分层。

### 3.2 重构后（当前结构）

- `app` 层（入口与装配）
  - `scripts/run_agent.py`
  - `scripts/smoke_test.py`
- `core` 层（稳定内核）
  - `src/agent/core/interfaces.py`
  - `src/agent/core/schemas.py`
  - `src/agent/core/factories.py`
  - `src/agent/core/config.py`
  - `src/agent/core/events.py`
- `providers` 层（节点调用门面）
  - `src/agent/providers/llm_provider.py`
  - `src/agent/providers/search_provider.py`
  - `src/agent/providers/retrieval_provider.py`
- `plugins` 层（可插拔后端）
  - `src/agent/plugins/registry.py`
  - `src/agent/plugins/bootstrap.py`
  - `src/agent/plugins/llm/openai_chat.py`
  - `src/agent/plugins/search/default_search.py`
  - `src/agent/plugins/retrieval/default_retriever.py`
- `infra` 层（外部能力适配）
  - `src/agent/infra/llm/openai_chat_client.py`
  - `src/agent/infra/search/sources.py`
  - `src/agent/infra/retrieval/chroma_retriever.py`
  - `src/agent/infra/indexing/chroma_indexing.py`

## 4. 功能实现升级（一一对应）

### 4.1 LLM 调用链升级

- 重构前：节点可能直接触达具体模型调用实现。
- 重构后：
  1. `nodes.py` -> `providers.call_llm`
  2. `llm_provider.py` -> `core.factories.create_llm_backend`
  3. 工厂按 `providers.llm.backend` 取插件实例
  4. 插件调用 `infra/llm/openai_chat_client.py`
- 升级收益：换模型后端只需新增插件 + 改 YAML。

### 4.2 搜索调用链升级

- 重构前：搜索源调用和路由策略混在节点逻辑中。
- 重构后：
  1. `nodes.py` -> `providers.fetch_candidates`
  2. `search_provider.py` -> `create_search_backend`
  3. `plugins/search/default_search.py` 聚合学术与网页结果
  4. 具体搜索 API 在 `infra/search/sources.py`
- 升级收益：更换搜索引擎不改 graph/node 主流程。

### 4.3 检索（retrieval）升级

- 重构前：分析节点直接 import 检索实现。
- 重构后：
  1. `nodes.py` -> `providers.retrieve_chunks`
  2. `retrieval_provider.py` -> `create_retriever_backend`
  3. `plugins/retrieval/default_retriever.py`
  4. `infra/retrieval/chroma_retriever.py`
- 升级收益：检索后端可插拔，分析节点不依赖具体检索库。

### 4.4 索引与运行跟踪升级

- 重构前：索引能力耦合在节点内部实现细节中。
- 重构后：`nodes.py` 通过 `infra/indexing/chroma_indexing.py` 调索引/分块/run docs 记录。
- 升级收益：索引基础设施替换时，影响集中在 infra。

### 4.5 配置与默认值升级

- 重构前：多个默认值散落在节点中（如阈值、预算、上下文截断）。
- 重构后：
  - 统一 normalize：`src/agent/core/config.py`
  - 配置落地：`configs/agent.yaml`
  - 启动注入：`scripts/run_agent.py`
- 升级收益：策略调参主要通过 YAML/CLI 完成。

### 4.6 状态契约升级

- 重构前：状态字段定义分散，内部字段有隐式约定。
- 重构后：
  - `core/schemas.py` 统一定义 `ResearchState/PaperRecord/WebResult/AnalysisResult/RunMetrics`。
  - `state.py` 仅做兼容导出。
- 升级收益：跨节点 I/O 更清晰，新增字段可控。

### 4.7 观测与复现升级

- 重构前：缺少节点级结构化事件和完整 run 元数据。
- 重构后：
  - 节点埋点：`node_start/node_end/node_error`
  - run 产物：`config.snapshot.yaml`、`run_meta.json`、`metrics.json`、`events.log`
  - 元信息：`seed`、`git_commit_hash`（可用时）
- 升级收益：定位问题和复现实验更直接。

## 5. 配置对照（关键项）

| 配置项 | 作用 | 当前位置 |
|---|---|---|
| `providers.llm.backend` | 选择 LLM 后端插件 | `configs/agent.yaml` |
| `providers.search.backend` | 选择搜索后端插件 | `configs/agent.yaml` |
| `providers.retrieval.backend` | 选择检索后端插件 | `configs/agent.yaml` |
| `agent.dynamic_retrieval.*` | 简单/深度查询路由策略 | `configs/agent.yaml` |
| `agent.source_ranking.*` | 报告证据分层策略 | `configs/agent.yaml` |
| `agent.limits.*` | 分析内容长度等限制 | `configs/agent.yaml` |
| `agent.seed` | 可复现随机种子 | `configs/agent.yaml` + CLI `--seed` |

## 6. 测试与质量保障

### 6.1 测试覆盖

- 配置归一化与校验：`tests/test_core_config.py`
- Schema 契约：`tests/test_core_schemas.py`
- 注册表与工厂/provider：`tests/test_registry.py`, `tests/test_factories_and_providers.py`, `tests/test_phase3_contracts.py`
- 节点逻辑与流程：`tests/test_nodes_helpers.py`, `tests/test_nodes_flow.py`
- 图编排与运行时：`tests/test_graph_runtime.py`, `tests/test_core_events.py`
- 运行工具函数：`tests/test_run_agent_utils.py`

### 6.2 Smoke

- `scripts/smoke_test.py` 使用 mock 后端跑通最小闭环。
- 在无 `langgraph` 场景下内置 fallback 图执行器，保证 smoke 可运行。

## 7. 验收结论

按本次重构目标，“结构解耦、可替换后端、配置驱动、可观测可复现、测试闭环”均已落地。

建议后续新增功能继续遵循：

1. 先定义 `core/interfaces` 与 `core/schemas`。
2. 实现放在 `infra`，可插拔入口放在 `plugins`。
3. 节点只通过 `providers` 调用外部能力。
4. 配置先入 YAML，再在 `core/config.py` normalize。
