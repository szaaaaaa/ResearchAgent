import React from 'react';
import { RunEvent } from '../types';

const VISIBLE_EVENTS = new Set([
  'plan_update',
  'node_status',
  'skill_invoke',
  'tool_invoke',
  'observation',
  'replan',
  'artifact_created',
  'policy_block',
  'run_terminate',
]);

const EVENT_STYLES: Record<string, string> = {
  plan_update: 'bg-slate-100 text-slate-700',
  node_status: 'bg-sky-100 text-sky-700',
  skill_invoke: 'bg-indigo-100 text-indigo-700',
  tool_invoke: 'bg-cyan-100 text-cyan-700',
  observation: 'bg-amber-100 text-amber-800',
  replan: 'bg-orange-100 text-orange-800',
  artifact_created: 'bg-emerald-100 text-emerald-700',
  policy_block: 'bg-rose-100 text-rose-700',
  run_terminate: 'bg-slate-200 text-slate-700',
};

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value));
}

function eventBadgeClass(type: string): string {
  return EVENT_STYLES[type] || 'bg-slate-100 text-slate-700';
}

function eventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    plan_update: 'Plan',
    node_status: 'Node',
    skill_invoke: 'Skill',
    tool_invoke: 'Tool',
    observation: 'Observation',
    replan: 'Replan',
    artifact_created: 'Artifact',
    policy_block: 'Policy',
    run_terminate: 'Terminate',
  };
  return labels[type] || type;
}

function describeEvent(event: RunEvent): { title: string; detail: string } {
  switch (event.type) {
    case 'plan_update':
      return {
        title: `Planner updated local DAG`,
        detail: event.detail || `Iteration ${event.iteration ?? 0}`,
      };
    case 'node_status':
      return {
        title: `${event.role || 'node'} / ${event.nodeId || 'unknown'} -> ${event.status || 'pending'}`,
        detail: event.detail || '',
      };
    case 'skill_invoke':
      return {
        title: `Invoke skill ${event.skillId || 'unknown'}`,
        detail: [event.nodeId, event.phase].filter(Boolean).join(' · '),
      };
    case 'tool_invoke':
      return {
        title: `Invoke tool ${event.toolId || 'unknown'}`,
        detail: [event.skillId, event.phase, event.nodeId].filter(Boolean).join(' · '),
      };
    case 'observation':
      return {
        title: `Observation from ${event.role || event.nodeId || 'runtime'}`,
        detail: event.detail || event.reason || '',
      };
    case 'replan':
      return {
        title: `Planner requested replan`,
        detail: event.reason || event.detail || '',
      };
    case 'artifact_created':
      return {
        title: `Artifact created: ${event.artifactType || 'unknown'}`,
        detail: [event.artifactId, event.producerRole, event.producerSkill].filter(Boolean).join(' · '),
      };
    case 'policy_block':
      return {
        title: `Policy blocked ${event.blockedAction || 'action'}`,
        detail: event.reason || event.detail || '',
      };
    case 'run_terminate':
      return {
        title: `Run terminated`,
        detail: event.reason || event.detail || '',
      };
    default:
      return {
        title: event.type,
        detail: event.detail || '',
      };
  }
}

export const BehaviorTimeline: React.FC<{ events: RunEvent[] }> = ({ events }) => {
  const visibleEvents = events.filter((event) => VISIBLE_EVENTS.has(event.type));
  if (visibleEvents.length === 0) {
    return null;
  }

  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-400">Timeline</p>
        <h3 className="mt-2 text-base font-semibold text-slate-900">技能 / 工具 / 观察 / 重规划</h3>
      </div>

      <div className="mt-5 space-y-3">
        {visibleEvents
          .slice()
          .reverse()
          .map((event) => {
            const description = describeEvent(event);
            return (
              <div
                key={event.id}
                className="flex items-start justify-between gap-4 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${eventBadgeClass(event.type)}`}>
                      {eventTypeLabel(event.type)}
                    </span>
                    <p className="text-sm font-semibold text-slate-900">{description.title}</p>
                  </div>
                  {description.detail ? <p className="mt-1 text-sm text-slate-500">{description.detail}</p> : null}
                </div>
                <span className="shrink-0 rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-500 ring-1 ring-slate-200">
                  {formatTimestamp(event.ts)}
                </span>
              </div>
            );
          })}
      </div>
    </section>
  );
};
