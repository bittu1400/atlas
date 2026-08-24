import React, { useState } from 'react';
import { Sparkles, ShieldCheck, HelpCircle } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingGatesCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  pendingGatesCount,
}) => {
  const [showShortcuts, setShowShortcuts] = useState(false);

  return (
    <header className="border-b border-[#272b38] bg-[#12141a] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Channel Info */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-600 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-950/40">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-cinzel text-xl font-bold tracking-wider text-white">ATLAS</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-orange-950/60 text-orange-400 border border-orange-800/50">
                  ORIGINS
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans -mt-0.5">Primary Source Archival Synthesis</p>
            </div>
          </div>

          {/* Active Focus Pill */}
          <div className="hidden lg:flex items-center gap-2 text-xs bg-[#1a1d26] border border-[#272b38] px-3 py-1.5 rounded-full">
            <span className="text-slate-500 font-medium">Active Focus:</span>
            <span className="text-amber-400 font-semibold">History</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-300 font-mono text-[11px]">Rosetta Stone (Q19939)</span>
            <span className="text-slate-600">•</span>
            <span className="text-emerald-400 text-[10px] font-mono uppercase bg-emerald-950/50 px-1.5 py-0.2 rounded border border-emerald-800/40">
              Scope: Soft
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'dashboard'
                ? 'bg-[#272b38] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('approval')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'approval'
                ? 'bg-orange-600 text-white shadow-md shadow-orange-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
            }`}
          >
            Approval Queue
            {pendingGatesCount > 0 && (
              <span className="bg-amber-400 text-slate-950 text-xs font-bold px-1.5 py-0.2 rounded-full animate-pulse">
                {pendingGatesCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'preview'
                ? 'bg-[#272b38] text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
            }`}
          >
            Video Studio
          </button>
          <button
            onClick={() => setActiveTab('knowledge')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'knowledge'
                ? 'bg-[#272b38] text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
            }`}
          >
            Knowledge Graph
          </button>
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'telemetry'
                ? 'bg-[#272b38] text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a1d26]'
            }`}
          >
            Telemetry & Quota
          </button>
        </nav>

        {/* System Telemetry Badges */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#1a1d26] border border-[#272b38] px-3 py-1.5 rounded-lg text-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-slate-300 font-mono text-[11px]">API Online</span>
          </div>

          <button
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="text-slate-400 hover:text-slate-200 p-2 rounded-lg hover:bg-[#1a1d26] transition-colors cursor-pointer"
            title="Keyboard Shortcuts"
          >
            <HelpCircle className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Shortcuts Modal / Tooltip */}
      {showShortcuts && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-orange-500" />
              Operator Keyboard Shortcuts
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Approve current Gate</span>
                <kbd className="bg-[#272b38] text-amber-400 font-mono px-2 py-0.5 rounded text-xs">A</kbd>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Reject Gate (Structured Critique)</span>
                <kbd className="bg-[#272b38] text-red-400 font-mono px-2 py-0.5 rounded text-xs">R</kbd>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Play / Pause Video Preview</span>
                <kbd className="bg-[#272b38] text-slate-200 font-mono px-2 py-0.5 rounded text-xs">Space</kbd>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-[#272b38]">
                <span className="text-slate-300">Next / Previous Beat</span>
                <kbd className="bg-[#272b38] text-slate-200 font-mono px-2 py-0.5 rounded text-xs">← / →</kbd>
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
