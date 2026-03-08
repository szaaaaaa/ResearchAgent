# UI Requirements for ResearchAgent

## Goal

This document defines the configuration surface that should be exposed in a desktop or web UI for ResearchAgent.

The UI should let users run the agent without editing YAML files manually, while preserving the current security model:

- Secrets must not be stored in project config files.
- Secrets must not be written to snapshots, traces, or logs in plaintext.
- The UI must distinguish between saved project settings and one-off run overrides.

## Configuration Sources

The current system reads configuration from three places:

1. `configs/agent.yaml`
2. environment variables
3. CLI run-time overrides in `scripts/run_agent.py`

The UI should preserve the same model:

- Project settings: saved in a structured config file or internal settings store.
- Credentials: stored outside YAML, ideally in environment variables or an OS credential store.
- Run overrides: applied only to the current run, not persisted unless the user explicitly saves them.

## Security Rules

These rules are mandatory for the UI:

1. Do not save API keys, tokens, secrets, or passwords into `agent.yaml` or any exported plain config.
2. Only store secret references in config, such as `providers.llm.gemini_api_key_env` or `retrieval.openai_api_key_env`.
3. Validate user input before saving. Any config field whose key matches `api_key`, `token`, `secret`, `password`, `authorization`, `access_key`, `private_key`, or `client_secret` must be rejected as inline config.
4. Show secrets in the UI only as masked values.
5. Provide a credential test button that verifies presence and basic connectivity without writing the raw secret into logs.
6. Any config preview, export, run snapshot, trace preview, or support bundle must show redacted values only.

## Storage Model

The UI should manage three layers of state.

### 1. Credentials

Recommended storage:

- Windows Credential Manager for desktop UI, with optional sync into the current process environment.
- Fallback: set environment variables for the current process only.

Current environment variables used by the codebase:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `SERPAPI_API_KEY`
- `GOOGLE_CSE_API_KEY`
- `GOOGLE_CSE_CX`
- `BING_API_KEY`
- `GITHUB_TOKEN`

Config fields that reference env var names:

- `providers.llm.gemini_api_key_env`
- `retrieval.openai_api_key_env`

### 2. Saved Project Settings

Recommended storage:

- Primary: `configs/agent.yaml`
- Optional UI-side preset files: `configs/presets/*.yaml`

These settings describe the default behavior of the agent and should persist across sessions.

### 3. Run Overrides

Recommended storage:

- In-memory form state until the user clicks Run
- Optionally written into a run manifest without plaintext secrets

These settings correspond to current CLI overrides and should not modify the saved project profile unless the user explicitly chooses "Save as default".

## Required UI Structure

The UI should be organized into the following pages or tabs.

1. Run
2. Credentials and Models
3. Data Sources
4. Retrieval and Indexing
5. Research Strategy
6. Multimodal Ingest
7. Paths and Storage
8. Safety and Budget
9. Advanced

## Page-by-Page Field Inventory

### 1. Run

Purpose:

- Collect one-off run input
- Start, resume, and monitor runs

Fields:

- `topic`
- `resume_run_id`
- `output_dir`
- `language`
- `model`
- `max_iter`
- `papers_per_query`
- `sources`
- `no_web`
- `no_scrape`
- `verbose`

Behavior:

- `topic` and `resume_run_id` are mutually flexible, but at least one must be present.
- `resume_run_id` should switch the form into resume mode.
- The page should show effective config summary before run start.
- The page should show run log, stage status, output directory, and generated report path.

### 2. Credentials and Models

Purpose:

- Configure LLM provider selection
- Manage API credentials safely

Fields:

- `providers.llm.backend`
- `llm.model`
- `llm.temperature`
- `providers.llm.retries`
- `providers.llm.retry_backoff_sec`
- `providers.llm.gemini_api_key_env`
- `retrieval.openai_api_key_env`

Credential entries to manage:

- OpenAI API key
- Gemini API key
- Google API key
- SerpAPI key
- Google CSE API key
- Google CSE CX
- Bing API key
- GitHub token

Behavior:

