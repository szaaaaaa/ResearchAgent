import React, { createContext, useContext, useEffect, useState } from 'react';
import { AgentRoleId, AppState, Credentials, ProjectConfig, RunOverrides } from './types';

export const API_BASE = window.location.port === '3000' ? 'http://localhost:8000' : '';

const LLM_BACKEND_BY_PROVIDER: Record<string, string> = {
  openai: 'openai_chat',
  gemini: 'gemini_chat',
};

const defaultCredentials: Credentials = {
  OPENAI_API_KEY: '',
  GEMINI_API_KEY: '',
  GOOGLE_API_KEY: '',
  SERPAPI_API_KEY: '',
  GOOGLE_CSE_API_KEY: '',
  GOOGLE_CSE_CX: '',
  BING_API_KEY: '',
  GITHUB_TOKEN: '',
};

const defaultProjectConfig: ProjectConfig = {
  providers: {
    llm: {
      backend: 'openai_chat',
      retries: 3,
      retry_backoff_sec: 2,
      gemini_api_key_env: 'GEMINI_API_KEY',
    },
    search: {
      backend: 'hybrid',
      academic_order: ['arxiv', 'semantic_scholar'],
      web_order: ['google_cse', 'bing'],
      query_all_academic: false,
      query_all_web: false,
      circuit_breaker: {
        enabled: true,
        failure_threshold: 5,
        open_ttl_sec: 60,
        half_open_probe_after_sec: 30,
        sqlite_path: '${project.data_dir}/circuit_breaker.db',
      },
    },
  },
  llm: {
    provider: 'openai',
    model: 'gpt-4o',
    temperature: 0.2,
    role_models: {
      conductor: { provider: 'openai', model: 'gpt-5.4' },
      researcher: { provider: 'gemini', model: 'gemini-3-pro-preview' },
      critic: { provider: 'openai', model: 'gpt-5.4' },
    },
  },
  retrieval: {
    openai_api_key_env: 'OPENAI_API_KEY',
    runtime_mode: 'standard',
    embedding_backend: 'openai_embedding',
    embedding_model: 'text-embedding-3-small',
    remote_embedding_model: 'text-embedding-3-small',
    hybrid: true,
    top_k: 10,
    candidate_k: 50,
    reranker_backend: 'local_crossencoder',
    reranker_model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
  },
  sources: {
    arxiv: { enabled: true, max_results_per_query: 10, download_pdf: true },
    openalex: { enabled: false, max_results_per_query: 10 },
    google_scholar: { enabled: false, max_results_per_query: 10 },
    semantic_scholar: {
      enabled: true,
      max_results_per_query: 10,
      polite_delay_sec: 1,
      max_retries: 3,
      retry_backoff_sec: 2,
    },
    web: { enabled: true, max_results_per_query: 10 },
    google_cse: { enabled: false },
    bing: { enabled: false },
    github: { enabled: false },
    pdf_download: { only_allowed_hosts: false, allowed_hosts: [], forbidden_host_ttl_sec: 86400 },
  },
  index: {
    backend: 'chroma',
    persist_dir: '${project.data_dir}/indexes',
    collection_name: 'papers',
    web_collection_name: 'web',
    chunk_size: 1000,
    overlap: 200,
  },
  agent: {
    seed: 42,
    max_iterations: 5,
    papers_per_query: 5,
    max_queries_per_iteration: 3,
    top_k_for_analysis: 10,
    language: 'zh',
    report_max_sources: 20,
    budget: { max_research_questions: 3, max_sections: 5, max_references: 30 },
    source_ranking: { core_min_a_ratio: 0.5, background_max_c: 0.3, max_per_venue: 5 },
    query_rewrite: { min_per_rq: 1, max_per_rq: 3, max_total_queries: 10 },
    dynamic_retrieval: {
      simple_query_academic: true,
      simple_query_pdf: true,
      simple_query_terms: 3,
      deep_query_terms: 5,
    },
    memory: { max_findings_for_context: 20, max_context_chars: 10000 },
    evidence: { min_per_rq: 2, allow_graceful_degrade: true },
    claim_alignment: { enabled: true, min_rq_relevance: 0.5, anchor_terms_max: 5 },
    limits: { analysis_web_content_max_chars: 20000 },
    topic_filter: { min_keyword_hits: 1, min_anchor_hits: 1, include_terms: [], block_terms: [] },
    experiment_plan: { enabled: false, max_per_rq: 2, require_human_results: false },
    checkpointing: { enabled: true, backend: 'sqlite', sqlite_path: '${project.data_dir}/checkpoints.db' },
  },
  ingest: {
    text_extraction: 'auto',
    latex: { download_source: false, source_dir: '${project.data_dir}/latex' },
    figure: {
      enabled: false,
      image_dir: '${project.data_dir}/figures',
      min_width: 200,
      min_height: 200,
      vlm_model: 'gemini-1.5-flash',
      vlm_temperature: 0.1,
      validation_min_entity_match: 1,
    },
  },
  fetch: {
    source: 'arxiv',
    max_results: 10,
    download_pdf: true,
    polite_delay_sec: 1,
  },
  project: { data_dir: './data' },
  paths: {
    papers_dir: '${project.data_dir}/papers',
    metadata_dir: '${project.data_dir}/metadata',
    indexes_dir: '${project.data_dir}/indexes',
    outputs_dir: '${project.data_dir}/outputs',
  },
  metadata_store: { backend: 'sqlite', sqlite_path: '${project.data_dir}/metadata.db' },
  budget_guard: { max_tokens: 1000000, max_api_calls: 1000, max_wall_time_sec: 3600 },
};

