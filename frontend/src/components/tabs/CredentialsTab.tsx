import React from 'react';
import { AGENT_ROLE_LABELS, LLM_PROVIDER_OPTIONS, MODEL_OPTIONS_BY_PROVIDER } from '../../modelOptions';
import { useAppContext } from '../../store';
import { Card, PasswordInput, Select, Input } from '../ui';
import { Shield, CheckCircle2 } from 'lucide-react';

export const CredentialsTab: React.FC = () => {
  const { state, updateCredentials, updateProjectConfig, setGlobalLlmProvider, updateRoleModel, saveCredentials } = useAppContext();
  const { credentials, projectConfig } = state;
  const globalModelOptions = MODEL_OPTIONS_BY_PROVIDER[projectConfig.llm.provider] ?? [];

  const getStatus = (key: string) => {
    return key && key.length > 0 ? 'present' : 'missing';
  };

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">凭证与模型 (Credentials)</h2>
        <p className="text-sm text-slate-500 mt-2">安全地管理 API 密钥并选择默认的语言模型提供商。</p>
      </div>

      <div className="bg-blue-50/50 border border-blue-100 rounded-2xl p-5 flex gap-4 items-start">
        <div className="p-2 bg-white rounded-xl shadow-sm border border-blue-50 shrink-0">
          <Shield className="w-5 h-5 text-blue-600" />
        </div>
        <div className="text-sm text-blue-900/80 leading-relaxed pt-0.5">
          <strong className="font-semibold text-blue-900">安全提示：</strong>
          您的 API 密钥仅存储在本地凭据管理器或当前进程环境变量中。它们绝不会以明文形式保存在项目配置文件中。
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="模型提供商 (LLM Provider)" description="选择用于推理的主要模型后端。">
            <Select
              label="默认提供商"
              options={LLM_PROVIDER_OPTIONS}
              value={projectConfig.llm.provider}
              onChange={(e) => setGlobalLlmProvider(e.target.value)}
            />
             
            <div className="grid grid-cols-2 gap-6">
              <Select
                label="默认模型 (Model)"
                options={globalModelOptions}
                value={projectConfig.llm.model}
                onChange={(e) => updateProjectConfig('llm.model', e.target.value)}
              />
              <Input
                label="温度 (Temperature)"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={projectConfig.llm.temperature}
                onChange={(e) => updateProjectConfig('llm.temperature', parseFloat(e.target.value))}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <Input
                label="重试次数 (Retries)"
                type="number"
                min="0"
                value={projectConfig.providers.llm.retries}
                onChange={(e) => updateProjectConfig('providers.llm.retries', parseInt(e.target.value))}
              />
              <Input
                label="重试退避 (Backoff Sec)"
                type="number"
                min="1"
                value={projectConfig.providers.llm.retry_backoff_sec}
                onChange={(e) => updateProjectConfig('providers.llm.retry_backoff_sec', parseInt(e.target.value))}
              />
            </div>
          </Card>

          <Card title="3-Agent 模型分配" description="为 Conductor、Researcher、Critic 分别设置模型。">
            <div className="space-y-6">
              {(['conductor', 'researcher', 'critic'] as const).map((roleId) => {
                const roleConfig = projectConfig.llm.role_models[roleId];
                const roleProvider = roleConfig.provider || projectConfig.llm.provider;
                const roleOptions = MODEL_OPTIONS_BY_PROVIDER[roleProvider] ?? globalModelOptions;
                return (
                  <div key={roleId} className="rounded-xl border border-slate-200 p-4 space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800">{AGENT_ROLE_LABELS[roleId]}</h3>
                      <p className="text-xs text-slate-500 mt-1">当前 3-agent OS 模式下，此角色将使用这里选择的模型。</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <Select
                        label="提供商"
                        options={LLM_PROVIDER_OPTIONS}
                        value={roleConfig.provider}
                        onChange={(e) => {
                          const provider = e.target.value;
                          const fallbackModel = MODEL_OPTIONS_BY_PROVIDER[provider]?.[0]?.value ?? '';
                          updateRoleModel(roleId, { provider, model: fallbackModel });
                        }}
                      />
                      <Select
                        label="模型"
                        options={roleOptions}
                        value={roleConfig.model}
                        onChange={(e) => updateRoleModel(roleId, { model: e.target.value })}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="API 密钥管理" description="提供所需服务的访问凭证。">
            <div className="space-y-5">
              <PasswordInput
                label="OpenAI API Key"
                status={getStatus(credentials.OPENAI_API_KEY)}
                value={credentials.OPENAI_API_KEY}
                onChange={(e) => updateCredentials({ OPENAI_API_KEY: e.target.value })}
                placeholder="sk-..."
              />
              <PasswordInput
                label="Gemini API Key"
                status={getStatus(credentials.GEMINI_API_KEY)}
                value={credentials.GEMINI_API_KEY}
                onChange={(e) => updateCredentials({ GEMINI_API_KEY: e.target.value })}
                placeholder="AIza..."
              />
              <PasswordInput
                label="Google API Key"
                status={getStatus(credentials.GOOGLE_API_KEY)}
                value={credentials.GOOGLE_API_KEY}
                onChange={(e) => updateCredentials({ GOOGLE_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="SerpAPI Key"
                status={getStatus(credentials.SERPAPI_API_KEY)}
                value={credentials.SERPAPI_API_KEY}
                onChange={(e) => updateCredentials({ SERPAPI_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="Google CSE API Key"
                status={getStatus(credentials.GOOGLE_CSE_API_KEY)}
                value={credentials.GOOGLE_CSE_API_KEY}
                onChange={(e) => updateCredentials({ GOOGLE_CSE_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="Google CSE CX"
                status={getStatus(credentials.GOOGLE_CSE_CX)}
                value={credentials.GOOGLE_CSE_CX}
                onChange={(e) => updateCredentials({ GOOGLE_CSE_CX: e.target.value })}
              />
              <PasswordInput
                label="Bing API Key"
                status={getStatus(credentials.BING_API_KEY)}
                value={credentials.BING_API_KEY}
                onChange={(e) => updateCredentials({ BING_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="GitHub Token"
                status={getStatus(credentials.GITHUB_TOKEN)}
                value={credentials.GITHUB_TOKEN}
                onChange={(e) => updateCredentials({ GITHUB_TOKEN: e.target.value })}
                placeholder="ghp_..."
              />
            </div>
            
            <div className="mt-8 pt-6 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => void saveCredentials()}
                className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                测试凭证连接
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
