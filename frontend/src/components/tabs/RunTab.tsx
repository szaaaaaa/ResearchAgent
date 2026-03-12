import React from 'react';
import { ArrowUpRight, Bot, LoaderCircle, SendHorizonal, Square, User2 } from 'lucide-react';
import { useAppContext } from '../../store';
import { NodeStatusMap, RoutePlan, RunArtifact } from '../../types';
import { Button } from '../ui';
import { UiPreferences } from '../settings/types';
import { RouteGraph } from '../RouteGraph';
import { BehaviorTimeline } from '../BehaviorTimeline';
import { RawTerminalPanel } from '../RawTerminalPanel';

const PROMPT_TEMPLATES = [
  '为一个关于动态研究智能体系统的主题生成最小研究闭环。',
  '比较 planner -> executor -> skill -> tool 架构和旧固定流水线的差异。',
  '分析一个检索增强系统在 reviewer 按需插入下的运行路径。',
];

function formatStatusLabel(status: string): string {
  if (status === 'Running') {
    return '运行中';
  }
  if (status === 'Stopping') {
    return '停止中';
  }
  if (status === 'Stopped') {
    return '已停止';
  }
  if (status === 'Failed') {
    return '失败';
  }
  if (status === 'Completed') {
    return '已完成';
  }
  return '待命';
}

function getMessageWidthClass(chatWidth: UiPreferences['chatWidth']): string {
  return chatWidth === 'wide' ? 'max-w-6xl' : 'max-w-4xl';
}

