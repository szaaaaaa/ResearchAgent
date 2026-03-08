import React from 'react';
import { useAppContext } from '../../store';
import { Card, Input, Select, Toggle } from '../ui';

export const StrategyTab: React.FC = () => {
  const { state, updateProjectConfig, toggleAdvancedMode } = useAppContext();
  const { projectConfig, isAdvancedMode } = state;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between pb-6 border-b border-slate-200/60">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">研究策略 (Strategy)</h2>
          <p className="text-sm text-slate-500 mt-2">控制自主代理如何规划、搜索、分析和综合。</p>
        </div>
        <Toggle
          label="高级模式"
          checked={isAdvancedMode}
          onChange={toggleAdvancedMode}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          <Card title="基本策略 (Basic Strategy)" description="控制研究的核心参数。">
            <Select
              label="报告语言 (Language)"
              options={[
                { value: 'zh', label: '中文 (Chinese)' },
                { value: 'en', label: '英文 (English)' },
              ]}
              value={projectConfig.agent.language}
              onChange={(e) => updateProjectConfig('agent.language', e.target.value)}
            />
            
            <div className="grid grid-cols-2 gap-6">
              <Input
                label="最大迭代次数"
                type="number"
                min="1"
                value={projectConfig.agent.max_iterations}
                onChange={(e) => updateProjectConfig('agent.max_iterations', parseInt(e.target.value))}
              />
              <Input
                label="每次查询论文数"
                type="number"
                min="1"
                value={projectConfig.agent.papers_per_query}
                onChange={(e) => updateProjectConfig('agent.papers_per_query', parseInt(e.target.value))}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <Input
                label="最大研究问题数"
                type="number"
                min="1"
                value={projectConfig.agent.budget.max_research_questions}
                onChange={(e) => updateProjectConfig('agent.budget.max_research_questions', parseInt(e.target.value))}
              />
              <Input
                label="报告最大来源数"
                type="number"
                min="1"
                value={projectConfig.agent.report_max_sources}
                onChange={(e) => updateProjectConfig('agent.report_max_sources', parseInt(e.target.value))}
              />
            </div>
          </Card>

          <Card title="实验计划 (Experiment Plan)" description="是否生成实验设计和验证计划。">
            <Toggle
              label="启用实验计划"
              checked={projectConfig.agent.experiment_plan.enabled}
              onChange={(c) => updateProjectConfig('agent.experiment_plan.enabled', c)}
            />
            
            {projectConfig.agent.experiment_plan.enabled && isAdvancedMode && (
              <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                <Input
                  label="每个 RQ 最大实验数"
                  type="number"
                  min="1"
                  value={projectConfig.agent.experiment_plan.max_per_rq}
                  onChange={(e) => updateProjectConfig('agent.experiment_plan.max_per_rq', parseInt(e.target.value))}
                />
                <Toggle
                  label="需要人工验证结果"
                  checked={projectConfig.agent.experiment_plan.require_human_results}
                  onChange={(c) => updateProjectConfig('agent.experiment_plan.require_human_results', c)}
                />
              </div>
            )}
          </Card>
        </div>

        {isAdvancedMode && (
          <div className="space-y-8">
            <Card title="动态检索与查询重写" description="控制如何生成和重写搜索查询。">
              <div className="grid grid-cols-2 gap-6">
                <Input
                  label="每个 RQ 最小查询数"
                  type="number"
                  min="1"
                  value={projectConfig.agent.query_rewrite.min_per_rq}
                  onChange={(e) => updateProjectConfig('agent.query_rewrite.min_per_rq', parseInt(e.target.value))}
                />
                <Input
                  label="每个 RQ 最大查询数"
                  type="number"
                  min="1"
                  value={projectConfig.agent.query_rewrite.max_per_rq}
                  onChange={(e) => updateProjectConfig('agent.query_rewrite.max_per_rq', parseInt(e.target.value))}
                />
              </div>
              
              <div className="mt-6 space-y-5">
                <Toggle
                  label="学术简单查询 (Simple Academic)"
                  checked={projectConfig.agent.dynamic_retrieval.simple_query_academic}
                  onChange={(c) => updateProjectConfig('agent.dynamic_retrieval.simple_query_academic', c)}
                />
                <Toggle
                  label="PDF 简单查询 (Simple PDF)"
                  checked={projectConfig.agent.dynamic_retrieval.simple_query_pdf}
                  onChange={(c) => updateProjectConfig('agent.dynamic_retrieval.simple_query_pdf', c)}
                />
              </div>
            </Card>

            <Card title="证据与声明对齐" description="控制如何验证和对齐声明与证据。">
              <Toggle
                label="启用声明对齐 (Claim Alignment)"
                checked={projectConfig.agent.claim_alignment.enabled}
                onChange={(c) => updateProjectConfig('agent.claim_alignment.enabled', c)}
              />
              
              {projectConfig.agent.claim_alignment.enabled && (
                <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                  <Input
                    label="最小 RQ 相关度"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={projectConfig.agent.claim_alignment.min_rq_relevance}
                    onChange={(e) => updateProjectConfig('agent.claim_alignment.min_rq_relevance', parseFloat(e.target.value))}
                  />
                  <Input
                    label="最大锚点词数"
                    type="number"
                    min="1"
                    value={projectConfig.agent.claim_alignment.anchor_terms_max}
                    onChange={(e) => updateProjectConfig('agent.claim_alignment.anchor_terms_max', parseInt(e.target.value))}
                  />
                </div>
              )}
            </Card>
            
            <Card title="检查点 (Checkpointing)" description="保存和恢复代理状态。">
              <Toggle
                label="启用检查点"
                checked={projectConfig.agent.checkpointing.enabled}
                onChange={(c) => updateProjectConfig('agent.checkpointing.enabled', c)}
              />
              
              {projectConfig.agent.checkpointing.enabled && (
                <div className="mt-6 space-y-6 pt-6 border-t border-slate-100">
                  <Select
                    label="后端 (Backend)"
                    options={[
                      { value: 'sqlite', label: 'SQLite' },
                      { value: 'json', label: 'JSON' },
                    ]}
                    value={projectConfig.agent.checkpointing.backend}
                    onChange={(e) => updateProjectConfig('agent.checkpointing.backend', e.target.value)}
                  />
                  <Input
                    label="SQLite 路径"
                    value={projectConfig.agent.checkpointing.sqlite_path}
                    onChange={(e) => updateProjectConfig('agent.checkpointing.sqlite_path', e.target.value)}
                    className="font-mono"
                  />
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};