- The UI should show whether each credential is missing, present, or verified.
- The UI should not require every key; only keys relevant to enabled providers should be required.
- Provider changes should update validation hints. For example, selecting `gemini_chat` should require `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

### 3. Data Sources

Purpose:

- Choose which academic and web sources are enabled
- Control source ordering and breadth

Fields:

- `providers.search.backend`
- `providers.search.academic_order`
- `providers.search.web_order`
- `providers.search.query_all_academic`
- `providers.search.query_all_web`
- `sources.arxiv.enabled`
- `sources.arxiv.max_results_per_query`
- `sources.arxiv.download_pdf`
- `sources.openalex.enabled`
- `sources.openalex.max_results_per_query`
- `sources.google_scholar.enabled`
- `sources.google_scholar.max_results_per_query`
- `sources.semantic_scholar.enabled`
- `sources.semantic_scholar.max_results_per_query`
- `sources.semantic_scholar.polite_delay_sec`
- `sources.semantic_scholar.max_retries`
- `sources.semantic_scholar.retry_backoff_sec`
- `sources.web.enabled`
- `sources.web.max_results_per_query`
- `sources.google_cse.enabled`
- `sources.bing.enabled`
- `sources.github.enabled`

Behavior:

- Ordering controls should support drag-and-drop or move up/down.
- Per-provider advanced settings should be hidden behind expanders by default.
- Source cards should show dependency badges. Example: Google CSE requires both `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX`.

### 4. Retrieval and Indexing

Purpose:

- Configure speed, cost, and retrieval quality

Fields:

- `retrieval.runtime_mode`
- `retrieval.embedding_backend`
- `retrieval.embedding_model`
- `retrieval.remote_embedding_model`
- `retrieval.hybrid`
- `retrieval.top_k`
- `retrieval.candidate_k`
- `retrieval.reranker_backend`
- `retrieval.reranker_model`
- `index.backend`
- `index.persist_dir`
- `index.collection_name`
- `index.web_collection_name`
- `index.chunk_size`
- `index.overlap`

Behavior:

- The UI should present `lite`, `standard`, and `heavy` as presets.
- Preset descriptions should explain the derived effects.
  - `lite`: prefer remote embedding, disable reranker by default, disable figure extraction by default, prefer `pymupdf_only`.
  - `standard`: balanced default.
  - `heavy`: higher-quality extraction and richer indexing defaults.
- If the user manually changes a preset-derived field, the UI should mark the mode as customized.

### 5. Research Strategy

Purpose:

- Control how the autonomous agent plans, searches, analyzes, and synthesizes

Fields:

- `agent.seed`
- `agent.max_iterations`
- `agent.papers_per_query`
- `agent.max_queries_per_iteration`
- `agent.top_k_for_analysis`
- `agent.language`
- `agent.report_max_sources`
- `agent.budget.max_research_questions`
- `agent.budget.max_sections`
- `agent.budget.max_references`
- `agent.source_ranking.core_min_a_ratio`
- `agent.source_ranking.background_max_c`
- `agent.source_ranking.max_per_venue`
- `agent.query_rewrite.min_per_rq`
- `agent.query_rewrite.max_per_rq`
- `agent.query_rewrite.max_total_queries`
- `agent.dynamic_retrieval.simple_query_academic`
- `agent.dynamic_retrieval.simple_query_pdf`
- `agent.dynamic_retrieval.simple_query_terms`
- `agent.dynamic_retrieval.deep_query_terms`
- `agent.memory.max_findings_for_context`
- `agent.memory.max_context_chars`
- `agent.evidence.min_per_rq`
- `agent.evidence.allow_graceful_degrade`
- `agent.claim_alignment.enabled`
- `agent.claim_alignment.min_rq_relevance`
- `agent.claim_alignment.anchor_terms_max`
- `agent.limits.analysis_web_content_max_chars`
- `agent.topic_filter.min_keyword_hits`
- `agent.topic_filter.min_anchor_hits`
- `agent.topic_filter.include_terms`
- `agent.topic_filter.block_terms`
- `agent.experiment_plan.enabled`
- `agent.experiment_plan.max_per_rq`
- `agent.experiment_plan.require_human_results`
- `agent.checkpointing.enabled`
- `agent.checkpointing.backend`
- `agent.checkpointing.sqlite_path`

Behavior:

- This page should have Basic and Advanced modes.
- Basic mode should show only high-impact knobs:
  - language
  - max iterations
  - papers per query
  - experiment plan enabled
  - max research questions
- Advanced mode should expose the full strategy surface.

### 6. Multimodal Ingest

Purpose:

- Configure PDF text extraction, LaTeX fetch, and figure understanding

Fields:

- `ingest.text_extraction`
- `ingest.latex.download_source`
- `ingest.latex.source_dir`
- `ingest.figure.enabled`
- `ingest.figure.image_dir`
- `ingest.figure.min_width`
- `ingest.figure.min_height`
- `ingest.figure.vlm_model`
- `ingest.figure.vlm_temperature`
- `ingest.figure.validation_min_entity_match`
- `fetch.source`
- `fetch.max_results`
- `fetch.download_pdf`
- `fetch.polite_delay_sec`

Behavior:

- `text_extraction` should be a dropdown:
  - `auto`
  - `latex_first`
  - `marker_only`
  - `pymupdf_only`
- Figure analysis controls should be hidden unless `ingest.figure.enabled` is enabled.
- The UI should warn when a selected mode depends on optional local packages that may be missing.

### 7. Paths and Storage

Purpose:

- Let the user control where data, indexes, outputs, and runtime state are stored

Fields:

- `project.data_dir`
- `paths.papers_dir`
- `paths.metadata_dir`
- `paths.indexes_dir`
- `paths.outputs_dir`
- `metadata_store.backend`
- `metadata_store.sqlite_path`
- `index.persist_dir`
- `ingest.latex.source_dir`
- `ingest.figure.image_dir`

Behavior:

- Use directory pickers and file pickers where appropriate.
- Show the expanded effective path, not only the templated expression.
- The UI should support "Reset to derived default" for fields like `${project.data_dir}/papers`.

### 8. Safety and Budget

Purpose:

- Prevent runaway cost, unsafe downloads, and unhealthy providers

Fields:

- `budget_guard.max_tokens`
- `budget_guard.max_api_calls`
- `budget_guard.max_wall_time_sec`
- `providers.search.circuit_breaker.enabled`
- `providers.search.circuit_breaker.failure_threshold`
- `providers.search.circuit_breaker.open_ttl_sec`
- `providers.search.circuit_breaker.half_open_probe_after_sec`
- `providers.search.circuit_breaker.sqlite_path`
- `sources.pdf_download.only_allowed_hosts`
- `sources.pdf_download.allowed_hosts`
- `sources.pdf_download.forbidden_host_ttl_sec`

Behavior:

- Budget fields should show cost-risk hints.
- Host allowlist editing should use a list editor with import/export support.
- Circuit breaker settings should display current health state in a future runtime view.

### 9. Advanced

Purpose:

- Expose raw configuration and power-user tools without making them part of the default workflow

Features:

- effective config preview
- redacted config preview
- import config
- export config
- save preset
- load preset
- show derived fields after normalization
- show environment variable references used by the current profile

Behavior:

- Secrets must remain redacted even in advanced preview mode.
- A diff view between saved config and current run overrides would be useful.

## Credentials Matrix

The UI should expose this dependency matrix so users know what to configure.

### LLM and VLM

- `providers.llm.backend = openai_chat`
  - requires `OPENAI_API_KEY`
- `providers.llm.backend = gemini_chat`
  - requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `ingest.figure.enabled = true` with Gemini captioning
  - requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`

