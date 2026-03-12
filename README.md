# ResearchAgent

ResearchAgent is a local-first autonomous research agent. It turns a topic into a structured, cited report through the dynamic `planner -> executor -> role -> skill -> tool` runtime.

## What remains in this repo

- `scripts/run_agent.py`: main autonomous agent entrypoint
- `scripts/build_index.py`: utility for building or refreshing the local Chroma index
- `src/dynamic_os/`: planner, executor, contracts, skills, tools, policy, and runtime
- `src/ingest/`: PDF/LaTeX parsing, chunking, figure extraction, indexing helpers
- `src/retrieval/`: embeddings, reranking, BM25 sidecar, Chroma retrieval
- `configs/agent.yaml`: single runtime config for the current codebase

Traditional single-shot RAG mode and its dedicated scripts/configs have been removed. Retrieval and indexing code is still present because the autonomous agent depends on it.

## Architecture

The main workflow is:

`planner -> executor -> role -> skill -> tool`

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
python -m scripts.build_index --papers_dir data/papers
```

## Project Layout

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