function getDensityClasses(density: UiPreferences['density']): { gap: string; padding: string } {
  if (density === 'compact') {
    return { gap: 'space-y-4', padding: 'py-2' };
  }
  return { gap: 'space-y-6', padding: 'py-4' };
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

function currentNode(routePlan: RoutePlan | null, nodeStatus: NodeStatusMap): { nodeId: string; status: string; goal: string; role: string } | null {
  if (!routePlan) {
    return null;
  }

  for (const node of routePlan.nodes) {
    const status = nodeStatus[node.node_id];
    if (status === 'running') {
      return { nodeId: node.node_id, status, goal: node.goal, role: node.role };
    }
  }
  for (const node of routePlan.nodes) {
    const status = nodeStatus[node.node_id];
    if (status === 'needs_replan' || status === 'partial') {
      return { nodeId: node.node_id, status, goal: node.goal, role: node.role };
    }
  }
  for (const node of routePlan.nodes) {
    const status = nodeStatus[node.node_id] || 'pending';
    if (status === 'pending') {
      return { nodeId: node.node_id, status, goal: node.goal, role: node.role };
    }
  }
  return routePlan.nodes.length > 0
    ? {
        nodeId: routePlan.nodes[routePlan.nodes.length - 1].node_id,
        status: nodeStatus[routePlan.nodes[routePlan.nodes.length - 1].node_id] || 'pending',
        goal: routePlan.nodes[routePlan.nodes.length - 1].goal,
        role: routePlan.nodes[routePlan.nodes.length - 1].role,
      }
    : null;
}

function summarizeCurrentStage(conversation: {
  status: string;
  routePlan: RoutePlan | null;
  nodeStatus: NodeStatusMap;
  artifacts: RunArtifact[];
}): { title: string; detail: string } {
  if (conversation.status === 'Completed') {
    return {
      title: '运行完成',
      detail: `已完成本次动态路由执行，累计产出 ${conversation.artifacts.length} 个 artifacts。`,
    };
  }
  if (conversation.status === 'Failed') {
    return {
      title: '运行失败',
      detail: '执行链路被中断，请结合下方时间线查看 observation、policy block 或 replan 事件。',
    };
  }
  if (conversation.status === 'Stopping' || conversation.status === 'Stopped') {
    return {
      title: '运行已停止',
      detail: '当前运行已被用户停止，节点状态保持在最后一次真实事件。',
    };
  }

  const node = currentNode(conversation.routePlan, conversation.nodeStatus);
  if (node) {
    const prefix =
      node.status === 'running'
        ? '正在执行'
        : node.status === 'needs_replan' || node.status === 'partial'
          ? '等待重规划'
          : '下一个节点';
    return {
      title: `${prefix}: ${node.role} / ${node.nodeId}`,
      detail: node.goal,
    };
  }

  if (conversation.routePlan?.nodes.length) {
    return {
      title: '已生成本地 DAG',
      detail: `当前计划包含 ${conversation.routePlan.nodes.length} 个节点。`,
    };
  }

  return {
    title: '等待执行',
    detail: '输入请求后，运行时会生成局部 DAG，并在这里展示节点、事件和 artifacts。',
  };
}

export const RunTab: React.FC<{ uiPreferences: UiPreferences }> = ({ uiPreferences }) => {
  const { state, updateRunOverrides, startRun, stopRun } = useAppContext();
  const { conversations, activeConversationId, runOverrides } = state;
  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) ?? conversations[0];
  const isActiveConversationRunning =
    activeConversation.status === 'Running' || activeConversation.status === 'Stopping';
  const shouldShowRunInsights =
    isActiveConversationRunning ||
    activeConversation.status === 'Completed' ||
    activeConversation.status === 'Failed' ||
    activeConversation.status === 'Stopped' ||
    Boolean(
      activeConversation.routePlan?.nodes.length ||
        activeConversation.runEvents.length ||
        activeConversation.artifacts.length ||
        activeConversation.rawTerminalLog.trim(),
    );
  const messageWidthClass = getMessageWidthClass(uiPreferences.chatWidth);
  const densityClasses = getDensityClasses(uiPreferences.density);
  const hasConversation = activeConversation.messages.some((message) => message.role === 'user');
  const visibleMessages = hasConversation
    ? activeConversation.messages.filter((message) => message.content || message.streaming)
    : [];
  const messageFontClass = uiPreferences.messageFont === 'large' ? 'text-[15px]' : 'text-sm';
  const currentStage = summarizeCurrentStage(activeConversation);

  const submitPrompt = () => {
    if (isActiveConversationRunning) {
      return;
    }
    void startRun();
  };

  return (
    <div className="flex min-h-screen flex-col">
      <div className="border-b border-slate-200 bg-[var(--app-bg)]/92 px-4 py-5 backdrop-blur-xl sm:px-6">
        <div className={`mx-auto flex w-full ${messageWidthClass} items-center justify-between gap-4`}>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Dynamic Research OS</p>
            <h2 className="mt-2 truncate text-2xl font-semibold tracking-tight text-slate-900">
              {activeConversation.title}
            </h2>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-medium text-slate-700">{formatStatusLabel(activeConversation.status)}</p>
            <p className="mt-1 text-xs text-slate-400">{formatTimestamp(activeConversation.updatedAt)}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-40 pt-8 sm:px-6">
        <div className={`mx-auto w-full ${messageWidthClass}`}>
          {shouldShowRunInsights ? (
            <div className="mb-8 space-y-6">
              <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-400">Runtime Summary</p>
                <h3 className="mt-2 text-base font-semibold text-slate-900">{currentStage.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">{currentStage.detail}</p>
              </section>

              {activeConversation.routePlan?.nodes.length ? (
                <RouteGraph routePlan={activeConversation.routePlan} nodeStatus={activeConversation.nodeStatus} />
              ) : null}

              {activeConversation.artifacts.length > 0 ? (
                <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-400">Artifacts</p>
                      <h3 className="mt-2 text-base font-semibold text-slate-900">产出面板</h3>
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                      {activeConversation.artifacts.length} item(s)
                    </span>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {activeConversation.artifacts.map((artifact) => (
                      <div
                        key={`${artifact.artifact_type}-${artifact.artifact_id}`}
                        className="rounded-3xl border border-slate-200 bg-slate-50 px-4 py-3"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
                            {artifact.artifact_type}
                          </span>
                          <span className="font-mono text-xs text-slate-500">{artifact.artifact_id}</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600">
                          {artifact.producer_role} · {artifact.producer_skill}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              <BehaviorTimeline events={activeConversation.runEvents} />
              <RawTerminalPanel content={activeConversation.rawTerminalLog} />
            </div>
          ) : null}

          {hasConversation ? (
            <div className={densityClasses.gap}>
              {visibleMessages.map((message) => {
                const isUser = message.role === 'user';
                const isAssistant = message.role === 'assistant';
                return (
                  <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'} ${densityClasses.padding}`}>
                    <div className={`flex max-w-[92%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div
                        className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
                          isUser ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-200'
                        }`}
                      >
                        {isUser ? <User2 className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                      </div>
                      <div className={isUser ? 'text-right' : ''}>
                        <div className="mb-2 text-xs font-medium text-slate-400">{isUser ? '你' : 'Research OS'}</div>
                        <div
                          className={`whitespace-pre-wrap rounded-[28px] px-5 py-4 leading-7 ${
                            isUser ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-800 shadow-sm'
                          } ${messageFontClass}`}
                        >
                          {message.content || (message.streaming ? '正在生成...' : '')}
                          {isAssistant && message.streaming ? (
                            <span className="ml-2 inline-flex align-middle text-slate-400">
                              <LoaderCircle className="h-4 w-4 animate-spin" />
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex min-h-[56vh] flex-col items-center justify-center text-center">
              <div className="max-w-2xl">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Research Runtime</p>
                <h2 className="mt-4 text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
                  使用动态 DAG 运行研究任务
                </h2>
                <p className="mt-4 text-base leading-7 text-slate-500">
                  输入一个研究请求后，前端会展示局部 DAG、节点状态、skill/tool 调用、observation、replan 和 artifacts。
                </p>
              </div>

              {uiPreferences.showWelcomeHints ? (
                <div className="mt-10 flex w-full max-w-4xl flex-wrap justify-center gap-3">
                  {PROMPT_TEMPLATES.map((template) => (
                    <button
                      key={template}
                      type="button"
                      onClick={() => updateRunOverrides({ prompt: template })}
                      className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                    >
                      {template}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      <div className="sticky bottom-0 z-10 bg-gradient-to-t from-[var(--app-bg)] via-[var(--app-bg)] to-transparent px-4 pb-6 pt-6 sm:px-6">
        <div className={`mx-auto w-full ${messageWidthClass}`}>
          <div className="rounded-[32px] border border-slate-200 bg-white p-3 shadow-[0_20px_70px_-40px_rgba(15,23,42,0.35)]">
            <textarea
              value={runOverrides.prompt}
              onChange={(event) => updateRunOverrides({ prompt: event.target.value })}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  submitPrompt();
                }
              }}
              placeholder="输入一个研究请求，运行时会按 planner -> executor -> role -> skill -> tool 路径执行。"
              className="min-h-[104px] w-full resize-none rounded-[24px] border-0 bg-transparent px-4 py-3 text-[15px] leading-7 text-slate-900 outline-none placeholder:text-slate-400"
            />
            <div className="mt-2 flex items-center justify-between gap-3 px-2 pb-1">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>{isActiveConversationRunning ? '当前运行进行中，可随时停止。' : 'Enter 发送，Shift+Enter 换行。'}</span>
              </div>
              {isActiveConversationRunning ? (
                <Button onClick={() => void stopRun()} variant="danger" className="rounded-full px-5">
                  <Square className="h-4 w-4" />
                  停止运行
                </Button>
              ) : (
                <Button onClick={submitPrompt} disabled={!runOverrides.prompt.trim()} className="rounded-full px-5">
                  <SendHorizonal className="h-4 w-4" />
                  发送
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
