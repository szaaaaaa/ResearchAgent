# ResearchAgent

ResearchAgent 是一个本地优先的自动研究 Agent。输入一个主题后，它会通过多阶段流程产出结构化、带引用的研究报告。

## 当前仓库保留的内容

- `scripts/run_agent.py`：主入口，运行自动研究 Agent
- `scripts/build_index.py`：构建或刷新本地 Chroma 索引
- `src/dynamic_os/`：planner、executor、contracts、skills、tools、policy 与 runtime
- `src/ingest/`：PDF/LaTeX 解析、切块、图像抽取、索引辅助
- `src/retrieval/`：embedding、reranker、BM25 sidecar、Chroma 检索
- `configs/agent.yaml`：当前唯一保留的运行配置

传统的单轮 RAG 模式、专用脚本和专用配置已经删除。检索与索引代码仍然保留，因为自动研究 Agent 本身依赖这些能力。

## 架构概览

主流程：

`planner -> executor -> role -> skill -> tool`

主要特性：

- 多源检索，支持学术源和可选网页源
- 支持本地或远程 embedding，以及可选 reranker
- 支持 PDF / LaTeX ingest、图像抽取和图像描述
- 带预算控制、checkpoint、trace、review gate
- 对 ML/DL 主题支持实验规划阶段

## 快速开始

安装依赖：

```bash
pip install -U pip
pip install -e .
```

设置一个 LLM Key：

```bash
export OPENAI_API_KEY="sk-..."
# 或
export GEMINI_API_KEY="AIza..."
```

运行 Agent：

```bash
python -m scripts.run_agent --topic "retrieval augmented generation"
```

辅助脚本：

```bash
python -m scripts.build_index --papers_dir data/papers
```

## 目录结构

```text
ResearchAgent/
├── configs/
│   └── agent.yaml
├── scripts/
│   ├── run_agent.py
│   ├── build_index.py
├── src/
│   ├── dynamic_os/
│   ├── ingest/
│   ├── retrieval/
│   └── common/
├── tests/
├── docs/
├── data/
└── outputs/
```

## 输出

每次 Agent 运行都会在 `outputs/run_<timestamp>/` 下生成一组产物，通常包括：

- `research_report.md`
- `research_state.json`
- `events.log`
- `metrics.json`
- `run_meta.json`
- 如果开启 tracing，还会有 `trace.jsonl` 和 `trace_summary.json`

## 测试

运行全部测试：

```bash
pytest
```

运行一组聚焦测试：

```bash
pytest tests/test_run_agent.py tests/test_stage_indexing.py tests/test_stage_analysis.py -q
```
