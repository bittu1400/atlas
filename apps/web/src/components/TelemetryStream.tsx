import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity } from 'lucide-react';
import { api } from '../api/client';
import { TelemetryEvent } from '../api/types';

// Rows come from `/runs/{id}/telemetry`, which merges the Run's `steps` and its
// metered `model_calls`. The previous version held six hardcoded log lines
// timestamped `Date.now() - 45000` so they always looked live, describing work
// that never happened (defect V-03, rule R4).

interface TelemetryStreamProps {
  runId?: string;
}

const STATUS_COLOR: Record<string, string> = {
  succeeded: 'text-emerald-400',
  success: 'text-emerald-400',
  running: 'text-blue-400',
  suspended: 'text-amber-400',
  failed: 'text-red-400',
  error: 'text-red-400',
  skipped: 'text-slate-500',
};

const EventRow: React.FC<{ event: TelemetryEvent }> = ({ event }) => (
  <li className="flex items-start gap-3 py-2 border-b border-[#1f2430] last:border-0 font-mono text-xs">
    <span className="text-slate-500 shrink-0 w-[92px]">
      {new Date(event.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })}
    </span>
    <span
      className={`shrink-0 w-[88px] uppercase ${
        event.kind === 'model_call' ? 'text-purple-300' : 'text-orange-400'
      }`}
    >
      {event.kind}
    </span>
    <span className="shrink-0 w-[152px] text-slate-300 truncate" title={event.stage}>
      {event.stage}
    </span>
    <span className="flex-1 text-slate-200">{event.event}</span>
    <span className={`shrink-0 ${STATUS_COLOR[event.status] ?? 'text-slate-400'}`}>
      {event.status}
    </span>
  </li>
);

export const TelemetryStream: React.FC<TelemetryStreamProps> = ({ runId }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['telemetry', runId],
    queryFn: () => api.getRunTelemetry(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex items-center gap-3 border-b border-[#272b38] pb-4">
        <div className="p-2.5 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white font-display">Run Telemetry</h2>
          <p className="text-xs text-slate-400">
            Recorded Steps and metered model calls, newest first.
          </p>
        </div>
      </div>

      {!runId && (
        <p className="text-xs text-slate-400">
          Select a Run on the Dashboard tab to see what it recorded.
        </p>
      )}
      {runId && isLoading && <p className="text-xs text-slate-400 font-mono">Loading…</p>}
      {runId && error && (
        <p className="text-xs text-red-400 font-mono">{(error as Error).message}</p>
      )}
      {data && data.length === 0 && (
        <p className="text-xs text-slate-400">This Run has recorded nothing yet.</p>
      )}

      <ul className="max-h-[520px] overflow-y-auto">
        {data?.map((event) => (
          <EventRow key={`${event.kind}-${event.id}`} event={event} />
        ))}
      </ul>
    </div>
  );
};
