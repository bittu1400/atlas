import React from 'react';
import {
  ArrowRight,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  XCircle,
} from 'lucide-react';
import { RunItem, RunStatus } from '../api/types';

// The "Current Stage" and "Focus Subject" columns are gone: `RunResponse`
// carries neither a `current_stage` nor a `config`, so both were read off
// `undefined` and only ever rendered because the mock fallback invented them
// (defect V-03). Stage-by-stage progress lives on the Telemetry tab, which
// reads the Run's actual `steps` rows.

interface RunsTableProps {
  runs: RunItem[];
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

const STATUS_BADGE: Partial<
  Record<RunStatus, { icon: React.ReactNode; label: string; className: string }>
> = {
  completed: {
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    label: 'Completed',
    className: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40',
  },
  suspended: {
    icon: <PauseCircle className="w-3.5 h-3.5" />,
    label: 'Gate suspended',
    className: 'bg-purple-950/60 text-purple-300 border-purple-800/40',
  },
  running: {
    icon: <PlayCircle className="w-3.5 h-3.5" />,
    label: 'Running',
    className: 'bg-blue-950/60 text-blue-400 border-blue-800/40',
  },
  failed: {
    icon: <XCircle className="w-3.5 h-3.5" />,
    label: 'Failed',
    className: 'bg-red-950/60 text-red-400 border-red-800/40',
  },
};

const StatusBadge: React.FC<{ status: RunStatus }> = ({ status }) => {
  const badge = STATUS_BADGE[status];
  if (!badge) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
        {status}
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${badge.className}`}
    >
      {badge.icon} {badge.label}
    </span>
  );
};

export const RunsTable: React.FC<RunsTableProps> = ({
  runs,
  selectedRunId,
  onSelectRun,
}) => (
  <div className="bg-[#161922] border border-[#272b38] rounded-xl overflow-hidden shadow-xl">
    <div className="px-6 py-4 border-b border-[#272b38] flex items-center justify-between">
      <h3 className="text-sm font-bold text-white uppercase tracking-wider">Runs</h3>
      <span className="text-xs text-slate-400 font-mono">{runs.length} total</span>
    </div>

    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-[#272b38] bg-[#12141a] text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
            <th className="py-3 px-6">Run ID</th>
            <th className="py-3 px-6">Topic</th>
            <th className="py-3 px-6">Channel</th>
            <th className="py-3 px-6">Status</th>
            <th className="py-3 px-6">Created</th>
            <th className="py-3 px-6 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#272b38] text-sm">
          {runs.length === 0 && (
            <tr>
              <td colSpan={6} className="py-8 px-6 text-center text-xs text-slate-400">
                No Runs yet.
              </td>
            </tr>
          )}
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className={`cursor-pointer transition-colors ${
                selectedRunId === run.id
                  ? 'bg-orange-950/30 hover:bg-orange-950/40'
                  : 'hover:bg-[#1c202c]'
              }`}
            >
              <td className="py-4 px-6 font-mono text-xs font-semibold text-amber-400">
                {run.id}
              </td>
              <td className="py-4 px-6">
                <div className="font-mono text-xs text-white">{run.topic_id}</div>
                {run.error && (
                  <div className="text-xs text-red-400 mt-0.5 max-w-md truncate" title={run.error}>
                    {run.error}
                  </div>
                )}
              </td>
              <td className="py-4 px-6 font-mono text-xs text-slate-300">{run.channel_id}</td>
              <td className="py-4 px-6">
                <StatusBadge status={run.status} />
              </td>
              <td className="py-4 px-6 text-xs text-slate-400 font-mono">
                {new Date(run.created_at).toLocaleString()}
              </td>
              <td className="py-4 px-6 text-right">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectRun(run.id);
                  }}
                  className="text-xs text-orange-400 hover:text-orange-300 font-medium inline-flex items-center gap-1 bg-orange-950/40 border border-orange-800/40 px-2.5 py-1 rounded cursor-pointer"
                >
                  Inspect <ArrowRight className="w-3 h-3" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);
