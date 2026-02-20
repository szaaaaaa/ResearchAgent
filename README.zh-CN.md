# ResearchAgent（中文说明）

ResearchAgent 是一个本地优先的研究工作流，支持两种运行模式：

1. 自主 Agent 模式（推荐）：规划 -> 抓取 -> 建索引 -> 分析 -> 综合 -> 生成报告
2. 传统 RAG 模式：抓取 -> 解析 -> 切分 -> 建索引 -> 检索 -> 生成回答

本文档重点说明：项目结构、环境配置、使用方法和快速入门。

## 项目结构

```text
ResearchAgent/
  configs/
    agent.yaml                 # Agent 运行配置
    rag.yaml                   # 传统 RAG 配置
    eval_samples.example.jsonl # 评测样本
  scripts/
    run_agent.py               # Agent 主入口
    smoke_test.py              # 端到端冒烟测试（mock provider）
    fetch_arxiv.py             # arXiv 抓取脚本
    build_index.py             # 构建本地向量索引
    demo_query.py              # 单轮 RAG 查询
    run_mvp.py                 # 一键传统 RAG 流程
    evaluate_rag.py            # RAG 评测
  src/
    agent/
      graph.py                 # LangGraph 编排
      nodes.py                 # 节点业务逻辑
      core/                    # 稳定契约/工厂/配置/事件
      providers/               # 服务网关层
      plugins/                 # 可插拔后端实现
      infra/                   # 外部集成适配层
    ingest/                    # 数据摄取工具
    rag/                       # 检索与回答链路
    workflows/                 # 传统/独立流程
    common/                    # 通用工具
  tests/                       # 单元与契约测试
  outputs/                     # 运行产物（报告/状态/指标）
  REFACTOR_README.md           # 重构映射与分阶段说明
```

## 环境配置

### 1. Python 版本

- Python >= 3.10
- 推荐 3.12

### 2. 安装依赖

```bash
pip install -U pip
pip install -e .
```

Conda 示例：

```bash
conda create -n research-agent python=3.12 -y
conda activate research-agent
pip install -U pip
pip install -e .
```

### 3. 配置 API Key

运行生成相关流程前请先设置 OpenAI Key。

PowerShell：

```powershell
$env:OPENAI_API_KEY="your_key"
```

Bash：

```bash
export OPENAI_API_KEY="your_key"
```

## 快速入门

### 1. 先跑冒烟测试

```bash
python -m scripts.smoke_test
```

该命令会使用 mock provider 验证整条 Agent 流程是否可运行。

### 2. 运行自主 Agent

```bash
python -m scripts.run_agent --topic "retrieval augmented generation"
```

常用参数示例：

```bash
python -m scripts.run_agent \
  --topic "LLM alignment techniques" \
  --max_iter 3 \
  --papers_per_query 5 \
  --model gpt-4.1-mini \
  --language en \
  --seed 42 \
  -v
```

数据源控制示例：

```bash
python -m scripts.run_agent --topic "RAG" --sources arxiv,web
python -m scripts.run_agent --topic "RAG" --no-web
python -m scripts.run_agent --topic "RAG" --no-scrape
```

### 3. 传统 RAG（可选）

```bash
python -m scripts.fetch_arxiv --query "retrieval augmented generation" --max_results 5
python -m scripts.build_index --papers_dir data/papers
python -m scripts.demo_query --query "Summarize key contributions with citations." --top_k 8
```

## 使用与输出

每次 Agent 运行会生成 `outputs/run_<timestamp>/`：

- `config.snapshot.yaml`
- `run_meta.json`
- `events.log`
- `metrics.json`
- `research_report.md`
- `research_state.json`

同时会在 `outputs/` 下生成便捷文件：

- `research_report_<timestamp>.md`
- `research_state_<timestamp>.json`

## 配置说明

主配置文件：`configs/agent.yaml`

关键配置块：

- `llm`：模型、温度
- `providers`：llm/search/retrieval 后端选择
- `agent`：迭代上限、语言、seed、路由/排序/记忆等限制
- `sources`：各数据源开关与抓取策略
- `index`：索引集合与切分参数
- `retrieval`：top_k、candidate_k、reranker

CLI 可覆盖常用字段（如 `--max_iter`、`--papers_per_query`、`--model`、`--language`、`--seed`）。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 常见问题

- `Missing OPENAI_API_KEY`
  - 先导出环境变量再运行。
- `ModuleNotFoundError`
  - 重新执行 `pip install -e .`。
- 网络超时
  - 检查代理、防火墙与外网连通性。
- 检索结果为空
  - 先构建索引并检查配置路径。
- 运行较慢
  - 使用 `--no-scrape`，并降低 `papers_per_query` 与迭代次数。

## 相关文档

- 英文文档：`README.md`
- 重构文档：`REFACTOR_README.md`
