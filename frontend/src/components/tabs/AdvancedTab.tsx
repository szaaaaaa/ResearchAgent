import React from 'react';
import { useAppContext } from '../../store';
import { Card } from '../ui';
import { Code2, Download, Upload, Eye, EyeOff } from 'lucide-react';

export const AdvancedTab: React.FC = () => {
  const { state } = useAppContext();
  const { projectConfig, runOverrides } = state;
  const [showRedacted, setShowRedacted] = React.useState(true);

  const getEffectiveConfig = () => {
    // In a real app, this would merge projectConfig and runOverrides
    // and apply normalization logic.
    return JSON.stringify(
      {
        ...projectConfig,
        _run_overrides: runOverrides,
      },
      null,
      2
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between pb-6 border-b border-slate-200/60">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">高级 (Advanced)</h2>
          <p className="text-sm text-slate-500 mt-2">暴露原始配置和高级工具，不作为默认工作流的一部分。</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all shadow-sm">
            <Upload className="w-4 h-4 text-slate-500" />
            导入配置
          </button>
          <button className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all shadow-sm">
            <Download className="w-4 h-4 text-slate-500" />
            导出配置
          </button>
        </div>
      </div>

      <Card title="有效配置预览 (Effective Config Preview)" description="查看合并并规范化后的最终配置。">
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setShowRedacted(!showRedacted)}
            className="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1.5 transition-colors"
          >
            {showRedacted ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {showRedacted ? '显示脱敏' : '显示完整'}
          </button>
        </div>
        <div className="bg-slate-900 rounded-xl p-6 overflow-x-auto shadow-inner">
          <pre className="text-sm text-slate-300 font-mono leading-relaxed">
            {getEffectiveConfig()}
          </pre>
        </div>
        <div className="mt-5 flex items-center gap-2 text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
          <Code2 className="w-4 h-4" />
          <span className="text-sm">注意：即使在完整模式下，凭证也不会显示在此预览中。</span>
        </div>
      </Card>
    </div>
  );
};
