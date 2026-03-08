import React from 'react';
import { Play, Key, Database, Search, Brain, Image as ImageIcon, Folder, Shield, Settings } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'run', label: '运行', icon: Play },
    { id: 'credentials', label: '凭证与模型', icon: Key },
    { id: 'datasources', label: '数据源', icon: Database },
    { id: 'retrieval', label: '检索与索引', icon: Search },
    { id: 'strategy', label: '研究策略', icon: Brain },
    { id: 'multimodal', label: '多模态摄取', icon: ImageIcon },
    { id: 'paths', label: '路径与存储', icon: Folder },
    { id: 'safety', label: '安全与预算', icon: Shield },
    { id: 'advanced', label: '高级', icon: Settings },
  ];

  return (
    <div className="w-72 bg-white/80 backdrop-blur-xl border-r border-slate-200/60 flex flex-col h-full z-10 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.05)]">
      <div className="p-6 pb-4">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-3 tracking-tight">
          <div className="p-2 bg-blue-600 rounded-xl shadow-sm shadow-blue-600/20">
            <Brain className="w-5 h-5 text-white" />
          </div>
          ResearchAgent
        </h1>
        <p className="text-xs text-slate-400 mt-2 font-mono ml-12">v1.0.0 // Config</p>
      </div>
      <nav className="flex-1 px-4 space-y-1.5 overflow-y-auto pt-4">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-blue-50 text-blue-700 shadow-sm shadow-blue-100/50'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
};
