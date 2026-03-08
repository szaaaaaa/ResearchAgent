import React from 'react';
import { useAppContext } from '../../store';
import { Card, Select } from '../ui';
import { FolderOpen, RefreshCw } from 'lucide-react';

export const PathsTab: React.FC = () => {
  const { state, updateProjectConfig } = useAppContext();
  const { projectConfig } = state;

  const resetToDefault = (key: string, defaultValue: string) => {
    updateProjectConfig(key, defaultValue);
  };

  const PathInput = ({ label, configKey, defaultValue }: { label: string; configKey: string; defaultValue: string }) => {
    const value = configKey.split('.').reduce((o, i) => o[i], projectConfig as any);
    
    return (
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium text-slate-700">{label}</label>
          {value !== defaultValue && (
            <button
              onClick={() => resetToDefault(configKey, defaultValue)}
              className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              重置为默认
            </button>
          )}
        </div>
        <div className="relative">
          <input
            className="w-full bg-slate-50/50 border border-slate-200 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-mono shadow-sm"
            value={value}
            onChange={(e) => updateProjectConfig(configKey, e.target.value)}
          />
          <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">路径与存储 (Paths)</h2>
        <p className="text-sm text-slate-500 mt-2">控制数据、索引、输出和运行时状态的存储位置。</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-8 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-800 mb-5 tracking-tight">项目根目录</h3>
        <PathInput
          label="数据目录 (Data Dir)"
          configKey="project.data_dir"
          defaultValue="./data"
        />
        <p className="text-sm text-slate-500 mt-3">
          所有使用 <code className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-700 text-xs font-mono">{`\${project.data_dir}`}</code> 的路径都会解析为此目录。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="核心路径 (Core Paths)" description="论文、元数据和输出的存储位置。">
            <PathInput
              label="论文目录 (Papers Dir)"
              configKey="paths.papers_dir"
              defaultValue="${project.data_dir}/papers"
            />
            <PathInput
              label="元数据目录 (Metadata Dir)"
              configKey="paths.metadata_dir"
              defaultValue="${project.data_dir}/metadata"
            />
            <PathInput
              label="输出目录 (Outputs Dir)"
              configKey="paths.outputs_dir"
              defaultValue="${project.data_dir}/outputs"
            />
          </Card>

          <Card title="元数据存储 (Metadata Store)" description="存储论文元数据和状态的后端。">
            <Select
              label="后端 (Backend)"
              options={[
                { value: 'sqlite', label: 'SQLite' },
                { value: 'json', label: 'JSON' },
              ]}
              value={projectConfig.metadata_store.backend}
              onChange={(e) => updateProjectConfig('metadata_store.backend', e.target.value)}
            />
            
            {projectConfig.metadata_store.backend === 'sqlite' && (
              <div className="mt-6">
                <PathInput
                  label="SQLite 路径"
                  configKey="metadata_store.sqlite_path"
                  defaultValue="${project.data_dir}/metadata.db"
                />
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="索引与多模态路径" description="向量索引、图表和 LaTeX 源码的存储位置。">
            <PathInput
              label="索引持久化目录 (Index Persist Dir)"
              configKey="index.persist_dir"
              defaultValue="${project.data_dir}/indexes"
            />
            <PathInput
              label="图表目录 (Image Dir)"
              configKey="ingest.figure.image_dir"
              defaultValue="${project.data_dir}/figures"
            />
            <PathInput
              label="LaTeX 源码目录 (Source Dir)"
              configKey="ingest.latex.source_dir"
              defaultValue="${project.data_dir}/latex"
            />
          </Card>
        </div>
      </div>
    </div>
  );
};
