# CLAUDE.md — ResearchAgent

## Project Overview

ResearchAgent is an autonomous multi-source research workflow engine powered by LangGraph. It decomposes research topics into questions, searches academic and web sources, indexes and analyzes findings, synthesizes results, and generates structured markdown reports with citations.

**Two modes:**
- **Autonomous Agent** (primary): Multi-iteration LangGraph workflow with planning, fetching, indexing, analysis, synthesis, and optional experiment planning (HITL)
- **Traditional RAG** (secondary): Simple fetch → parse → chunk → index → retrieve → answer pipeline

**Python 3.10+** (CI tests on 3.12). Package name: `research-agent`, version `0.2.0`.

## Quick Reference

```bash
# Install (dev mode)
pip install -e .

# Run autonomous agent
python -m scripts.run_agent --topic "retrieval augmented generation"

# Run tests
python -m unittest discover -s tests -v

# Smoke test (mocked providers, fast)
python -m scripts.smoke_test

# Validation gate
python -m scripts.validate_run_outputs \
  --state tests/fixtures/validation/pass_state.json \
  --report tests/fixtures/validation/pass_report.md \
  --strict --require-critic-pass
```

## Repository Structure

```
├── configs/
│   ├── agent.yaml              # Main agent config (~160 settings)
│   └── rag.yaml                # Traditional RAG config
├── docs/
│   └── experiment-suggestions-dev-guide.md
├── scripts/
│   ├── run_agent.py            # CLI entry point for autonomous agent
│   ├── smoke_test.py           # End-to-end smoke test (mocked)
│   ├── validate_run_outputs.py # Output validation gate
│   ├── fetch_arxiv.py          # arXiv fetching utility
│   ├── build_index.py          # Vector index building
│   ├── demo_query.py           # Single-query RAG demo
│   ├── run_mvp.py              # One-command traditional RAG
│   └── evaluate_rag.py         # RAG evaluation
├── src/
│   ├── agent/                  # Core autonomous agent system
│   │   ├── graph.py            # LangGraph orchestration (build_graph, run_research)
│   │   ├── nodes.py            # 9 node functions + 30+ helpers (~1600 LOC)
│   │   ├── state.py            # State schema export
│   │   ├── prompts.py          # All LLM prompt templates (~500 LOC)
│   │   └── core/               # Stable contracts & infrastructure
│   │       ├── interfaces.py   # Protocol definitions (LLMBackend, SearchBackend, etc.)
│   │       ├── schemas.py      # TypedDict state definitions (24 structs)
│   │       ├── config.py       # Config normalization & defaults
│   │       ├── events.py       # Structured JSONL event emission
│   │       ├── executor.py     # TaskRequest/TaskResult protocols
│   │       ├── executor_router.py  # Executor dispatch
│   │       ├── budget.py       # BudgetGuard (token/call/time limits)
│   │       ├── failure.py      # Failure classification (RETRY/SKIP/BACKOFF/ABORT)
│   │       ├── factories.py    # Backend creation from config
│   │       └── state_access.py # Namespace read/write helpers
│   ├── executors/              # Task executors (llm, search, retrieval, index)
│   ├── providers/              # Service gateways with retry & budget tracking
│   │   ├── llm_provider.py     # call_llm() — all LLM calls go through here
│   │   ├── search_provider.py  # fetch_candidates()
│   │   └── retrieval_provider.py # retrieve_chunks()
│   ├── plugins/                # Pluggable backend implementations
│   │   ├── registry.py         # Backend registration maps
│   │   ├── bootstrap.py        # Auto-loading on startup
│   │   ├── llm/                # OpenAI chat backend
│   │   ├── search/             # Multi-source search orchestration
│   │   └── retrieval/          # Chroma + reranking retrieval
│   ├── infra/                  # Thin adapters wrapping legacy modules
│   ├── ingest/                 # Data ingestion (fetchers, chunking, PDF, web)
│   ├── rag/                    # Legacy RAG pipeline (answerer, retriever)
│   ├── workflows/              # Standalone workflows (traditional_rag.py)
│   └── common/                 # Shared utilities (config, runtime, CLI, report)
├── tests/                      # 18 test files, ~2300 LOC
│   ├── fixtures/validation/    # Test fixtures (pass_state.json, pass_report.md)
│   └── test_*.py               # Unit & integration tests
├── pyproject.toml              # Package definition & dependencies
├── .github/workflows/ci.yml   # CI pipeline
└── .gitignore
```

## Architecture

### Layer Diagram

```
scripts/run_agent.py (CLI entry)
        │
        ▼
  graph.py (LangGraph orchestration)
        │
        ▼
  nodes.py (9 node functions)
        │
        ▼
  providers/ (call_llm, fetch_candidates, retrieve_chunks)
        │
        ▼
  plugins/ (backend implementations via registry)
        │
        ▼
  infra/ + ingest/ (external system adapters)
```

### Graph Topology

```
plan_research → fetch_sources → index_sources → analyze_sources
  → synthesize → recommend_experiments
    → [HITL: await_experiment_results → ingest_experiment_results]
  → evaluate_progress
    → [loop back to plan_research OR generate_report]
```

### Key Architectural Patterns

