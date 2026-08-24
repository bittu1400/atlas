import React from 'react';
import { RunItem } from '../api/types';
import { PlayCircle, CheckCircle2, PauseCircle, XCircle, ArrowRight } from 'lucide-react';

interface RunsTableProps {
  runs: RunItem[];
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

export const RunsTable: React.FC<RunsTableProps> = ({
  runs,
  selectedRunId,
  onSelectRun,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case 'suspended':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-950/60 text-purple-300 border border-purple-800/40 animate-pulse">
            <PauseCircle className="w-3.5 h-3.5" /> Gate Suspended
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-950/60 text-blue-400 border border-blue-800/40">
            <PlayCircle className="w-3.5 h-3.5" /> Running
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-950/60 text-red-400 border border-red-800/40">
            <XCircle className="w-3.5 h-3.5" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl overflow-hidden shadow-xl">
      <div className="px-6 py-4 border-b border-[#272b38] flex items-center justify-between">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          Synthesis Runs & Pipeline State
        </h3>
        <span className="text-xs text-slate-400 font-mono">{runs.length} Total Runs</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#272b38] bg-[#12141a] text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
              <th className="py-3 px-6">Run ID</th>
              <th className="py-3 px-6">Focus Subject</th>
              <th className="py-3 px-6">Current Stage</th>
              <th className="py-3 px-6">Status</th>
              <th className="py-3 px-6">Created</th>
              <th className="py-3 px-6 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#272b38] text-sm">
            {runs.map((run) => {
              const isSelected = selectedRunId === run.id;
              const focusNote = (run.config?.note as string) || (run.config?.focus_note as string) || 'Primary Archive Topic';
              const focusField = (run.config?.field as string) || (run.config?.focus_field as string) || 'Origins';

              return (
                <tr
                  key={run.id}
                  onClick={() => onSelectRun(run.id)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-orange-950/30 hover:bg-orange-950/40'
                      : 'hover:bg-[#1c202c]'
                  }`}
                >
                  <td className="py-4 px-6 font-mono text-xs font-semibold text-amber-400">
                    {run.id}
                  </td>
                  <td className="py-4 px-6">
                    <div className="font-semibold text-white">{focusNote}</div>
                    <div className="text-xs text-slate-400">{focusField}</div>
                  </td>
                  <td className="py-4 px-6">
                    <span className="text-xs font-mono uppercase bg-[#1f2430] border border-[#2d3345] px-2 py-0.5 rounded text-slate-300">
                      {run.current_stage.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-4 px-6">{getStatusBadge(run.status)}</td>
                  <td className="py-4 px-6 text-xs text-slate-400 font-mono">
                    {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
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
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
