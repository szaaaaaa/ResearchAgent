import React from 'react';
import { useAppContext } from '../../store';
import { Card, Toggle, Input, Select } from '../ui';
import { GripVertical, Database, Globe, Search } from 'lucide-react';

export const DataSourcesTab: React.FC = () => {
  const { state, updateProjectConfig } = useAppContext();
  const { projectConfig } = state;

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">数据源 (Data Sources)</h2>
        <p className="text-sm text-slate-500 mt-2">配置学术和网页搜索提供商，控制来源优先级和广度。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="学术搜索 (Academic Search)" description="配置用于查找学术论文的来源。">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Database className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">arXiv</span>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.arxiv.enabled}
                  onChange={(c) => updateProjectConfig('sources.arxiv.enabled', c)}
                />
              </div>
              
              {projectConfig.sources.arxiv.enabled && (
                <div className="pl-14 pr-4 space-y-4 pb-4">
                  <Input
                    label="每次查询最大结果数"
                    type="number"
                    min="1"
                    value={projectConfig.sources.arxiv.max_results_per_query}
                    onChange={(e) => updateProjectConfig('sources.arxiv.max_results_per_query', parseInt(e.target.value))}
                  />
                  <Toggle
                    label="下载 PDF"
                    checked={projectConfig.sources.arxiv.download_pdf}
                    onChange={(c) => updateProjectConfig('sources.arxiv.download_pdf', c)}
                  />
                </div>
              )}

              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Database className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">Semantic Scholar</span>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.semantic_scholar.enabled}
                  onChange={(c) => updateProjectConfig('sources.semantic_scholar.enabled', c)}
                />
              </div>

              {projectConfig.sources.semantic_scholar.enabled && (
                <div className="pl-14 pr-4 space-y-4 pb-4">
                  <Input
                    label="每次查询最大结果数"
                    type="number"
                    min="1"
                    value={projectConfig.sources.semantic_scholar.max_results_per_query}
                    onChange={(e) => updateProjectConfig('sources.semantic_scholar.max_results_per_query', parseInt(e.target.value))}
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="礼貌延迟 (秒)"
                      type="number"
                      min="0"
                      value={projectConfig.sources.semantic_scholar.polite_delay_sec}
                      onChange={(e) => updateProjectConfig('sources.semantic_scholar.polite_delay_sec', parseInt(e.target.value))}
                    />
                    <Input
                      label="最大重试次数"
                      type="number"
                      min="0"
                      value={projectConfig.sources.semantic_scholar.max_retries}
                      onChange={(e) => updateProjectConfig('sources.semantic_scholar.max_retries', parseInt(e.target.value))}
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Database className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">OpenAlex</span>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.openalex.enabled}
                  onChange={(c) => updateProjectConfig('sources.openalex.enabled', c)}
                />
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="网页搜索 (Web Search)" description="配置用于查找网页内容的来源。">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Globe className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">通用网页搜索 (Web)</span>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.web.enabled}
                  onChange={(c) => updateProjectConfig('sources.web.enabled', c)}
                />
              </div>

              {projectConfig.sources.web.enabled && (
                <div className="pl-14 pr-4 space-y-4 pb-4">
                  <Input
                    label="每次查询最大结果数"
                    type="number"
                    min="1"
                    value={projectConfig.sources.web.max_results_per_query}
                    onChange={(e) => updateProjectConfig('sources.web.max_results_per_query', parseInt(e.target.value))}
                  />
                </div>
              )}

              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Search className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-slate-800">Google CSE</span>
                    <span className="text-xs text-slate-500 mt-0.5">需要 GOOGLE_CSE_API_KEY 和 CX</span>
                  </div>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.google_cse.enabled}
                  onChange={(c) => updateProjectConfig('sources.google_cse.enabled', c)}
                />
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-200 transition-colors hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <GripVertical className="w-4 h-4 text-slate-400 cursor-grab" />
                  <div className="p-2 bg-white rounded-lg shadow-sm border border-slate-100">
                    <Search className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-slate-800">Bing Search</span>
                    <span className="text-xs text-slate-500 mt-0.5">需要 BING_API_KEY</span>
                  </div>
                </div>
                <Toggle
                  label=""
                  checked={projectConfig.sources.bing.enabled}
                  onChange={(c) => updateProjectConfig('sources.bing.enabled', c)}
                />
              </div>
            </div>
          </Card>

          <Card title="搜索策略" description="控制如何组合多个数据源。">
            <Select
              label="搜索后端 (Search Backend)"
              options={[
                { value: 'hybrid', label: '混合 (Hybrid)' },
                { value: 'academic_only', label: '仅学术 (Academic Only)' },
                { value: 'web_only', label: '仅网页 (Web Only)' },
              ]}
              value={projectConfig.providers.search.backend}
              onChange={(e) => updateProjectConfig('providers.search.backend', e.target.value)}
            />
            
            <div className="mt-6 space-y-5">
              <Toggle
                label="查询所有学术源"
                description="如果启用，将并行查询所有已启用的学术源，而不是按顺序。"
                checked={projectConfig.providers.search.query_all_academic}
                onChange={(c) => updateProjectConfig('providers.search.query_all_academic', c)}
              />
              <Toggle
                label="查询所有网页源"
                description="如果启用，将并行查询所有已启用的网页源。"
                checked={projectConfig.providers.search.query_all_web}
                onChange={(c) => updateProjectConfig('providers.search.query_all_web', c)}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
