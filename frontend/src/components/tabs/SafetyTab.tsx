import React from 'react';
import { useAppContext } from '../../store';
import { Card, Input, Toggle } from '../ui';
import { ShieldAlert, Activity, Lock } from 'lucide-react';

export const SafetyTab: React.FC = () => {
  const { state, updateProjectConfig } = useAppContext();
  const { projectConfig } = state;

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">安全与预算 (Safety)</h2>
        <p className="text-sm text-slate-500 mt-2">防止失控的成本、不安全的下载和不健康的提供商。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="预算守卫 (Budget Guard)" description="设置硬性限制以防止意外的高额账单。">
            <div className="p-4 bg-red-50/80 border border-red-100 rounded-xl flex gap-3 mb-6">
              <div className="p-1.5 bg-white rounded-lg shadow-sm border border-red-50 shrink-0">
                <ShieldAlert className="w-4 h-4 text-red-600" />
              </div>
              <p className="text-sm text-red-800 pt-1 leading-relaxed">
                达到这些限制中的任何一个都会立即终止代理运行。
              </p>
            </div>
            
            <Input
              label="最大 Token 数 (Max Tokens)"
              type="number"
              min="1000"
              value={projectConfig.budget_guard.max_tokens}
              onChange={(e) => updateProjectConfig('budget_guard.max_tokens', parseInt(e.target.value))}
            />
            
            <div className="grid grid-cols-2 gap-6">
              <Input
                label="最大 API 调用次数"
                type="number"
                min="1"
                value={projectConfig.budget_guard.max_api_calls}
                onChange={(e) => updateProjectConfig('budget_guard.max_api_calls', parseInt(e.target.value))}
              />
              <Input
                label="最大运行时间 (秒)"
                type="number"
                min="60"
                value={projectConfig.budget_guard.max_wall_time_sec}
                onChange={(e) => updateProjectConfig('budget_guard.max_wall_time_sec', parseInt(e.target.value))}
              />
            </div>
          </Card>

          <Card title="断路器 (Circuit Breaker)" description="保护系统免受不稳定搜索提供商的影响。">
            <Toggle
              label="启用搜索断路器"
              checked={projectConfig.providers.search.circuit_breaker.enabled}
              onChange={(c) => updateProjectConfig('providers.search.circuit_breaker.enabled', c)}
            />
            
            {projectConfig.providers.search.circuit_breaker.enabled && (
              <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                <div className="flex items-center gap-2 text-emerald-600 mb-2">
                  <Activity className="w-4 h-4" />
                  <span className="text-sm font-medium">当前状态: 闭合 (健康)</span>
                </div>
                
                <Input
                  label="失败阈值 (Failure Threshold)"
                  description="连续失败多少次后打开断路器。"
                  type="number"
                  min="1"
                  value={projectConfig.providers.search.circuit_breaker.failure_threshold}
                  onChange={(e) => updateProjectConfig('providers.search.circuit_breaker.failure_threshold', parseInt(e.target.value))}
                />
                
                <div className="grid grid-cols-2 gap-6">
                  <Input
                    label="打开持续时间 (秒)"
                    type="number"
                    min="1"
                    value={projectConfig.providers.search.circuit_breaker.open_ttl_sec}
                    onChange={(e) => updateProjectConfig('providers.search.circuit_breaker.open_ttl_sec', parseInt(e.target.value))}
                  />
                  <Input
                    label="半开探测延迟 (秒)"
                    type="number"
                    min="1"
                    value={projectConfig.providers.search.circuit_breaker.half_open_probe_after_sec}
                    onChange={(e) => updateProjectConfig('providers.search.circuit_breaker.half_open_probe_after_sec', parseInt(e.target.value))}
                  />
                </div>
                
                <Input
                  label="SQLite 路径"
                  value={projectConfig.providers.search.circuit_breaker.sqlite_path}
                  onChange={(e) => updateProjectConfig('providers.search.circuit_breaker.sqlite_path', e.target.value)}
                  className="font-mono"
                />
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="PDF 下载安全" description="控制允许从哪些主机下载 PDF。">
            <div className="flex items-center gap-2 text-amber-600 mb-5">
              <Lock className="w-4 h-4" />
              <span className="text-sm font-medium">安全建议：仅允许受信任的学术主机。</span>
            </div>
            
            <Toggle
              label="仅允许白名单主机"
              description="如果启用，将拒绝从不在白名单中的任何主机下载 PDF。"
              checked={projectConfig.sources.pdf_download.only_allowed_hosts}
              onChange={(c) => updateProjectConfig('sources.pdf_download.only_allowed_hosts', c)}
            />
            
            {projectConfig.sources.pdf_download.only_allowed_hosts && (
              <div className="mt-6 pt-6 border-t border-slate-100">
                <label className="text-sm font-medium text-slate-700 block mb-2">允许的主机 (每行一个)</label>
                <textarea
                  className="w-full h-40 bg-slate-50/50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-mono placeholder:text-slate-400 shadow-sm"
                  placeholder="arxiv.org&#10;nature.com&#10;sciencedirect.com"
                  value={projectConfig.sources.pdf_download.allowed_hosts.join('\n')}
                  onChange={(e) => updateProjectConfig('sources.pdf_download.allowed_hosts', e.target.value.split('\n').filter(Boolean))}
                />
              </div>
            )}
            
            <div className="mt-6">
              <Input
                label="禁止主机 TTL (秒)"
                description="失败的主机将被禁止多长时间。"
                type="number"
                min="0"
                value={projectConfig.sources.pdf_download.forbidden_host_ttl_sec}
                onChange={(e) => updateProjectConfig('sources.pdf_download.forbidden_host_ttl_sec', parseInt(e.target.value))}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
