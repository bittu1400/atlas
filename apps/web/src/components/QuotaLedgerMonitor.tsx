import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap } from 'lucide-react';
import { api } from '../api/client';

// Numbers come from `/quota`, which sums `quota_ledger`. The previous version
// printed "18 / 1,500 RPD (1.2%)" and "RTX 5070 8GB" as literals, in every
// environment, with no request behind them (defect V-03).

export const QuotaLedgerMonitor: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['quota'],
    queryFn: api.getQuota,
    refetchInterval: 10000,
  });

  if (isLoading) {
    return <p className="text-xs text-slate-400 font-mono">Loading quota…</p>;
  }
  if (error) {
    return <p className="text-xs text-red-400 font-mono">{(error as Error).message}</p>;
  }

  const providers = Object.entries(data?.providers ?? {});

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {providers.map(([name, usage]) => (
        <div
          key={name}
          className="bg-[#161922] border border-[#272b38] rounded-xl p-5 shadow-xl space-y-3"
        >
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <h4 className="text-sm font-bold text-white capitalize">{name}</h4>
            </div>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded border ${
                usage.status === 'active'
                  ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/40'
                  : 'text-amber-400 bg-amber-950/60 border-amber-800/40'
              }`}
            >
              {usage.status}
            </span>
          </div>

          <dl className="space-y-1 text-xs font-mono">
            <div className="flex justify-between">
              <dt className="text-slate-400">Requests left this minute</dt>
              <dd className="text-white font-bold">{usage.rpm_remaining}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Requests left today</dt>
              <dd className="text-white font-bold">{usage.rpd_remaining}</dd>
            </div>
          </dl>
        </div>
      ))}
    </div>
  );
};
