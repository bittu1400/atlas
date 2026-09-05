import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { RunItem } from '../api/types';
import { api } from '../api/client';

// Counts, not gauges. Every number here is `rows.filter(...).length` over data
// already fetched for the panels below — nothing is estimated, extrapolated or
// held as a literal, and a count of zero is shown as zero (**R13**).

interface RunSummaryProps {
  runs: RunItem[];
  pendingGates: number;
}

const Tile: React.FC<{
  label: string;
  value: number | string;
  note: string;
  accent: string;
}> = ({ label, value, note, accent }) => (
  <div className="bg-[#161922] border border-[#272b38] rounded-xl p-5 shadow-xl">
    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
    <p className={`mt-2 text-2xl font-bold font-mono ${accent}`}>{value}</p>
    <p className="mt-1 text-[11px] text-slate-500 leading-relaxed">{note}</p>
  </div>
);

export const RunSummary: React.FC<RunSummaryProps> = ({ runs, pendingGates }) => {
  const topics = useQuery({ queryKey: ['topics'], queryFn: api.getTopics });

  const count = (status: string) => runs.filter((r) => r.status === status).length;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <Tile
        label="Topics"
        value={(topics.data ?? []).length}
        note="Candidate subjects available to launch"
        accent="text-white"
      />
      <Tile
        label="Runs"
        value={runs.length}
        note="Every execution recorded, all statuses"
        accent="text-white"
      />
      <Tile
        label="Running"
        value={count('running')}
        note="Executing a stage right now"
        accent="text-blue-400"
      />
      <Tile
        label="Awaiting a human"
        value={pendingGates}
        note="Gates suspended for an operator decision"
        accent={pendingGates > 0 ? 'text-amber-400' : 'text-slate-400'}
      />
      <Tile
        label="Failed"
        value={count('failed')}
        note="A stage raised and the Run stopped"
        accent={count('failed') > 0 ? 'text-red-400' : 'text-slate-400'}
      />
    </div>
  );
};
