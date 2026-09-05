import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CircleDot, GitBranch, ShieldQuestion } from 'lucide-react';
import { api } from '../api/client';
import { GateItem, StepItem } from '../api/types';

// `GET /runs/{id}/steps` and `GET /runs/{id}/gates` have existed since Phase 3
// and nothing in the dashboard read either of them, so an operator could see
// that a Run was suspended but not *where* — which of the eighteen stages it
// reached, which one failed, or which Gate is holding it.
//
// Stage names come from the `steps` rows. There is no client-side list of the
// eighteen stages: a hardcoded pipeline would keep rendering after the state
// machine changed, and would show stages for a Run that never reached them
// (**R13**).

interface RunPipelineProps {
  runId?: string;
}

const STEP_STYLE: Record<string, { dot: string; text: string }> = {
  succeeded: { dot: 'bg-emerald-500', text: 'text-emerald-400' },
  running: { dot: 'bg-blue-500 animate-pulse', text: 'text-blue-400' },
  suspended: { dot: 'bg-amber-400', text: 'text-amber-400' },
  failed: { dot: 'bg-red-500', text: 'text-red-400' },
  pending: { dot: 'bg-slate-600', text: 'text-slate-400' },
  skipped: { dot: 'bg-slate-700', text: 'text-slate-500' },
};

const stepStyle = (status: string) =>
  STEP_STYLE[status] ?? { dot: 'bg-slate-600', text: 'text-slate-400' };

const StepRow: React.FC<{ step: StepItem; gate?: GateItem }> = ({ step, gate }) => {
  const style = stepStyle(step.status);
  return (
    <li className="flex items-start gap-3 py-2.5 border-b border-[#1f2430] last:border-0">
      <span className="shrink-0 w-7 text-right text-[11px] font-mono text-slate-600 pt-0.5">
        {step.step_index}
      </span>
      <span className={`shrink-0 mt-1.5 w-2 h-2 rounded-full ${style.dot}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm text-white truncate">{step.step_name}</span>
          <span className={`shrink-0 text-[11px] font-mono uppercase ${style.text}`}>
            {step.status}
          </span>
        </div>
        <p className="text-[11px] font-mono text-slate-500 truncate">
          {step.id}
          {step.output_artifact_ref ? ` · ${step.output_artifact_ref}` : ''}
        </p>
        {step.error && (
          <p className="mt-1 text-[11px] font-mono text-red-400 break-words">{step.error}</p>
        )}
        {gate && (
          <p className="mt-1 inline-flex items-center gap-1.5 text-[11px] font-mono text-amber-400">
            <ShieldQuestion className="w-3 h-3" />
            {gate.gate_type} gate · {gate.status} · {gate.id}
          </p>
        )}
      </div>
    </li>
  );
};

export const RunPipeline: React.FC<RunPipelineProps> = ({ runId }) => {
  const steps = useQuery({
    queryKey: ['run-steps', runId],
    queryFn: () => api.getRunSteps(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });

  const gates = useQuery({
    queryKey: ['run-gates', runId],
    queryFn: () => api.getRunGates(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });

  if (!runId) {
    return (
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl">
        <p className="text-xs text-slate-500 font-mono">
          Select a Run to see which of its stages have run.
        </p>
      </div>
    );
  }

  const gateByStep = new Map((gates.data ?? []).map((g) => [g.step_id, g]));
  const rows = steps.data ?? [];
  const counts = rows.reduce<Record<string, number>>((acc, s) => {
    acc[s.status] = (acc[s.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl shadow-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-[#272b38] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
            <GitBranch className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Pipeline</h3>
            <p className="text-[11px] font-mono text-slate-500">{runId}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono">
          {Object.entries(counts).map(([status, count]) => (
            <span key={status} className={`flex items-center gap-1.5 ${stepStyle(status).text}`}>
              <CircleDot className="w-3 h-3" />
              {count} {status}
            </span>
          ))}
          <span className="text-slate-500">{rows.length} of 18 stages recorded</span>
        </div>
      </div>

      <div className="p-6">
        {steps.error && (
          <p className="text-xs text-red-400 font-mono">{(steps.error as Error).message}</p>
        )}
        {gates.error && (
          <p className="text-xs text-red-400 font-mono">{(gates.error as Error).message}</p>
        )}
        {!steps.error && rows.length === 0 && (
          <p className="text-xs text-slate-500 font-mono">
            {steps.isLoading
              ? 'Loading…'
              : 'No Step rows for this Run. It has been created but has not executed a stage.'}
          </p>
        )}
        <ul>
          {rows.map((step) => (
            <StepRow key={step.id} step={step} gate={gateByStep.get(step.id)} />
          ))}
        </ul>
      </div>
    </div>
  );
};
