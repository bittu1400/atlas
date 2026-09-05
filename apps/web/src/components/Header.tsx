import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HelpCircle, ShieldCheck, Sparkles } from 'lucide-react';
import { api } from '../api/client';

// Two things on this bar used to be decoration: an "Active Focus: History •
// Rosetta Stone (Q19939)" pill that named a Focus no Run had ever captured, and
// an "API Online" badge with a pulsing green dot that was a literal, shown
// whether or not the API answered (defect V-03). The pill now shows the Run
// under inspection; the badge polls `/health`.

export type DashboardTab =
  | 'dashboard'
  | 'catalog'
  | 'approval'
  | 'pipeline'
  | 'knowledge'
  | 'telemetry';

interface HeaderProps {
  activeTab: DashboardTab;
  setActiveTab: (tab: DashboardTab) => void;
  pendingGatesCount: number;
  selectedRunId?: string;
}

const TABS: Array<{ id: DashboardTab; label: string }> = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'catalog', label: 'Catalog' },
  { id: 'approval', label: 'Approval Queue' },
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'telemetry', label: 'Telemetry & Quota' },
];

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  pendingGatesCount,
  selectedRunId,
}) => {
  const [showShortcuts, setShowShortcuts] = useState(false);
  const { data: health, isError: healthFailed } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 15000,
    retry: false,
  });

  const apiUp = Boolean(health) && !healthFailed;

  return (
    <header className="border-b border-[#272b38] bg-[#12141a] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <button
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setActiveTab('dashboard')}
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-600 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-950/40">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="text-left">
              <span className="font-cinzel text-xl font-bold tracking-wider text-white">
                ATLAS
              </span>
              <p className="text-[11px] text-slate-400 -mt-0.5">
                Primary Source Archival Synthesis
              </p>
            </div>
          </button>

          {selectedRunId && (
            <div className="hidden lg:flex items-center gap-2 text-xs bg-[#1a1d26] border border-[#272b38] px-3 py-1.5 rounded-full">
              <span className="text-slate-500 font-medium">Inspecting:</span>
              <span className="text-amber-400 font-mono text-[11px]">{selectedRunId}</span>
            </div>
          )}
        </div>

        <nav className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === tab.id
                  ? tab.id === 'approval'
                    ? 'bg-orange-600 text-white shadow-md shadow-orange-950/50'
                    : 'bg-[#272b38] text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
              }`}
            >
              {tab.label}
              {tab.id === 'approval' && pendingGatesCount > 0 && (
                <span className="bg-amber-400 text-slate-950 text-xs font-bold px-1.5 rounded-full">
                  {pendingGatesCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#1a1d26] border border-[#272b38] px-3 py-1.5 rounded-lg text-xs">
            <span
              className={`inline-flex rounded-full h-2 w-2 ${
                apiUp ? 'bg-emerald-500' : 'bg-red-500'
              }`}
            />
            <span className="text-slate-300 font-mono text-[11px]">
              {apiUp ? 'API online' : 'API unreachable'}
            </span>
          </div>

          <button
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="text-slate-400 hover:text-slate-200 p-2 rounded-lg hover:bg-[#1a1d26] transition-colors cursor-pointer"
            title="Keyboard shortcuts"
          >
            <HelpCircle className="w-5 h-5" />
          </button>
        </div>
      </div>

      {showShortcuts && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-orange-500" />
              Operator keyboard shortcuts
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Approve current Gate</span>
                <kbd className="bg-[#272b38] text-amber-400 font-mono px-2 py-0.5 rounded text-xs">
                  A
                </kbd>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Reject Gate with critique</span>
                <kbd className="bg-[#272b38] text-red-400 font-mono px-2 py-0.5 rounded text-xs">
                  R
                </kbd>
              </div>
            </div>
            <button
              onClick={() => setShowShortcuts(false)}
              className="mt-6 w-full py-2 bg-[#272b38] hover:bg-[#343a4c] text-white rounded-lg text-sm font-medium transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
