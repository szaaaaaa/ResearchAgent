import { AgentRoleId } from './types';

export const LLM_PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Google Gemini' },
];

export const MODEL_OPTIONS_BY_PROVIDER: Record<string, Array<{ value: string; label: string }>> = {
  openai: [
    { value: 'gpt-5.4', label: 'ChatGPT 5.4' },
    { value: 'gpt-5.4-mini', label: 'ChatGPT 5.4 Mini' },
    { value: 'gpt-4.1', label: 'GPT-4.1' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
  ],
  gemini: [
    { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro' },
    { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
  ],
};

export const AGENT_ROLE_LABELS: Record<AgentRoleId, string> = {
  conductor: 'Conductor',
  researcher: 'Researcher',
  critic: 'Critic',
};
