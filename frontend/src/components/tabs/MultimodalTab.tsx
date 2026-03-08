import React from 'react';
import { useAppContext } from '../../store';
import { Card, Input, Select, Toggle } from '../ui';
import { Image as ImageIcon, AlertTriangle } from 'lucide-react';

export const MultimodalTab: React.FC = () => {
  const { state, updateProjectConfig } = useAppContext();
  const { projectConfig } = state;

  return (
    <div className="space-y-8">
      <div className="pb-6 border-b border-slate-200/60">
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">多模态摄取 (Multimodal)</h2>
        <p className="text-sm text-slate-500 mt-2">配置 PDF 文本提取、LaTeX 获取和图表理解。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="文本提取 (Text Extraction)" description="选择如何从 PDF 中提取文本。">
            <Select
              label="提取策略 (Strategy)"
              options={[
                { value: 'auto', label: '自动 (Auto)' },
                { value: 'latex_first', label: 'LaTeX 优先 (LaTeX First)' },
                { value: 'marker_only', label: '仅 Marker (Marker Only)' },
                { value: 'pymupdf_only', label: '仅 PyMuPDF (PyMuPDF Only)' },
              ]}
              value={projectConfig.ingest.text_extraction}
              onChange={(e) => updateProjectConfig('ingest.text_extraction', e.target.value)}
            />
            
            {projectConfig.ingest.text_extraction === 'marker_only' && (
              <div className="mt-5 p-4 bg-amber-50/80 border border-amber-100 rounded-xl flex gap-3">
                <div className="p-1.5 bg-white rounded-lg shadow-sm border border-amber-50 shrink-0">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                </div>
                <p className="text-sm text-amber-800 pt-1 leading-relaxed">
                  使用 Marker 需要安装可选的本地依赖包。如果未安装，将回退到 PyMuPDF。
                </p>
              </div>
            )}
            
            <div className="mt-6 pt-6 border-t border-slate-100">
              <Toggle
                label="下载 LaTeX 源码"
                description="如果可用，尝试从 arXiv 下载 LaTeX 源码以获得更高质量的文本和公式。"
                checked={projectConfig.ingest.latex.download_source}
                onChange={(c) => updateProjectConfig('ingest.latex.download_source', c)}
              />
            </div>
            
            {projectConfig.ingest.latex.download_source && (
              <div className="mt-5">
                <Input
                  label="LaTeX 源码目录"
                  value={projectConfig.ingest.latex.source_dir}
                  onChange={(e) => updateProjectConfig('ingest.latex.source_dir', e.target.value)}
                  className="font-mono"
                />
              </div>
            )}
          </Card>

          <Card title="获取设置 (Fetch Settings)" description="配置如何获取和下载文档。">
            <Select
              label="默认获取源 (Source)"
              options={[
                { value: 'arxiv', label: 'arXiv' },
                { value: 'semantic_scholar', label: 'Semantic Scholar' },
              ]}
              value={projectConfig.fetch.source}
              onChange={(e) => updateProjectConfig('fetch.source', e.target.value)}
            />
            
            <div className="grid grid-cols-2 gap-6 mt-6">
              <Input
                label="最大结果数"
                type="number"
                min="1"
                value={projectConfig.fetch.max_results}
                onChange={(e) => updateProjectConfig('fetch.max_results', parseInt(e.target.value))}
              />
              <Input
                label="礼貌延迟 (秒)"
                type="number"
                min="0"
                value={projectConfig.fetch.polite_delay_sec}
                onChange={(e) => updateProjectConfig('fetch.polite_delay_sec', parseInt(e.target.value))}
              />
            </div>
            
            <div className="mt-6">
              <Toggle
                label="自动下载 PDF"
                checked={projectConfig.fetch.download_pdf}
                onChange={(c) => updateProjectConfig('fetch.download_pdf', c)}
              />
            </div>
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="图表理解 (Figure Understanding)" description="使用视觉语言模型 (VLM) 分析和提取图表信息。">
            <Toggle
              label="启用图表提取"
              checked={projectConfig.ingest.figure.enabled}
              onChange={(c) => updateProjectConfig('ingest.figure.enabled', c)}
            />
            
            {projectConfig.ingest.figure.enabled && (
              <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl flex gap-3 mb-2">
                  <div className="p-1.5 bg-white rounded-lg shadow-sm border border-blue-50 shrink-0">
                    <ImageIcon className="w-4 h-4 text-blue-600" />
                  </div>
                  <p className="text-sm text-blue-900/80 pt-1 leading-relaxed">
                    图表理解通常需要配置 Gemini API Key 或 Google API Key，具体取决于所选的 VLM 模型。
                  </p>
                </div>
                
                <Select
                  label="VLM 模型 (VLM Model)"
                  options={[
                    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
                    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
                    { value: 'gpt-4o', label: 'GPT-4o' },
                  ]}
                  value={projectConfig.ingest.figure.vlm_model}
                  onChange={(e) => updateProjectConfig('ingest.figure.vlm_model', e.target.value)}
                />
                
                <Input
                  label="VLM 温度 (Temperature)"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={projectConfig.ingest.figure.vlm_temperature}
                  onChange={(e) => updateProjectConfig('ingest.figure.vlm_temperature', parseFloat(e.target.value))}
                />
                
                <div className="grid grid-cols-2 gap-6">
                  <Input
                    label="最小宽度 (Min Width)"
                    type="number"
                    min="50"
                    value={projectConfig.ingest.figure.min_width}
                    onChange={(e) => updateProjectConfig('ingest.figure.min_width', parseInt(e.target.value))}
                  />
                  <Input
                    label="最小高度 (Min Height)"
                    type="number"
                    min="50"
                    value={projectConfig.ingest.figure.min_height}
                    onChange={(e) => updateProjectConfig('ingest.figure.min_height', parseInt(e.target.value))}
                  />
                </div>
                
                <Input
                  label="验证最小实体匹配数"
                  type="number"
                  min="0"
                  value={projectConfig.ingest.figure.validation_min_entity_match}
                  onChange={(e) => updateProjectConfig('ingest.figure.validation_min_entity_match', parseInt(e.target.value))}
                />
                
                <Input
                  label="图表保存目录"
                  value={projectConfig.ingest.figure.image_dir}
                  onChange={(e) => updateProjectConfig('ingest.figure.image_dir', e.target.value)}
                  className="font-mono"
                />
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