### Embeddings and Reranking

- `retrieval.embedding_backend = openai_embedding`
  - requires `OPENAI_API_KEY` or the env var named by `retrieval.openai_api_key_env`
- `retrieval.embedding_backend = local_st`
  - no API key, but requires local model availability
- `retrieval.reranker_backend = local_crossencoder`
  - no API key, but requires local model availability

### Search Providers

- `sources.google_cse.enabled = true`
  - requires `GOOGLE_CSE_API_KEY`
  - requires `GOOGLE_CSE_CX`
- `sources.bing.enabled = true`
  - requires `BING_API_KEY`
- `sources.github.enabled = true`
  - requires `GITHUB_TOKEN`
- `SerpAPI` integration if enabled in code path
  - requires `SERPAPI_API_KEY`

## Validation Rules

The UI should implement validation before save and before run.

### Save-Time Validation

- reject inline secrets in config payload
- ensure numeric fields are within sane ranges
- ensure lists contain normalized strings
- ensure ordering lists contain unique values
- ensure required directories are not empty strings

### Run-Time Validation

- require `topic` or `resume_run_id`
- require credentials for enabled remote providers
- warn, not fail, for optional local dependencies when a fallback exists
- fail early when a selected provider is impossible to use in the current environment

### Cross-Field Validation

- `retrieval.candidate_k` should be greater than or equal to `retrieval.top_k`
- `agent.query_rewrite.min_per_rq` should be less than or equal to `agent.query_rewrite.max_per_rq`
- `agent.budget.max_references` should be greater than or equal to `agent.report_max_sources`
- if `sources.web.enabled = false`, hide or disable scrape-specific web options
- if `agent.experiment_plan.enabled = false`, disable experiment-only subfields

## Recommended UX Defaults

The UI should expose two experience levels.

### Simple Mode

Show only:

- topic
- model
- provider
- runtime mode
- language
- max iterations
- key source toggles
- experiment plan enabled
- output directory
- credential status

### Advanced Mode

Show the entire configuration surface, including:

- provider order
- retrieval internals
- topic filtering
- claim alignment
- evidence thresholds
- budget guard
- circuit breaker
- checkpointing
- PDF host allowlist

## Suggested Internal UI Model

The UI implementation should keep a structured internal model with three top-level objects.

### `credentials`

- contains secret values or handles
- never serialized into project config
- optionally synced into process env at run start

### `project_config`

- mirrors the normalized structure of `agent.yaml`
- safe to save after redaction validation

### `run_overrides`

- contains temporary overrides such as topic, resume run id, output dir, verbose flag, and temporary source selection

At run start, the UI should build:

1. normalized saved config
2. apply run overrides
3. inject credentials through environment
4. execute the run
5. show the redacted effective config in the UI

## Suggested First UI Milestone

A minimal but useful first release should support:

1. topic entry and run control
2. provider and model selection
3. credential management
4. source toggles
5. runtime mode selection
6. output directory selection
7. simple advanced drawer for max iterations and experiment plan
8. run log viewer
9. redacted effective config preview

This is enough to eliminate manual YAML editing for most users while staying aligned with the current architecture.

## Implementation Notes

- The UI should treat `agent.yaml` as the main editable profile for the autonomous agent workflow.
- The current codebase ships a single `agent.yaml` runtime config; any future alternate workflow should define its own explicit config surface instead of reviving `rag.yaml`.
- The UI should call the same normalization path used by the CLI before saving or running.
- The UI should never duplicate default logic that already exists in `src/agent/core/config.py`; instead it should either import that logic or mirror it through a backend service boundary.
- Any future remote UI or multi-user UI should replace process environment storage with a proper encrypted secret backend.
