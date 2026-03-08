# ResearchAgent

ResearchAgent is a local-first autonomous research agent. It turns a topic into a structured, cited report through a staged workflow built on LangGraph.

## What remains in this repo

- `scripts/run_agent.py`: main autonomous agent entrypoint
- `scripts/fetch_arxiv.py`: utility for fetching papers into the local data store
- `scripts/build_index.py`: utility for building or refreshing the local Chroma index
- `scripts/smoke_test.py`: mocked end-to-end smoke test
- `src/agent/`: orchestration, runtime, providers, plugins, reviewers, tracing
- `src/ingest/`: PDF/LaTeX parsing, chunking, figure extraction, indexing helpers
- `src/retrieval/`: embeddings, reranking, BM25 sidecar, Chroma retrieval
- `configs/agent.yaml`: single runtime config for the current codebase

Traditional single-shot RAG mode and its dedicated scripts/configs have been removed. Retrieval and indexing code is still present because the autonomous agent depends on it.

## Architecture

The main workflow is:

`plan -> fetch -> index -> analyze -> synthesize -> evaluate -> report`

Key properties:

- Multi-source search across academic and optional web providers
- Local or remote embeddings with optional reranking
- PDF and LaTeX ingest with figure extraction/captioning
- Budget guard, checkpointing, tracing, and reviewer gates
- Optional experiment-planning stage for ML/DL topics

## Quick Start

Install:

```bash
pip install -U pip
pip install -e .
```

Set one LLM key:

```bash
export OPENAI_API_KEY="sk-..."
# or
export GEMINI_API_KEY="AIza..."
```

Run the agent:

```bash
python -m scripts.run_agent --topic "retrieval augmented generation"
```

Utility scripts:

```bash
python -m scripts.fetch_arxiv --query "retrieval augmented generation" --max_results 10
python -m scripts.build_index --papers_dir data/papers
python -m scripts.smoke_test
```

## Project Layout

```text
ResearchAgent/
├── configs/
│   └── agent.yaml
├── scripts/
│   ├── run_agent.py
│   ├── fetch_arxiv.py
│   ├── build_index.py
│   ├── smoke_test.py
│   └── validate_run_outputs.py
├── src/
│   ├── agent/
│   ├── ingest/
│   ├── retrieval/
│   └── common/
├── tests/
├── docs/
├── data/
└── outputs/
```

## Outputs

Each agent run writes to `outputs/run_<timestamp>/` and typically includes:

- `research_report.md`
- `research_state.json`
- `events.log`
- `metrics.json`
- `run_meta.json`
- `trace.jsonl` and `trace_summary.json` when tracing is enabled

## Tests

Run the full suite:

```bash
pytest
```

Run a focused smoke set:

```bash
pytest tests/test_run_agent.py tests/test_stage_indexing.py tests/test_stage_analysis.py -q
```