- **Protocol interfaces** (`src/agent/core/interfaces.py`): `LLMBackend`, `SearchBackend`, `RetrieverBackend` — contracts without inheritance
- **Plugin registry** (`src/plugins/registry.py`): Global dicts with register/get for backend discovery
- **Provider gateway**: Nodes call `call_llm()`, `fetch_candidates()`, `retrieve_chunks()` — never backends directly
- **Executor dispatch**: Nodes emit `TaskRequest` → router dispatches to matching executor → returns `TaskResult`
- **Namespace isolation**: State uses nested TypedDicts (research/planning/evidence/report) with flat fallback via `sget()`/`to_namespaced_update()`
- **BudgetGuard**: Enforces token, API call, and wall-time limits across the run
- **Failure classification**: Exceptions routed to RETRY/SKIP/BACKOFF/ABORT actions

## Configuration

Main config: `configs/agent.yaml` (~160 settings). Supports `${section.key}` variable expansion.

Key sections: `project`, `paths`, `fetch`, `index`, `retrieval`, `llm`, `providers`, `agent`, `sources`, `budget_guard`.

All config is normalized by `src/agent/core/config.py:normalize_and_validate_config()` which enforces schema, types, and defaults. Downstream code trusts the normalized structure.

CLI overrides: `--max_iter`, `--papers_per_query`, `--model`, `--language`, `--seed`, `--sources`, `--no-web`, `--no-scrape`, `-v`.

## Testing

**Run all tests:**
```bash
python -m unittest discover -s tests -v
```

**Test categories:**
- **Core contracts**: `test_core_config.py`, `test_core_schemas.py`, `test_core_events.py`, `test_phase3_contracts.py`
- **Executor/provider**: `test_executor.py`, `test_factories_and_providers.py`, `test_registry.py`
- **Graph/nodes**: `test_graph_runtime.py`, `test_nodes_flow.py`, `test_nodes_helpers.py`
- **Features**: `test_experiment_integration.py`, `test_experiment_prompts.py`, `test_recommend_experiments.py`
- **Infrastructure**: `test_budget_guard.py`, `test_failure_router.py`, `test_state_access.py`, `test_run_agent_utils.py`, `test_validate_run_outputs.py`

Tests use `unittest` (no pytest). External APIs are mocked. Fixtures live in `tests/fixtures/`.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR:
1. Setup Python 3.12
2. `pip install -e . --no-deps` + pyyaml + requests
3. Unit tests: `python -m unittest discover -s tests -v`
4. Smoke test: `python -m scripts.smoke_test`
5. Validation gate: `python -m scripts.validate_run_outputs --strict --require-critic-pass`

Timeout: 20 minutes.

## Code Conventions

- **Type hints everywhere**: `from __future__ import annotations`, TypedDict, Protocol, Literal
- **Google-style docstrings** on public functions
- **Synchronous code** throughout (no async/await); thread-safe with locks where needed
- **Absolute imports** from package root (`from src.agent.core.config import ...`)
- **Graceful degradation**: Optional dependency failures log warnings, don't crash
- **No hardcoded values**: All tuning knobs live in `configs/agent.yaml` and `src/agent/core/config.py` defaults
- **Section markers** (`# ── description ──`) used in large functions for readability
- **Naming**: Verb + object for functions (`call_llm`, `fetch_candidates`, `retrieve_chunks`)

## Key Dependencies

| Package | Purpose |
|---------|---------|
| langgraph | Graph orchestration |
| langchain-openai, langchain-core | LLM integration |
| openai | OpenAI API client |
| chromadb | Vector database |
| sentence-transformers | Embeddings |
| pymupdf | PDF parsing |
| feedparser | arXiv RSS parsing |
| duckduckgo-search | Web search |
| trafilatura | Web page scraping |
| beautifulsoup4 | HTML parsing |
| pyyaml | YAML config loading |
| requests | HTTP client |
| numpy | Numerical operations |

## Environment Variables

- `OPENAI_API_KEY` — Required for LLM calls (OpenAI models)
- API keys for optional search providers (Semantic Scholar, Bing, Google CSE) as configured

## Output Artifacts

Each run creates `outputs/run_<timestamp>/` containing:
- `config.snapshot.yaml` — Full config used
- `run_meta.json` — Run metadata
- `events.log` — Structured JSONL event log
- `metrics.json` — Quality metrics
- `research_report.md` — Final markdown report
- `research_state.json` — Full state export

## Common Tasks for AI Assistants

**Adding a new search source**: Implement `SearchBackend` protocol in `src/plugins/search/`, register in `src/plugins/registry.py`, add config keys to `configs/agent.yaml`, update `normalize_and_validate_config()`.

**Adding a new LLM backend**: Implement `LLMBackend` protocol in `src/plugins/llm/`, register in registry, reference by name in config.

**Modifying graph flow**: Edit `src/agent/graph.py` for topology changes, `src/agent/nodes.py` for node logic, `src/agent/prompts.py` for LLM prompt templates.

**Modifying config defaults**: Edit `src/agent/core/config.py` constants and normalization logic. Add corresponding YAML keys to `configs/agent.yaml`.

**Writing tests**: Use `unittest.TestCase`, mock external calls, follow existing patterns in `tests/`. Run the full suite before submitting.
