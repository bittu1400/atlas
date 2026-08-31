import React, { useState } from 'react';
import { AlertOctagon, Ban, GitBranch, RotateCcw, X } from 'lucide-react';
import { RejectGatePayload, RejectionAction } from '../api/types';

// The payload matches `RejectGateRequest`: a flat object with `target_ref`,
// `rubric_dimension`, `reason` and `action`. It used to send a nested
// `{rejection_type, critique: {...}}` shape the endpoint has never accepted.

interface StructuredRejectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: RejectGatePayload) => Promise<void>;
}

const ACTIONS: Array<{ value: RejectionAction; label: string; icon: React.ReactNode }> = [
  { value: 'regenerate', label: 'Regenerate', icon: <RotateCcw className="w-4 h-4" /> },
  { value: 'branch', label: 'Branch Angle', icon: <GitBranch className="w-4 h-4" /> },
  { value: 'abandon', label: 'Abandon Run', icon: <Ban className="w-4 h-4" /> },
];

const RUBRIC_DIMENSIONS = [
  'sourcing_integrity',
  'hook_strength',
  'narrative_arc',
  'language_craft',
  'factual_density',
  'novelty',
  'visual_coherence',
  'technical_compliance',
];

export const StructuredRejectionModal: React.FC<StructuredRejectionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [action, setAction] = useState<RejectionAction>('regenerate');
  const [rubricDimension, setRubricDimension] = useState('sourcing_integrity');
  const [targetRef, setTargetRef] = useState('');
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || !targetRef.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        actor_id: 'operator-web',
        target_ref: targetRef.trim(),
        rubric_dimension: rubricDimension,
        reason: reason.trim(),
        action,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#161922] border border-[#272b38] rounded-xl max-w-xl w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#272b38] pb-4 mb-5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-red-950/60 border border-red-800/50 text-red-400">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Structured Gate Rejection</h3>
              <p className="text-xs text-slate-400">
                Feedback is stored on the Approval row and drives the rework cycle.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-200 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <span className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Action
            </span>
            <div className="grid grid-cols-3 gap-2">
              {ACTIONS.map((a) => (
                <button
                  key={a.value}
                  type="button"
                  onClick={() => setAction(a.value)}
                  className={`py-2.5 px-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                    action === a.value
                      ? 'bg-amber-950/60 border-amber-500 text-amber-300 font-bold'
                      : 'bg-[#1e2230] border-[#2d3345] text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {a.icon}
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label
              htmlFor="rubric-dimension"
              className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Rubric Dimension
            </label>
            <select
              id="rubric-dimension"
              value={rubricDimension}
              onChange={(e) => setRubricDimension(e.target.value)}
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-red-500"
            >
              {RUBRIC_DIMENSIONS.map((dim) => (
                <option key={dim} value={dim}>
                  {dim}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="target-ref"
              className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Target Reference <span className="text-red-400">*</span>
            </label>
            <input
              id="target-ref"
              type="text"
              value={targetRef}
              onChange={(e) => setTargetRef(e.target.value)}
              placeholder="beat_03, ast_…, or the Step ID under review"
              required
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-red-500"
            />
          </div>

          <div>
            <label
              htmlFor="critique"
              className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Critique <span className="text-red-400">*</span>
            </label>
            <textarea
              id="critique"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="What specifically fails, and what would make it pass."
              required
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg p-3 text-sm text-white focus:outline-none focus:border-red-500"
            />
          </div>

          {error && (
            <div className="text-red-400 text-xs bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg font-mono">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-[#272b38]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-[#272b38] hover:bg-[#343a4c] text-white text-sm font-medium rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim() || !targetRef.trim()}
              className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-red-950/60 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Submitting…' : 'Reject with Critique'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
