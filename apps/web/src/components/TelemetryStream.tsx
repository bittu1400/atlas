import React, { useState } from 'react';
import { Activity } from 'lucide-react';

interface TelemetryLog {
  id: string;
  timestamp: string;
  stage: string;
  event: string;
  status: 'info' | 'success' | 'warn' | 'error';
}

export const TelemetryStream: React.FC = () => {
  const [logs] = useState<TelemetryLog[]>([
    {
      id: 'log-1',
      timestamp: new Date(Date.now() - 45000).toISOString(),
      stage: 'idea_discovery',
      event: 'Focus bound to Wikidata Q19939 (Rosetta Stone)',
      status: 'info',
    },
    {
      id: 'log-2',
      timestamp: new Date(Date.now() - 38000).toISOString(),
      stage: 'research',
      event: 'Tier-0 fetch: 8 primary documents snapshotted (SHA-256 verified)',
      status: 'info',
    },
    {
      id: 'log-3',
      timestamp: new Date(Date.now() - 25000).toISOString(),
      stage: 'claim_extraction',
      event: 'Extracted 14 verified Claims from primary sources',
      status: 'success',
    },
    {
      id: 'log-4',
      timestamp: new Date(Date.now() - 15000).toISOString(),
      stage: 'fact_verification',
      event: '0 contradictions detected across Demotic & Greek translations',
      status: 'success',
    },
    {
      id: 'log-5',
      timestamp: new Date(Date.now() - 8000).toISOString(),
      stage: 'script',
      event: 'Script written: 11 beats, 138 words (100% within 60s word budget)',
      status: 'success',
    },
    {
      id: 'log-6',
      timestamp: new Date(Date.now() - 2000).toISOString(),
      stage: 'asset_selection',
      event: 'Gate suspended: Human operator review required for Invariant 9 compliance',
      status: 'warn',
    },
  ]);

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-[#272b38] pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Live Pipeline Telemetry & SSE Stream</h3>
            <p className="text-xs text-slate-400 font-mono">Channel: ORIGINS • Event Stream: /events/runs/run-8323-001</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs text-emerald-400 font-mono">Stream Active</span>
        </div>
      </div>

      <div className="bg-[#0a0b0e] border border-[#272b38] rounded-lg p-4 font-mono text-xs max-h-96 overflow-y-auto space-y-2">
        {logs.map((log) => {
          const colorClass =
            log.status === 'success'
              ? 'text-emerald-400'
              : log.status === 'warn'
              ? 'text-amber-400'
              : log.status === 'error'
              ? 'text-red-400'
              : 'text-slate-300';

          return (
            <div key={log.id} className="flex items-start gap-3 py-1 border-b border-[#1a1d26] last:border-0">
              <span className="text-slate-500 whitespace-nowrap">
                {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className="text-orange-400 uppercase font-semibold text-[10px] px-1.5 py-0.2 rounded bg-orange-950/50 border border-orange-800/40 whitespace-nowrap">
                {log.stage}
              </span>
              <span className={`flex-1 ${colorClass}`}>{log.event}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
