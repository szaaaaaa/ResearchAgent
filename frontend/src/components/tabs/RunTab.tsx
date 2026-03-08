import React, { useState } from 'react';
import { Play, Terminal } from 'lucide-react';
import { API_BASE, useAppContext } from '../../store';
import { MODEL_OPTIONS_BY_PROVIDER } from '../../modelOptions';
import { Card, Input, Select, Toggle } from '../ui';

export const RunTab: React.FC = () => {
  const { state, updateRunOverrides } = useAppContext();
  const { runOverrides, credentials, projectConfig } = state;
  const [logs, setLogs] = useState<string[]>(['> 就绪。等待输入主题。']);
  const [isRunning, setIsRunning] = useState(false);
  const globalModelOptions = MODEL_OPTIONS_BY_PROVIDER[projectConfig.llm.provider] ?? [];

  const handleRun = async () => {
    setIsRunning(true);
    setLogs([
      '> 开始初始化 Agent...',
      runOverrides.topic ? `> 主题: ${runOverrides.topic}` : '> 续跑模式',
    ]);

    try {
      const response = await fetch(`${API_BASE}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          runOverrides,
          credentials,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        setLogs((prev) => [...prev, '> 没有收到可读取的输出流。']);
        return;
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        const text = decoder.decode(value, { stream: true });
        if (text) {
          setLogs((prev) => [...prev, text]);
        }
      }
    } catch (error) {
      setLogs((prev) => [...prev, `> 运行出错: ${String(error)}`]);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">运行</h2>
          <p className="text-sm text-slate-500 mt-2">配置运行参数并实时查看 Agent 终端输出。</p>
        </div>
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-6 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all shadow-sm shadow-blue-600/20"
        >
          <Play className="w-4 h-4 fill-current" />
          {isRunning ? '运行中...' : '开始运行'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <Card title="运行主题" description="设置本次研究任务的主题和基础运行参数。">
            <Input
              label="主题 (Topic)"
              description="输入要生成综述报告的研究主题。"
              placeholder="例如：多模态大模型在医学影像分析中的应用综述"
              value={runOverrides.topic}
              onChange={(e) => updateRunOverrides({ topic: e.target.value })}
            />

            <div className="grid grid-cols-2 gap-6">
              <Select
                label="执行模式"
                options={[
                  { value: 'os', label: 'Research OS (3-Agent)' },
                  { value: 'legacy', label: 'Legacy Graph' },
                ]}
                value={runOverrides.mode}
                onChange={(e) => updateRunOverrides({ mode: e.target.value })}
              />
              <Select
                label="语言"
                options={[
                  { value: 'zh', label: '中文 (Chinese)' },
                  { value: 'en', label: '英文 (English)' },
                ]}
                value={runOverrides.language}
                onChange={(e) => updateRunOverrides({ language: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <Select
                label="默认模型"
                options={globalModelOptions}
                value={runOverrides.model}
                onChange={(e) => updateRunOverrides({ model: e.target.value })}
              />
              <Input
                label="最大迭代次数 (Max Iterations)"
                type="number"
                min={1}
                max={20}
                value={runOverrides.max_iter}
                onChange={(e) => updateRunOverrides({ max_iter: parseInt(e.target.value, 10) || 1 })}
              />
            </div>

            <Input
              label="每轮论文数 (Papers per Query)"
              type="number"
              min={1}
              max={50}
              value={runOverrides.papers_per_query}
              onChange={(e) => updateRunOverrides({ papers_per_query: parseInt(e.target.value, 10) || 1 })}
            />
          </Card>

          <Card title="续跑设置" description="如需从已有 run 继续，可填写 run ID。">
            <Input
              label="续跑 Run ID (Resume Run ID)"
              description="留空表示启动一次新的研究运行。"
              placeholder="run_1234567890"
              value={runOverrides.resume_run_id}
              onChange={(e) => updateRunOverrides({ resume_run_id: e.target.value })}
              className="font-mono"
            />
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="运行输出">
            <Input
              label="输出目录 (Output Dir)"
              value={runOverrides.output_dir}
              onChange={(e) => updateRunOverrides({ output_dir: e.target.value })}
              className="font-mono"
            />

            <div className="space-y-5 mt-6 pt-6 border-t border-slate-100">
              <Toggle
                label="禁用 Web"
                checked={runOverrides.no_web}
                onChange={(checked) => updateRunOverrides({ no_web: checked })}
              />
              <Toggle
                label="禁用抓取"
                checked={runOverrides.no_scrape}
                onChange={(checked) => updateRunOverrides({ no_scrape: checked })}
              />
              <Toggle
                label="详细日志"
                checked={runOverrides.verbose}
                onChange={(checked) => updateRunOverrides({ verbose: checked })}
              />
            </div>
          </Card>

          <div className="bg-slate-900 rounded-2xl p-5 shadow-lg max-h-96 overflow-y-auto">
            <div className="flex items-center gap-2 text-slate-400 mb-4 border-b border-slate-800 pb-3">
              <Terminal className="w-4 h-4" />
              <span className="text-xs font-mono uppercase tracking-wider font-semibold">Terminal</span>
            </div>
            <div className="font-mono text-sm text-emerald-400 whitespace-pre-wrap">
              {logs.map((log, index) => (
                <span key={index}>{log}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
