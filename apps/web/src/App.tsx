import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api/client';
import { Header } from './components/Header';
import { FocusLauncher } from './components/FocusLauncher';
import { RunsTable } from './components/RunsTable';
import { ApprovalQueue } from './components/ApprovalQueue';
import { VideoPlayerPreview } from './components/VideoPlayerPreview';
import { TelemetryStream } from './components/TelemetryStream';
import { QuotaLedgerMonitor } from './components/QuotaLedgerMonitor';
import { KnowledgeExplorer } from './components/KnowledgeExplorer';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: api.getRuns,
    refetchInterval: 5000,
  });

  const { data: gates = [] } = useQuery({
    queryKey: ['gates'],
    queryFn: api.getGates,
    refetchInterval: 5000,
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['runs'] });
    queryClient.invalidateQueries({ queryKey: ['gates'] });
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    setActiveTab('approval');
  };

  return (
    <div className="min-h-screen bg-[#0a0b0e] text-[#f8fafc] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingGatesCount={gates.filter((g) => g.status === 'open').length}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <FocusLauncher onRunCreated={handleRefresh} />
            <RunsTable
              runs={runs}
              selectedRunId={selectedRunId}
              onSelectRun={handleSelectRun}
            />
          </div>
        )}

        {activeTab === 'approval' && (
          <ApprovalQueue
            gates={gates.filter((g) => g.status === 'open')}
            onGateActionCompleted={handleRefresh}
          />
        )}

        {activeTab === 'preview' && <VideoPlayerPreview />}

        {activeTab === 'knowledge' && <KnowledgeExplorer />}

        {activeTab === 'telemetry' && (
          <div className="space-y-8">
            <QuotaLedgerMonitor />
            <TelemetryStream />
          </div>
        )}
      </main>

      <footer className="border-t border-[#272b38] bg-[#12141a] py-4 text-center text-xs text-slate-500 font-mono">
        Atlas Video Studio • Free-Tier Autonomous Synthesis Engine • Invariants 1–10 Enforced
      </footer>
    </div>
  );
};
