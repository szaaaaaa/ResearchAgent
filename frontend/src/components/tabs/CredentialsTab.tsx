import React from 'react';
import { CheckCircle2, Shield } from 'lucide-react';
import {
  getFirstModelForProvider,
  getModelOptionsForProvider,
  getModelsForProviderVendor,
  getVendorFromProviderModel,
  getVendorOptionsForProvider,
  isVendorScopedProvider,
  LLM_PROVIDER_OPTIONS,
} from '../../modelOptions';
import { useAppContext } from '../../store';
import { AgentRoleId, ProviderModelCatalog } from '../../types';
import { Card, Input, PasswordInput, Select } from '../ui';

const ROLE_LABELS: Record<AgentRoleId, string> = {
  conductor: 'Conductor 统筹',
  researcher: 'Researcher 研究',
  critic: 'Critic 审查',
};

function getCatalogStatus(provider: string, catalog?: ProviderModelCatalog): string | null {
  const providerLabel = (
    {
      openai: 'OpenAI',
      gemini: 'Gemini',
      openrouter: 'OpenRouter',
      siliconflow: 'SiliconFlow',
    } as const
  )[provider as 'openai' | 'gemini' | 'openrouter' | 'siliconflow'];
  if (!providerLabel) {
    return null;
  }
  if (!catalog || !catalog.loaded) {
    return `${providerLabel} 模型目录加载中。`;
  }
  if (catalog.missing_api_key) {
    return `${providerLabel} 未检测到 API Key，暂时无法拉取实时模型目录。`;
  }
  if (catalog.error) {
    return `${providerLabel} 模型目录拉取失败：${catalog.error}`;
  }
  if (catalog.modelCount === 0) {
    return `${providerLabel} 当前没有返回可用模型。`;
  }
  return `${providerLabel} 已加载 ${catalog.vendorCount} 个厂商，${catalog.modelCount} 个模型。`;
}

