# ResearchAgent（中文说明）

一个自主、本地优先的研究 Agent，能将一个主题字符串转化为结构完整、带引用的研究报告。基于 [LangGraph](https://github.com/langchain-ai/langgraph) 编排，集多源检索、LLM 分析、证据追踪与迭代综合于一体，并针对 ML/DL 主题提供可选的人工介入（HITL）实验规划扩展。

---

## 目录

- [功能概览](#功能概览)
- [系统架构](#系统架构)
  - [Agent 图结构](#agent-图结构)
  - [分层设计](#分层设计)
  - [数据源](#数据源)
  - [LLM 后端](#llm-后端)
  - [状态 Schema](#状态-schema)
- [项目结构](#项目结构)
- [环境配置](#环境配置)
- [快速入门](#快速入门)
- [使用方法](#使用方法)
  - [自主 Agent 模式](#自主-agent-模式)
  - [传统 RAG 模式](#传统-rag-模式)
  - [实验蓝图（HITL）](#实验蓝图hitl)
- [配置参考](#配置参考)
- [运行输出](#运行输出)
- [测试](#测试)
- [常见问题](#常见问题)

---

## 功能概览

ResearchAgent 支持两种运行模式：

| 模式 | 流程 | 适用场景 |
|------|------|----------|
| **自主 Agent 模式**（推荐） | 规划 → 抓取 → 建索引 → 分析 → 综合 → 生成报告 | 深度、多轮迭代研究，含证据溯源 |
| **传统 RAG 模式** | 抓取 → 切分 → 建索引 → 检索 → 生成回答 | 对固定论文集的快速单轮问答 |

---

## 系统架构

### Agent 图结构

自主模式以 LangGraph 有向图编排，各节点关系如下：

```
                    ┌─────────────────┐
                    │  plan_research  │◄──────────────┐
                    └────────┬────────┘               │
                             │                        │ （循环继续）
                    ┌────────▼────────┐               │
                    │  fetch_sources  │               │
                    └────────┬────────┘               │
                             │                        │
                    ┌────────▼────────┐               │
                    │  index_sources  │               │
                    └────────┬────────┘               │
                             │                        │
                    ┌────────▼────────┐               │
                    │ analyze_sources │               │
                    └────────┬────────┘               │
                             │                        │
                    ┌────────▼────────┐               │
                    │   synthesize    │               │
                    └────────┬────────┘               │
                             │                        │
               ┌─────────────▼─────────────┐          │
               │  recommend_experiments    │          │
               └──┬────────────────────┬──┘          │
                  │（ML 主题）          │（其他主题）   │
     ┌────────────▼──────────┐         │              │
     │ ingest_experiment_    │         │              │
     │     results           │         │              │
     └────────┬──────────────┘         │              │
              │ 结果有效？             │              │
        ┌─────┴──────────────────────┐ │              │
        │    evaluate_progress       │◄┘              │
        └──────────────┬─────────────┘                │
                       │ 是否继续？                   │
              ┌────────┴────────┐                     │
              │（是）           │（否）                │
              └────────────────►│ generate_report │──►END
                                └─────────────────┘
```

每个节点都由 `instrument_node` 包裹，写入结构化事件到 `events.log`，并受全局 `BudgetGuard` 约束（令牌数、API 调用次数、运行时长上限）。

**各节点职责：**

| 节点 | 职责 |
|------|------|
| `plan_research` | 生成研究问题（RQ）、扩写检索查询、按来源路由查询 |
| `fetch_sources` | 并发抓取 arXiv / OpenAlex / Semantic Scholar / Web，下载 PDF |
| `index_sources` | 切分文本，写入 ChromaDB 向量索引，去重 |
| `analyze_sources` | LLM 逐源分析：摘要、关键发现、方法论、可信度、相关性 |
| `synthesize` | 跨源综合，更新 memory_summary，构建 claim_evidence_map |
| `recommend_experiments` | 检测是否为 ML/DL 领域，生成实验蓝图（数据集、环境、超参） |
| `ingest_experiment_results` | 接受人工注入的实验结果，验证并规范化 |
| `evaluate_progress` | 质量审计，决定是否再迭代或直接生成报告 |
| `generate_report` | 撰写最终 Markdown 报告，执行引用检查和 critic 修复 |

### 分层设计

```
src/agent/
├── graph.py              # LangGraph 图定义 + run_research() 入口
├── nodes.py              # 各节点业务逻辑
│
├── core/                 # 稳定契约层 —— 不依赖 plugins/infra
│   ├── schemas.py        # TypedDict 状态定义（ResearchState、PaperRecord 等）
│   ├── config.py         # 配置规范化、默认值与常量
│   ├── events.py         # 事件发射与节点插桩
│   ├── executor.py       # TaskRequest / 执行器抽象
│   ├── executor_router.py# 将任务分发到对应 provider 后端
│   ├── factories.py      # Provider 工厂（读配置 → 实例化插件）
│   ├── budget.py         # BudgetGuard：令牌 / API 调用 / 时长强制限制
│   ├── interfaces.py     # LLM / Search / Retrieval 抽象基类
│   ├── reference_utils.py# URL 规范化与引用去重
│   └── state_access.py   # 命名空间状态读写工具
│
├── providers/            # 薄网关层（每类服务一个文件）
│   ├── llm_provider.py
│   ├── search_provider.py
│   └── retrieval_provider.py
│
├── plugins/              # 可插拔后端实现
│   ├── registry.py       # @register_* 装饰器，用于动态插件发现
│   ├── bootstrap.py      # 启动时自动导入所有插件
│   ├── llm/
│   │   ├── openai_chat.py    # OpenAI Chat 后端
│   │   └── gemini_chat.py    # Google Gemini 后端
│   ├── search/
│   │   └── default_search.py # 多源扇出搜索
│   └── retrieval/
│       └── default_retriever.py  # ChromaDB 语义检索
│
└── infra/                # 外部集成适配层
    ├── llm/
    │   ├── openai_chat_client.py
    │   └── gemini_chat_client.py
    ├── search/
    │   └── sources.py    # arXiv、OpenAlex、Semantic Scholar、DuckDuckGo、Google、Bing、GitHub
    ├── retrieval/
    │   └── chroma_retriever.py
    └── indexing/
        └── chroma_indexing.py
```

**核心设计原则：**

- **稳定内核，可换外层。** `core/` 定义契约；`plugins/` 和 `infra/` 提供实现。新增 LLM 后端只需在 `plugins/llm/` 中新建文件并用 `@register_llm_backend` 注册。
- **命名空间状态。** `ResearchState` 分为 `planning`、`research`、`evidence`、`report` 四个子字典，避免跨迭代 key 冲突。
- **预算强制执行。** 所有 LLM 调用均经过 `BudgetGuard`，超出令牌、API 调用或时长上限时立即终止。
- **证据审计。** `claim_evidence_map` 与 `evidence_audit_log` 追踪每条声明对应的来源，报告生成前执行质量 critic 步骤。

### 数据源

| 数据源 | 类型 | 默认状态 | 配置键 |
|--------|------|----------|--------|
| arXiv | 学术论文 | ✅ 启用 | `sources.arxiv` |
| OpenAlex | 学术论文 | ✅ 启用 | `sources.openalex` |
| Semantic Scholar | 学术论文 | ✅ 启用 | `sources.semantic_scholar` |
| Google Scholar | 学术论文 | ❌ 禁用 | `sources.google_scholar` |
| DuckDuckGo | 网页 | ❌ 禁用 | `sources.web` |
| Google CSE | 网页 | ❌ 禁用 | `sources.google_cse` |
| Bing | 网页 | ❌ 禁用 | `sources.bing` |
| GitHub | 代码仓库 | ❌ 禁用 | `sources.github` |

学术查询按 `academic_order` 顺序扇出，网页查询按 `web_order` 顺序扇出。建索引前按 URL/标题去重。

### LLM 后端

| 后端 | 配置值 | 所需环境变量 |
|------|--------|-------------|
| OpenAI | `openai_chat` | `OPENAI_API_KEY` |
| Google Gemini | `gemini_chat` | `GEMINI_API_KEY` |

在 `configs/agent.yaml` 中切换后端：

```yaml
providers:
  llm:
    backend: gemini_chat       # 或 openai_chat
llm:
  model: gemini-2.0-flash      # 或 gpt-4.1-mini、gpt-4.1 等
```

### 状态 Schema

`ResearchState` 是一个分命名空间的 `TypedDict`：

```
ResearchState
├── topic, iteration, max_iterations, should_continue, run_id …
├── planning（规划命名空间）
│   ├── research_questions    # 本轮生成的研究问题
│   ├── search_queries        # 扩写后的检索查询
│   ├── query_routes          # 每条查询的来源路由决策
│   ├── _academic_queries     # 内部：路由到学术源的查询
│   └── _web_queries          # 内部：路由到网页源的查询
├── research（研究命名空间）
│   ├── papers                # List[PaperRecord]
│   ├── web_sources           # List[WebResult]
│   ├── indexed_paper_ids     # 已入库的去重 ID
│   ├── analyses              # List[AnalysisResult]（逐源 LLM 分析）
│   ├── findings              # 汇总关键发现
│   ├── synthesis             # 跨源综合文本
│   ├── memory_summary        # 跨迭代滚动摘要
│   ├── experiment_plan       # ExperimentPlan（仅 ML 主题）
│   └── experiment_results    # ExperimentResults（HITL 注入）
├── evidence（证据命名空间）
│   ├── claim_evidence_map    # 声明 → 支撑来源 UID
│   ├── evidence_audit_log    # 按研究问题的证据质量审计
│   └── gaps                  # 识别到的研究空白
└── report（报告命名空间）
    ├── report                # 最终 Markdown 报告
    ├── report_critic         # Critic 反馈字典
    ├── repair_attempted      # 是否触发了自动修复
    └── acceptance_metrics    # RunMetrics（a_ratio、覆盖率等）
```

---

## 项目结构

```
ResearchAgent/
├── configs/
│   ├── agent.yaml                  # 主 Agent 运行配置
│   ├── rag.yaml                    # 传统 RAG 配置
│   └── eval_samples.example.jsonl  # 评测样本集
├── scripts/
│   ├── run_agent.py                # 自主 Agent 主入口
│   ├── smoke_test.py               # 端到端冒烟测试（mock provider）
│   ├── fetch_arxiv.py              # 独立 arXiv 抓取脚本
│   ├── build_index.py              # 构建本地 ChromaDB 索引
│   ├── demo_query.py               # 单轮 RAG 查询演示
│   ├── run_mvp.py                  # 一键传统 RAG 流程
│   ├── evaluate_rag.py             # RAG 评测脚本
│   └── validate_run_outputs.py     # 验证输出产物
├── src/
│   ├── agent/                      # 自主 Agent（见架构部分）
│   ├── ingest/                     # 数据摄取工具
│   │   ├── fetchers.py             # PDF + 网页下载
│   │   ├── pdf_loader.py           # PDF 文本提取
│   │   ├── chunking.py             # 文本切分
│   │   ├── indexer.py              # 索引构建
│   │   └── web_fetcher.py          # 网页抓取
│   ├── rag/                        # 传统 RAG 流程
│   │   ├── retriever.py
│   │   └── answerer.py
│   ├── workflows/                  # 传统 / 独立流程
│   └── common/                     # 通用工具
│       ├── arg_utils.py
│       ├── cli_utils.py
│       ├── config_utils.py
│       ├── rag_config.py
│       ├── report_utils.py
│       └── runtime_utils.py
├── tests/                          # 单元与契约测试
├── data/                           # 本地数据（已 gitignore）
│   ├── papers/                     # 下载的 PDF
│   ├── metadata/                   # SQLite 元数据库
│   └── indexes/chroma/             # ChromaDB 向量索引
├── outputs/                        # Agent 运行产物
└── pyproject.toml / setup.cfg      # 包配置
```

---

## 环境配置

### 1. Python 版本

- Python >= 3.10（推荐 3.12）

### 2. 安装依赖

```bash
pip install -U pip
pip install -e .
```

使用 Conda：

```bash
conda create -n research-agent python=3.12 -y
conda activate research-agent
pip install -U pip
pip install -e .
```

### 3. 配置 API Key

**OpenAI 后端：**

```bash
# Bash
export OPENAI_API_KEY="sk-..."

# PowerShell
$env:OPENAI_API_KEY="sk-..."
```

**Gemini 后端：**

```bash
# Bash
export GEMINI_API_KEY="AIza..."

# PowerShell
$env:GEMINI_API_KEY="AIza..."
```

同时在 `configs/agent.yaml` 中设置 `providers.llm.backend: gemini_chat`。

---

## 快速入门

> **从零到第一份报告，约 5 分钟。**

### 第一步 — 确认 Python 版本

```bash
python --version   # 需要 3.10+，推荐 3.12
```

### 第二步 — 安装依赖

```bash
pip install -U pip
pip install -e .
```

### 第三步 — 配置 API Key

选择一个 LLM 后端：

**方案 A — OpenAI**（默认配置，开箱即用）：

```bash
export OPENAI_API_KEY="sk-..."          # Bash
# $env:OPENAI_API_KEY="sk-..."          # PowerShell
```

**方案 B — Google Gemini**（有免费额度）：

```bash
export GEMINI_API_KEY="AIza..."         # Bash
# $env:GEMINI_API_KEY="AIza..."         # PowerShell
```

使用 Gemini 时，还需在 `configs/agent.yaml` 中修改：

```yaml
providers:
  llm:
    backend: gemini_chat
llm:
  model: gemini-2.0-flash
```

### 第四步 — 验证安装（无需真实 API Key）

```bash
python -m scripts.smoke_test
```

全部通过即可继续。若有报错，请参考[常见问题](#常见问题)。

### 第五步 — 运行第一次研究

```bash
python -m scripts.run_agent --topic "retrieval augmented generation"
```

Agent 会自动完成以下步骤：
1. 生成研究问题和检索查询
2. 从 arXiv、OpenAlex、Semantic Scholar 抓取论文
3. 建立向量索引并逐源分析
4. 跨源综合，多轮迭代
5. 输出带引用的完整研究报告

### 第六步 — 查看报告

```
outputs/
├── research_report_<timestamp>.md   ← 打开这个
└── run_<timestamp>/
    ├── research_report.md
    ├── metrics.json
    └── events.log
```

用任意 Markdown 阅读器打开 `outputs/research_report_<timestamp>.md`。

---

**提速技巧（首次运行推荐）：**

```bash
# 更快：减少论文数，只跑一轮
python -m scripts.run_agent --topic "RAG" --max_iter 1 --papers_per_query 3 --no-scrape

# 生成中文报告
python -m scripts.run_agent --topic "检索增强生成" --language zh
```

---

## 使用方法

### 自主 Agent 模式

```bash
python -m scripts.run_agent --topic "主题" [选项]
```

**常用参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--topic TEXT` | 必填 | 研究主题或问题 |
| `--max_iter N` | 3 | 最大研究迭代次数 |
| `--papers_per_query N` | 5 | 每条查询抓取的论文数 |
| `--model NAME` | 配置文件 | LLM 模型名称 |
| `--language en\|zh` | en | 报告输出语言 |
| `--seed N` | 42 | 随机种子（可复现） |
| `-v` | 关闭 | 详细日志输出 |

**数据源控制：**

```bash
# 仅使用学术源（arXiv + OpenAlex）
python -m scripts.run_agent --topic "RAG" --sources arxiv,openalex

# 禁用网页抓取（更快）
python -m scripts.run_agent --topic "RAG" --no-scrape

# 禁用所有网页来源
python -m scripts.run_agent --topic "RAG" --no-web
```

**完整示例：**

```bash
python -m scripts.run_agent \
  --topic "大语言模型对齐技术" \
  --max_iter 3 \
  --papers_per_query 5 \
  --model gpt-4.1-mini \
  --language zh \
  --seed 42 \
  -v
```

### 传统 RAG 模式

分步执行：

```bash
# 1. 抓取论文
python -m scripts.fetch_arxiv --query "retrieval augmented generation" --max_results 10

# 2. 构建向量索引
python -m scripts.build_index --papers_dir data/papers

# 3. 查询
python -m scripts.demo_query --query "关键贡献是什么？" --top_k 8
```

一键执行：

```bash
python -m scripts.run_mvp --query "retrieval augmented generation"
```

### 实验蓝图（HITL）

针对 ML/DL/CV/NLP/RL 主题，Agent 自动生成 `experiment_plan` 章节，包含：

- 推荐数据集（含许可证和下载链接）
- 代码框架与环境规格（Python/CUDA/PyTorch 版本）
- 超参数基线与搜索空间
- 评估协议（指标、训练/评估命令）

**开启人工结果等待（`require_human_results: true`）：**

```yaml
# configs/agent.yaml
agent:
  experiment_plan:
    enabled: true
    max_per_rq: 2
    require_human_results: true
```

运行会在 `ingest_experiment_results` 节点暂停（返回 `END`），等待人工注入实验结果。将实验结果写入已保存的 state 后，重新触发图即可继续。

**不等待人工结果（默认）：**

```yaml
agent:
  experiment_plan:
    require_human_results: false
```

Agent 生成实验蓝图后直接进入 `evaluate_progress`，最终报告包含 `Experimental Blueprint` 章节。

---

## 配置参考

主配置文件：**`configs/agent.yaml`**

```yaml
llm:
  model: gemini-2.0-flash   # LLM 模型名
  temperature: 0.3

providers:
  llm:
    backend: gemini_chat    # openai_chat | gemini_chat
    retries: 1
  search:
    backend: default_search
    academic_order: [openalex, semantic_scholar, google_scholar]
    web_order: [duckduckgo]
    query_all_academic: false  # true = 扇出到所有学术源
  retrieval:
    backend: default_retriever

agent:
  seed: 42
  max_iterations: 3
  papers_per_query: 5
  max_queries_per_iteration: 3
  top_k_for_analysis: 12
  language: en               # en | zh
  report_max_sources: 80

  budget:
    max_research_questions: 3  # 最大研究问题数
    max_sections: 7            # 报告最大章节数
    max_references: 60         # 最大引用数

  source_ranking:
    core_min_a_ratio: 0.9    # A 级来源证据占比下限
    background_max_c: 0      # 最大 C 级（低质量）来源数

  query_rewrite:
    min_per_rq: 6            # 每个研究问题最少生成查询数
    max_per_rq: 8

  memory:
    max_findings_for_context: 40
    max_context_chars: 7000

  evidence:
    min_per_rq: 2            # 每个研究问题所需最少证据条目
    allow_graceful_degrade: true

  experiment_plan:
    enabled: true
    max_per_rq: 2
    require_human_results: false

sources:
  arxiv:
    enabled: true
    max_results_per_query: 6
  openalex:
    enabled: true
    max_results_per_query: 6
  semantic_scholar:
    enabled: true
    max_results_per_query: 5
  web:
    enabled: false           # 设为 true 启用网页来源
    scrape_pages: true
    scrape_max_chars: 30000

index:
  backend: chroma
  collection_name: papers
  chunk_size: 1200           # 切分块大小（字符数）
  overlap: 200               # 块间重叠

retrieval:
  top_k: 10
  candidate_k: 30
  reranker_model: BAAI/bge-reranker-base

budget_guard:
  max_tokens: 5000000        # 最大 token 消耗
  max_api_calls: 1500        # 最大 API 调用次数
  max_wall_time_sec: 7200    # 最大运行时长（秒）
```

---

## 运行输出

每次 Agent 运行会在 `outputs/run_<timestamp>/` 下生成：

| 文件 | 说明 |
|------|------|
| `research_report.md` | 最终研究报告（Markdown 格式） |
| `research_state.json` | 完整运行状态（所有论文、分析、发现等） |
| `events.log` | 结构化事件日志（每行一个 JSON） |
| `metrics.json` | 质量指标（证据比例、覆盖率、critic 问题） |
| `config.snapshot.yaml` | 本次运行实际生效的配置快照 |
| `run_meta.json` | 运行 ID、时间戳、主题、迭代次数 |

同时在 `outputs/` 下生成便捷副本：

- `research_report_<timestamp>.md`
- `research_state_<timestamp>.json`

---

## 测试

```bash
# 运行所有测试
python -m unittest discover -s tests -v

# 冒烟测试（无需 API Key）
python -m scripts.smoke_test

# 验证某次运行的输出产物
python -m scripts.validate_run_outputs outputs/run_<timestamp>/
```

---

## 常见问题

| 错误 | 解决方案 |
|------|----------|
| `Missing OPENAI_API_KEY` | `export OPENAI_API_KEY="sk-..."` |
| `Missing GEMINI_API_KEY` | 使用 `gemini_chat` 后端时，设置 `export GEMINI_API_KEY="AIza..."` |
| `ModuleNotFoundError` | 重新执行 `pip install -e .` |
| 网络超时 / 连接错误 | 检查代理、防火墙和外网连通性 |
| 检索结果为空 | 先构建索引：`python -m scripts.build_index` |
| 运行较慢 | 使用 `--no-scrape`，降低 `--papers_per_query` 和 `--max_iter` |
| 报告缺少引用 | 提高 `evidence.min_per_rq` 或增加数据源 |

---

## 相关文档

- 英文文档：[`README.md`](README.md)
- 重构文档：[`REFACTOR_README.md`](REFACTOR_README.md)
