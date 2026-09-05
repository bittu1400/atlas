import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle, Info, XCircle } from 'lucide-react';
import { api } from '../api/client';
import { GateItem, RejectGatePayload } from '../api/types';
import { StructuredRejectionModal } from './StructuredRejectionModal';

// A failed approve or reject is now shown as a failure.
//
// This component used to catch the error, log "Simulated approval completed in
// dev mode" and call `onGateActionCompleted()` — telling the operator their
// human decision had been recorded when no Approval row was written. That is a
// human gate reported as passed without a human decision reaching the database
// (defect V-03, rules R5 and R8). It also drew the gate's assets, script beats
// and a passing quality rubric from `gate.metadata`, a field the API does not
// return; those panels are gone until an endpoint exists to fill them.

interface ApprovalQueueProps {
  gates: GateItem[];
  onGateActionCompleted: () => void;
  onInspectRun: (runId: string) => void;
}

export const ApprovalQueue: React.FC<ApprovalQueueProps> = ({
  gates,
  onGateActionCompleted,
  onInspectRun,
}) => {
  const [selectedGateId, setSelectedGateId] = useState<string>('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedGate = gates.find((g) => g.id === selectedGateId) ?? gates[0];

  const handleApprove = useCallback(async () => {
    if (!selectedGate) return;
    setIsApproving(true);
    setError(null);
    try {
      await api.approveGate(selectedGate.id, { actor_id: 'operator-web' });
      onGateActionCompleted();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsApproving(false);
    }
  }, [selectedGate, onGateActionCompleted]);

  const handleRejectSubmit = async (payload: RejectGatePayload) => {
    if (!selectedGate) return;
    await api.rejectGate(selectedGate.id, payload);
    onGateActionCompleted();
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) return;
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        void handleApprove();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        setShowRejectModal(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleApprove]);

  if (!selectedGate) {
    return (
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-12 text-center shadow-xl">
        <div className="w-12 h-12 rounded-full bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 mx-auto flex items-center justify-center mb-3">
          <CheckCircle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-white mb-1">No pending Gates</h3>
        <p className="text-xs text-slate-400">Nothing is waiting on an operator decision.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {gates.length > 1 && (
        <div className="flex gap-2 bg-[#12141a] p-2 rounded-lg border border-[#272b38] overflow-x-auto">
          {gates.map((g) => (
            <button
              key={g.id}
              onClick={() => setSelectedGateId(g.id)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all whitespace-nowrap ${
                selectedGate.id === g.id
                  ? 'bg-orange-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {g.step_id}
            </button>
          ))}
        </div>
      )}

      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono uppercase bg-amber-950/60 border border-amber-800/40 text-amber-400 px-2.5 py-0.5 rounded font-bold">
                {selectedGate.gate_type} gate
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Run: {selectedGate.run_id}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white font-mono">{selectedGate.step_id}</h2>
            <p className="text-xs text-slate-300 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-orange-400" />
              Requested {new Date(selectedGate.requested_at).toLocaleString()} · status{' '}
              {selectedGate.status}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowRejectModal(true)}
              className="px-4 py-2.5 bg-[#272b38] hover:bg-red-950/60 hover:text-red-300 border border-transparent hover:border-red-800/50 text-slate-300 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer"
            >
              <XCircle className="w-4 h-4 text-red-400" />
              Reject (R)
            </button>
            <button
              onClick={handleApprove}
              disabled={isApproving}
              className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-sm font-bold flex items-center gap-2 shadow-lg shadow-emerald-950/50 transition-all disabled:opacity-50 cursor-pointer"
            >
              <CheckCircle className="w-4 h-4" />
              {isApproving ? 'Approving…' : 'Approve & Resume (A)'}
            </button>
          </div>
        </div>

        {error && (
          <div className="text-red-400 text-xs bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg font-mono">
            Gate action failed, nothing was recorded: {error}
          </div>
        )}

        <div className="border-t border-[#272b38] pt-4">
          <p className="text-xs text-slate-400">
            Review what this Run actually produced before deciding.{' '}
            <button
              onClick={() => onInspectRun(selectedGate.run_id)}
              className="text-teal-400 hover:text-teal-300 underline decoration-dotted cursor-pointer"
            >
              Open its Knowledge Object and telemetry
            </button>
            .
          </p>
        </div>
      </div>

      <StructuredRejectionModal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onSubmit={handleRejectSubmit}
      />
    </div>
  );
};
