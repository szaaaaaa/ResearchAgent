import React, { useState } from 'react';
import { AppProvider } from './store';
import { Sidebar } from './components/Sidebar';
import { RunTab } from './components/tabs/RunTab';
import { CredentialsTab } from './components/tabs/CredentialsTab';
import { DataSourcesTab } from './components/tabs/DataSourcesTab';
import { RetrievalTab } from './components/tabs/RetrievalTab';
import { StrategyTab } from './components/tabs/StrategyTab';
import { MultimodalTab } from './components/tabs/MultimodalTab';
import { PathsTab } from './components/tabs/PathsTab';
import { SafetyTab } from './components/tabs/SafetyTab';
import { AdvancedTab } from './components/tabs/AdvancedTab';

const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('run');

  const renderTab = () => {
    switch (activeTab) {
      case 'run': return <RunTab />;
      case 'credentials': return <CredentialsTab />;
      case 'datasources': return <DataSourcesTab />;
      case 'retrieval': return <RetrievalTab />;
      case 'strategy': return <StrategyTab />;
      case 'multimodal': return <MultimodalTab />;
      case 'paths': return <PathsTab />;
      case 'safety': return <SafetyTab />;
      case 'advanced': return <AdvancedTab />;
      default: return <RunTab />;
    }
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] text-slate-900 font-sans overflow-hidden selection:bg-blue-100 selection:text-blue-900">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 overflow-y-auto relative">
        {/* Modern subtle gradient background */}
        <div className="absolute top-0 left-0 right-0 h-[500px] bg-gradient-to-b from-blue-50/60 via-white/30 to-transparent -z-10 pointer-events-none" />
        <div className="p-8 lg:p-12 max-w-5xl mx-auto">
          {renderTab()}
        </div>
      </main>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