export const CredentialsTab: React.FC = () => {
  const { state, updateCredentials, updateProjectConfig, setGlobalLlmProvider, updateRoleModel, saveCredentials } = useAppContext();
  const { credentials, credentialStatus, openaiCatalog, geminiCatalog, openrouterCatalog, siliconflowCatalog, projectConfig } = state;
  const catalogs = { openaiCatalog, geminiCatalog, openrouterCatalog, siliconflowCatalog };

  const globalProvider = projectConfig.llm.provider;
  const globalModelOptions = getModelOptionsForProvider(globalProvider, catalogs);
  const globalVendor = getVendorFromProviderModel(globalProvider, projectConfig.llm.model, catalogs);
  const globalVendorOptions = getVendorOptionsForProvider(globalProvider, catalogs);
  const globalVendorModels = getModelsForProviderVendor(globalProvider, globalVendor, catalogs);
  const globalCatalog =
    globalProvider === 'openai'
      ? openaiCatalog
      : globalProvider === 'gemini'
        ? geminiCatalog
        : globalProvider === 'openrouter'
          ? openrouterCatalog
          : globalProvider === 'siliconflow'
            ? siliconflowCatalog
            : undefined;

  const getStatus = (key: keyof typeof credentials) => {
    if (credentials[key]) {
      return 'present';
    }
    return credentialStatus[key].present ? 'present' : 'missing';
  };

  const getDescription = (key: keyof typeof credentials) => {
    if (credentials[key]) {
      return '当前输入只保存在浏览器状态中，点击“保存凭证”后才会写入项目 .env。';
    }
    switch (credentialStatus[key].source) {
      case 'environment':
        return '已在系统环境变量中检测到，界面不会显示真实值。';
      case 'dotenv':
        return '已在项目 .env 中检测到，界面不会显示真实值。';
      case 'both':
        return '系统环境变量和项目 .env 中都检测到了，界面不会显示真实值。';
      default:
        return '当前没有检测到已保存的值。';
    }
  };

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">模型与凭证</h2>
        <p className="text-sm text-slate-500 mt-2">管理默认模型、3 个 agent 的角色模型，以及各类 API Key。</p>
      </div>

      <div className="bg-blue-50/50 border border-blue-100 rounded-2xl p-5 flex gap-4 items-start">
        <div className="p-2 bg-white rounded-xl shadow-sm border border-blue-50 shrink-0">
          <Shield className="w-5 h-5 text-blue-600" />
        </div>
        <div className="text-sm text-blue-900/80 leading-relaxed pt-0.5 space-y-1">
          <p>OpenRouter 和 SiliconFlow 都按“中转站”处理：先选厂商，再选具体模型。</p>
          <p>模型下拉框优先使用后端实时目录，不再依赖不完整的前端静态列表。</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="全局默认模型" description="设置默认 provider、模型以及重试策略。">
            <Select
              label="模型服务商"
              options={LLM_PROVIDER_OPTIONS}
              value={globalProvider}
              onChange={(e) => setGlobalLlmProvider(e.target.value)}
            />

            {getCatalogStatus(globalProvider, globalCatalog) && (
              <p className="text-xs text-slate-500 -mt-2">{getCatalogStatus(globalProvider, globalCatalog)}</p>
            )}

            <div className={`grid gap-6 ${isVendorScopedProvider(globalProvider) ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {isVendorScopedProvider(globalProvider) && (
                <Select
                  label="模型厂商"
                  options={globalVendorOptions}
                  value={globalVendor}
                  disabled={globalVendorOptions.length === 0}
                  onChange={(e) => {
                    const vendor = e.target.value;
                    const nextModel = getModelsForProviderVendor(globalProvider, vendor, catalogs)[0]?.value ?? '';
                    updateProjectConfig('llm.model', nextModel);
                  }}
                />
              )}
              <Select
                label="具体模型"
                options={isVendorScopedProvider(globalProvider) ? globalVendorModels : globalModelOptions}
                value={projectConfig.llm.model}
                disabled={(isVendorScopedProvider(globalProvider) ? globalVendorModels : globalModelOptions).length === 0}
                onChange={(e) => updateProjectConfig('llm.model', e.target.value)}
              />
              <Input
                label="Temperature"
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
                label="重试次数"
                type="number"
                min="0"
                value={projectConfig.providers.llm.retries}
                onChange={(e) => updateProjectConfig('providers.llm.retries', parseInt(e.target.value, 10) || 0)}
              />
              <Input
                label="重试退避秒数"
                type="number"
                min="1"
                value={projectConfig.providers.llm.retry_backoff_sec}
                onChange={(e) => updateProjectConfig('providers.llm.retry_backoff_sec', parseInt(e.target.value, 10) || 1)}
              />
            </div>
          </Card>

          <Card title="3-Agent 角色模型" description="分别为 conductor、researcher、critic 指定 provider 与模型。">
            <div className="space-y-6">
              {(['conductor', 'researcher', 'critic'] as const).map((roleId) => {
                const roleConfig = projectConfig.llm.role_models[roleId];
                const roleProvider = roleConfig.provider || globalProvider;
                const roleVendor = getVendorFromProviderModel(roleProvider, roleConfig.model, catalogs);
                const roleVendorOptions = getVendorOptionsForProvider(roleProvider, catalogs);
                const roleOptions = getModelOptionsForProvider(roleProvider, catalogs);
                const roleVendorModels = getModelsForProviderVendor(roleProvider, roleVendor, catalogs);
                const roleCatalog =
                  roleProvider === 'openai'
                    ? openaiCatalog
                    : roleProvider === 'gemini'
                      ? geminiCatalog
                      : roleProvider === 'openrouter'
                        ? openrouterCatalog
                        : roleProvider === 'siliconflow'
                          ? siliconflowCatalog
                          : undefined;

                return (
                  <div key={roleId} className="rounded-xl border border-slate-200 p-4 space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800">{ROLE_LABELS[roleId]}</h3>
                      <p className="text-xs text-slate-500 mt-1">每个角色都可以单独指定 provider 与模型。</p>
                    </div>

                    {getCatalogStatus(roleProvider, roleCatalog) && (
                      <p className="text-xs text-slate-500 -mt-1">{getCatalogStatus(roleProvider, roleCatalog)}</p>
                    )}

                    <div className={`grid gap-4 ${isVendorScopedProvider(roleProvider) ? 'grid-cols-3' : 'grid-cols-2'}`}>
                      <Select
                        label="模型服务商"
                        options={LLM_PROVIDER_OPTIONS}
                        value={roleConfig.provider}
                        onChange={(e) => {
                          const provider = e.target.value;
                          updateRoleModel(roleId, {
                            provider,
                            model: getFirstModelForProvider(provider, catalogs) || roleConfig.model,
                          });
                        }}
                      />
                      {isVendorScopedProvider(roleProvider) && (
                        <Select
                          label="模型厂商"
                          options={roleVendorOptions}
                          value={roleVendor}
                          disabled={roleVendorOptions.length === 0}
                          onChange={(e) => {
                            const vendor = e.target.value;
                            const nextModel = getModelsForProviderVendor(roleProvider, vendor, catalogs)[0]?.value ?? '';
                            updateRoleModel(roleId, { model: nextModel });
                          }}
                        />
                      )}
                      <Select
                        label="具体模型"
                        options={isVendorScopedProvider(roleProvider) ? roleVendorModels : roleOptions}
                        value={roleConfig.model}
                        disabled={(isVendorScopedProvider(roleProvider) ? roleVendorModels : roleOptions).length === 0}
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
          <Card title="API 凭证" description="界面只显示是否存在，不会显示真实密钥。">
            <div className="space-y-5">
              <PasswordInput
                label="OpenAI API Key"
                status={getStatus('OPENAI_API_KEY')}
                description={getDescription('OPENAI_API_KEY')}
                value={credentials.OPENAI_API_KEY}
                onChange={(e) => updateCredentials({ OPENAI_API_KEY: e.target.value })}
                placeholder="sk-..."
              />
              <PasswordInput
                label="Gemini API Key"
                status={getStatus('GEMINI_API_KEY')}
                description={getDescription('GEMINI_API_KEY')}
                value={credentials.GEMINI_API_KEY}
                onChange={(e) => updateCredentials({ GEMINI_API_KEY: e.target.value })}
                placeholder="AIza..."
              />
              <PasswordInput
                label="OpenRouter API Key"
                status={getStatus('OPENROUTER_API_KEY')}
                description={getDescription('OPENROUTER_API_KEY')}
                value={credentials.OPENROUTER_API_KEY}
                onChange={(e) => updateCredentials({ OPENROUTER_API_KEY: e.target.value })}
                placeholder="sk-or-..."
              />
              <PasswordInput
                label="SiliconFlow API Key"
                status={getStatus('SILICONFLOW_API_KEY')}
                description={getDescription('SILICONFLOW_API_KEY')}
                value={credentials.SILICONFLOW_API_KEY}
                onChange={(e) => updateCredentials({ SILICONFLOW_API_KEY: e.target.value })}
                placeholder="sk-..."
              />
              <PasswordInput
                label="Google API Key"
                status={getStatus('GOOGLE_API_KEY')}
                description={getDescription('GOOGLE_API_KEY')}
                value={credentials.GOOGLE_API_KEY}
                onChange={(e) => updateCredentials({ GOOGLE_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="SerpAPI Key"
                status={getStatus('SERPAPI_API_KEY')}
                description={getDescription('SERPAPI_API_KEY')}
                value={credentials.SERPAPI_API_KEY}
                onChange={(e) => updateCredentials({ SERPAPI_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="Google CSE API Key"
                status={getStatus('GOOGLE_CSE_API_KEY')}
                description={getDescription('GOOGLE_CSE_API_KEY')}
                value={credentials.GOOGLE_CSE_API_KEY}
                onChange={(e) => updateCredentials({ GOOGLE_CSE_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="Google CSE CX"
                status={getStatus('GOOGLE_CSE_CX')}
                description={getDescription('GOOGLE_CSE_CX')}
                value={credentials.GOOGLE_CSE_CX}
                onChange={(e) => updateCredentials({ GOOGLE_CSE_CX: e.target.value })}
              />
              <PasswordInput
                label="Bing API Key"
                status={getStatus('BING_API_KEY')}
                description={getDescription('BING_API_KEY')}
                value={credentials.BING_API_KEY}
                onChange={(e) => updateCredentials({ BING_API_KEY: e.target.value })}
              />
              <PasswordInput
                label="GitHub Token"
                status={getStatus('GITHUB_TOKEN')}
                description={getDescription('GITHUB_TOKEN')}
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
                保存凭证
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