const defaultRunOverrides: RunOverrides = {
  topic: '',
  resume_run_id: '',
  mode: 'os',
  output_dir: './outputs',
  language: 'zh',
  model: 'gpt-4o',
  max_iter: 5,
  papers_per_query: 5,
  sources: ['arxiv', 'semantic_scholar', 'web'],
  no_web: false,
  no_scrape: false,
  verbose: false,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function mergeDeep<T>(base: T, incoming: unknown): T {
  if (!isRecord(base) || !isRecord(incoming)) {
    return (incoming === undefined ? base : incoming) as T;
  }

  const merged: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(incoming)) {
    const current = merged[key];
    if (Array.isArray(value)) {
      merged[key] = [...value];
    } else if (isRecord(current) && isRecord(value)) {
      merged[key] = mergeDeep(current, value);
    } else {
      merged[key] = value;
    }
  }
  return merged as T;
}

function updateNestedValue(config: ProjectConfig, path: string, value: unknown): ProjectConfig {
  const nextConfig = structuredClone(config);
  const keys = path.split('.');
  let current: Record<string, unknown> = nextConfig as unknown as Record<string, unknown>;
  for (let index = 0; index < keys.length - 1; index += 1) {
    current = current[keys[index]] as Record<string, unknown>;
  }
  current[keys[keys.length - 1]] = value;
  return nextConfig;
}

interface AppContextType {
  state: AppState;
  updateCredentials: (updates: Partial<Credentials>) => void;
  saveCredentials: () => Promise<void>;
  updateProjectConfig: (path: string, value: unknown) => void;
  setGlobalLlmProvider: (provider: string) => void;
  updateRoleModel: (roleId: AgentRoleId, updates: Partial<ProjectConfig['llm']['role_models'][AgentRoleId]>) => void;
  updateRunOverrides: (updates: Partial<RunOverrides>) => void;
  toggleAdvancedMode: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AppState>({
    credentials: defaultCredentials,
    projectConfig: defaultProjectConfig,
    runOverrides: defaultRunOverrides,
    isAdvancedMode: false,
  });

  useEffect(() => {
    fetch(`${API_BASE}/api/config`)
      .then((res) => res.json())
      .then((data) => {
        if (!data || Object.keys(data).length === 0) {
          return;
        }
        setState((prev) => ({
          ...prev,
          projectConfig: mergeDeep(defaultProjectConfig, data),
        }));
      })
      .catch((err) => console.error('Failed to load config', err));

    fetch(`${API_BASE}/api/credentials`)
      .then((res) => res.json())
      .then((data) => {
        if (!data || Object.keys(data).length === 0) {
          return;
        }
        setState((prev) => ({
          ...prev,
          credentials: { ...defaultCredentials, ...(data as Partial<Credentials>) },
        }));
      })
      .catch((err) => console.error('Failed to load credentials', err));
  }, []);

  const saveConfigToBackend = async (newConfig: ProjectConfig) => {
    await fetch(`${API_BASE}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newConfig),
    });
  };

  const updateCredentials = (updates: Partial<Credentials>) => {
    setState((prev) => ({ ...prev, credentials: { ...prev.credentials, ...updates } }));
  };

  const saveCredentials = async () => {
    await fetch(`${API_BASE}/api/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.credentials),
    });
  };

  const updateProjectConfig = (path: string, value: unknown) => {
    const nextConfig = updateNestedValue(state.projectConfig, path, value);
    setState((prev) => ({ ...prev, projectConfig: nextConfig }));
    void saveConfigToBackend(nextConfig).catch((err) => console.error('Failed to save config', err));
  };

  const setGlobalLlmProvider = (provider: string) => {
    const nextConfig = structuredClone(state.projectConfig);
    nextConfig.llm.provider = provider;
    nextConfig.providers.llm.backend = LLM_BACKEND_BY_PROVIDER[provider] ?? nextConfig.providers.llm.backend;
    setState((prev) => ({ ...prev, projectConfig: nextConfig }));
    void saveConfigToBackend(nextConfig).catch((err) => console.error('Failed to save config', err));
  };

  const updateRoleModel = (
    roleId: AgentRoleId,
    updates: Partial<ProjectConfig['llm']['role_models'][AgentRoleId]>,
  ) => {
    const nextConfig = structuredClone(state.projectConfig);
    nextConfig.llm.role_models[roleId] = {
      ...nextConfig.llm.role_models[roleId],
      ...updates,
    };
    setState((prev) => ({ ...prev, projectConfig: nextConfig }));
    void saveConfigToBackend(nextConfig).catch((err) => console.error('Failed to save config', err));
  };

  const updateRunOverrides = (updates: Partial<RunOverrides>) => {
    setState((prev) => ({ ...prev, runOverrides: { ...prev.runOverrides, ...updates } }));
  };

  const toggleAdvancedMode = () => {
    setState((prev) => ({ ...prev, isAdvancedMode: !prev.isAdvancedMode }));
  };

  return (
    <AppContext.Provider
      value={{
        state,
        updateCredentials,
        saveCredentials,
        updateProjectConfig,
        setGlobalLlmProvider,
        updateRoleModel,
        updateRunOverrides,
        toggleAdvancedMode,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};
