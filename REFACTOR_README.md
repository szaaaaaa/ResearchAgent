# ResearchAgent 重构 README

## 1. 重构目标

本次重构聚焦两个核心目标：

1. 可替换外部 API  
当后续更换大模型 API 或搜索引擎 API 时，只需要修改对应 provider 文件，不改核心编排逻辑。

2. 全量配置化  
模型、搜索、路径、阈值、超参数、策略开关全部通过 YAML 配置管理，代码中不再硬编码业务参数。


## 2. 设计原则（高层不变）

1. 单向依赖：业务逻辑只依赖抽象接口，不依赖具体实现。
2. 稳定内核 + 可插拔外壳：核心只做编排，变化点做插件。
3. 配置驱动：禁止硬编码路径、模型名、引擎名、阈值。
4. 数据与代码分离：run 产物、配置快照、日志可追溯。
5. 强 I/O 契约：模块间通信走 schema，不随意塞字段。
6. 可观测优先：每个节点必须输出结构化日志与关键指标。
7. 最小可替换面：新增功能应“加文件 + 注册 + 改配置”。
8. 失败可控：外部依赖必须超时、重试、降级，不破坏主骨架。


## 3. 目标架构与依赖方向

建议采用四层结构：

- `app/`: 入口与编排（CLI、LangGraph、pipeline 组装）
- `core/`: 稳定内核（interfaces、schemas、factories、runner、events）
- `plugins/`: 可插拔实现（llm、search、retriever、evaluator）
- `infra/`: 外部依赖封装（OpenAI 客户端、SerpAPI、文件系统、缓存）

依赖方向必须固定为：

`app -> core -> (plugins, infra)`  
`core` 禁止 import `plugins/infra` 的具体实现。


## 4. 在当前仓库的落地映射

### 4.1 当前痛点

- `src/agent/nodes.py` 里存在外部 API 直接调用与策略逻辑耦合。
- 部分默认值仍在代码里（如阈值、截断长度、路由词表）。
- 数据源分支以 `if source == ...` 方式扩展，新增来源改动面较大。

### 4.2 近期重构落点（最小改造）

先不推倒重来，采用增量迁移：

- 新增 `src/agent/core/interfaces.py`
- 新增 `src/agent/core/schemas.py`
- 新增 `src/agent/core/factories.py`
- 新增 `src/agent/plugins/registry.py`
- 新增 `src/agent/plugins/llm/*.py`
- 新增 `src/agent/plugins/search/*.py`
- 新增 `src/agent/infra/*`（SDK/HTTP 客户端薄封装）

`src/agent/graph.py` 保持主流程，`src/agent/nodes.py` 逐步改为只调用接口，不直接调用外部 SDK。


## 5. 核心接口约定（必须遵守）

所有可替换组件必须在 `core/interfaces.py` 定义抽象接口（Protocol/ABC）：

- `LLMClient`
- `AcademicSearchProvider`
- `WebSearchProvider`
- `Retriever`
- `Evaluator`
- `Tool`

模块间数据必须在 `core/schemas.py` 中定义（TypedDict/dataclass/pydantic）：

- `ResearchState`
- `PaperRecord`
- `WebResult`
- `AnalysisResult`
- `RunMetrics`

新增字段必须默认兼容，不破坏已有节点。


## 6. 注册与工厂机制

### 6.1 注册

所有插件在 `plugins/registry.py` 注册：

- `register_llm("openai_chat", OpenAIChatClient)`
- `register_search("serpapi_google", SerpApiGoogleSearch)`

### 6.2 工厂

`core/factories.py` 只根据配置实例化接口，不写 provider 细节。

### 6.3 新增组件流程

新增一个组件必须只需要这四步：

1. 在 `plugins/` 下新建实现文件。
2. 实现对应接口。
3. 在 registry 注册。
4. 在 `configs/agent.yaml` 里切换配置。

禁止为新增组件改核心 runner/graph 逻辑。


## 7. 配置规范（YAML Only）

所有可变参数必须进入 `configs/agent.yaml`，并支持 CLI override。

推荐新增配置块：

```yaml
providers:
  llm:
    backend: openai_chat
    timeout_sec: 60
    retries: 2
    retry_backoff_sec: 1.0
  search:
    academic_priority: [google_scholar, semantic_scholar, arxiv]
    web_priority: [google, duckduckgo]
    timeout_sec: 30
    retries: 2

agent:
  limits:
    web_content_max_chars: 15000
    report_max_sources: 40
```

说明：

- 代码里不应再出现 provider 名字常量（如 `openai`, `google_scholar`）。
- 代码里不应出现业务阈值 magic number（如 `15000`, `0.7`）。


## 8. 观测与可复现

每次运行必须生成独立 `run_dir`，至少包含：

- `config.snapshot.yaml`
- `run_meta.json`（时间、seed、git hash、provider 选择）
- `events.log`（节点 start/end、耗时、样本量）
- `metrics.json`（核心指标）
- 最终报告与中间状态


## 9. 错误处理基线

外部依赖调用必须具备：

- 超时：必须可配置
- 重试：次数与退避可配置
- 明确报错：日志可定位 provider、query、阶段
- 降级：主路径失败可切换备选 provider 或返回空结果，不崩核心编排


## 10. 禁止项（强制）

- 禁止在业务节点直接调用 `openai.*` / `requests.*` / 向量库 SDK。
- 禁止硬编码路径、模型名、搜索引擎、阈值、语言策略。
- 禁止函数隐式依赖全局变量（`API_KEY`, `MODEL_NAME`, `seed`）。
- 禁止在 state 中临时追加未声明字段。
- 禁止出现跨层反向依赖与循环 import。


## 11. 分阶段实施计划

### Phase 1（立即执行，低风险）

- 抽离 LLM gateway：节点统一走 `LLMClient` 接口。
- 抽离 Search gateway：`fetch_sources` 改为调用 search provider。
- 将现有 magic number 迁移到 YAML（保留兼容默认值）。

### Phase 2（结构稳定）

- 引入 registry + factory。
- 完成 `core/interfaces.py` 与 `core/schemas.py`。
- 新增 config 校验模块，启动时统一 normalize。

### Phase 3（质量补齐）

- 增加 smoke test（小样本 <30s）。
- 增加 provider 合约测试（每类插件至少 1 个）。
- 补 run_dir 元数据与结构化日志。


## 12. 验收标准

满足以下条件视为重构达标：

1. 切换 LLM provider 仅需改配置和 provider 文件。
2. 切换搜索 provider 仅需改配置和 provider 文件。
3. 调整策略与参数只改 YAML，不改核心业务代码。
4. 新增插件无需改 `graph` 主流程。
5. 端到端 smoke test 稳定通过。


## 13. 最小运行与验证建议

示例运行：

```bash
python -m scripts.run_agent --topic "RAG overview" --max_iter 1 --sources arxiv,web --no-scrape
```

建议新增：

- `scripts/smoke_test.py`：使用 mock provider 跑完整流程，保证在无外网环境也可验证骨架。

