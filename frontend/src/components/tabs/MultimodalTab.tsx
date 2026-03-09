import React from 'react';
import { AlertTriangle, Image as ImageIcon } from 'lucide-react';
import { getModelOptionsForProvider } from '../../modelOptions';
import { useAppContext } from '../../store';
import { ProviderModelCatalog } from '../../types';
import { Card, Input, Select, Toggle } from '../ui';

function getGeminiCatalogStatus(catalog?: ProviderModelCatalog): string {
  if (!catalog || !catalog.loaded) {
    return 'Gemini VLM 模型目录加载中。';
  }
  if (catalog.missing_api_key) {
    return '未检测到 Gemini API Key 或 Google API Key，暂时无法拉取实时 VLM 模型目录。';
  }
  if (catalog.error) {
    return `Gemini VLM 模型目录拉取失败：${catalog.error}`;
  }
  if (catalog.modelCount === 0) {
    return '当前没有返回可用的 Gemini VLM 模型。';
  }
  return `已加载 ${catalog.modelCount} 个 Gemini VLM 模型。`;
}

export const MultimodalTab: React.FC = () => {
  const { state, updateProjectConfig } = useAppContext();
  const { projectConfig, openaiCatalog, geminiCatalog, openrouterCatalog, siliconflowCatalog } = state;
  const catalogs = { openaiCatalog, geminiCatalog, openrouterCatalog, siliconflowCatalog };
  const vlmModelOptions = getModelOptionsForProvider('gemini', catalogs);

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
                  使用 Marker 需要安装可选本地依赖；如果缺失，运行时会回退到 PyMuPDF。
                </p>
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-slate-100">
              <Toggle
                label="下载 LaTeX 源码"
                description="如果可用，尝试从 arXiv 下载 LaTeX 源码以获得更高质量的文本和公式。"
                checked={projectConfig.ingest.latex.download_source}
                onChange={(checked) => updateProjectConfig('ingest.latex.download_source', checked)}
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
                onChange={(e) => updateProjectConfig('fetch.max_results', parseInt(e.target.value, 10) || 1)}
              />
              <Input
                label="礼貌延迟 (秒)"
                type="number"
                min="0"
                value={projectConfig.fetch.polite_delay_sec}
                onChange={(e) => updateProjectConfig('fetch.polite_delay_sec', parseInt(e.target.value, 10) || 0)}
              />
            </div>

            <div className="mt-6">
              <Toggle
                label="自动下载 PDF"
                checked={projectConfig.fetch.download_pdf}
                onChange={(checked) => updateProjectConfig('fetch.download_pdf', checked)}
              />
            </div>
          </Card>
        </div>

        <div className="space-y-8">
          <Card title="图表理解 (Figure Understanding)" description="使用视觉语言模型分析和提取图表信息。">
            <Toggle
              label="启用图表提取"
              checked={projectConfig.ingest.figure.enabled}
              onChange={(checked) => updateProjectConfig('ingest.figure.enabled', checked)}
            />

            {projectConfig.ingest.figure.enabled && (
              <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl flex gap-3 mb-2">
                  <div className="p-1.5 bg-white rounded-lg shadow-sm border border-blue-50 shrink-0">
                    <ImageIcon className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="text-sm text-blue-900/80 pt-1 leading-relaxed space-y-1">
                    <p>当前图表理解后端仅支持 Gemini VLM，不建议现在直接改成 4 家统一入口。</p>
                    <p>{getGeminiCatalogStatus(geminiCatalog)}</p>
                    <p>建议：复杂图表优先 `gemini-2.5-pro`，速度和成本优先 `gemini-2.5-flash`。</p>
                  </div>
                </div>

                <Select
                  label="VLM 模型 (Gemini VLM)"
                  options={vlmModelOptions}
                  value={projectConfig.ingest.figure.vlm_model}
                  disabled={vlmModelOptions.length === 0}
                  onChange={(e) => updateProjectConfig('ingest.figure.vlm_model', e.target.value)}
                />

                <Input
                  label="VLM 温度 (Temperature)"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={projectConfig.ingest.figure.vlm_temperature}
                  onChange={(e) =>
                    updateProjectConfig('ingest.figure.vlm_temperature', parseFloat(e.target.value) || 0)
                  }
                />

                <div className="grid grid-cols-2 gap-6">
                  <Input
                    label="最小宽度 (Min Width)"
                    type="number"
                    min="50"
                    value={projectConfig.ingest.figure.min_width}
                    onChange={(e) => updateProjectConfig('ingest.figure.min_width', parseInt(e.target.value, 10) || 50)}
                  />
                  <Input
                    label="最小高度 (Min Height)"
                    type="number"
                    min="50"
                    value={projectConfig.ingest.figure.min_height}
                    onChange={(e) => updateProjectConfig('ingest.figure.min_height', parseInt(e.target.value, 10) || 50)}
                  />
                </div>

                <Input
                  label="验证最小实体匹配率"
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={projectConfig.ingest.figure.validation_min_entity_match}
                  onChange={(e) =>
                    updateProjectConfig(
                      'ingest.figure.validation_min_entity_match',
                      parseFloat(e.target.value) || 0,
                    )
                  }
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
