import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api/client';
import { ApprovalQueue } from './components/ApprovalQueue';
import { FocusLauncher } from './components/FocusLauncher';
import { DashboardTab, Header } from './components/Header';
import { KnowledgeExplorer } from './components/KnowledgeExplorer';
import { QuotaLedgerMonitor } from './components/QuotaLedgerMonitor';
import { RunsTable } from './components/RunsTable';
import { TelemetryStream } from './components/TelemetryStream';

// The "Video Studio" tab is gone. It played a Remotion composition fed by a
// hardcoded Rosetta Stone script, labelled "rendering engine", while rendering
// does not exist (SPEC Phase 7, deferred by D57) and no Run had produced an
// artifact to play. It returns when there is a real RenderArtifact to show.

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<DashboardTab>('dashboard');
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data: runs = [], error: runsError } = useQuery({
    queryKey: ['runs'],
    queryFn: api.getRuns,
    refetchInterval: 5000,
  });

  const { data: gates = [] } = useQuery({
    queryKey: ['gates'],
    queryFn: api.getPendingGates,
    refetchInterval: 5000,
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['runs'] });
    queryClient.invalidateQueries({ queryKey: ['gates'] });
    queryClient.invalidateQueries({ queryKey: ['telemetry'] });
    queryClient.invalidateQueries({ queryKey: ['knowledge'] });
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    setActiveTab('knowledge');
  };

  return (
    <div className="min-h-screen bg-[#0a0b0e] text-[#f8fafc] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingGatesCount={gates.length}
        selectedRunId={selectedRunId}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {runsError && (
          <div className="mb-6 text-xs text-red-400 bg-red-950/50 border border-red-800/50 p-3 rounded-lg font-mono">
            {(runsError as Error).message}
          </div>
        )}

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
            gates={gates}
            onGateActionCompleted={handleRefresh}
            onInspectRun={handleSelectRun}
          />
        )}

        {activeTab === 'knowledge' && <KnowledgeExplorer runId={selectedRunId} />}

        {activeTab === 'telemetry' && (
          <div className="space-y-8">
            <QuotaLedgerMonitor />
            <TelemetryStream runId={selectedRunId} />
          </div>
        )}
      </main>

      <footer className="border-t border-[#272b38] bg-[#12141a] py-4 text-center text-xs text-slate-500 font-mono">
        Atlas · every panel here reads a database row · see docs/STATUS.md for what does not exist yet
      </footer>
    </div>
  );
};
