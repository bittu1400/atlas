import React, { useState } from 'react';
import { RejectGatePayload } from '../api/types';
import { X, AlertOctagon, RotateCcw, GitBranch, Ban } from 'lucide-react';

interface StructuredRejectionModalProps {
  gateId?: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: RejectGatePayload) => Promise<void>;
}

export const StructuredRejectionModal: React.FC<StructuredRejectionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [rejectionType, setRejectionType] = useState<'regenerate' | 'branch' | 'abandon'>('regenerate');
  const [rubricDimension, setRubricDimension] = useState('sourcing_integrity');
  const [targetBeatIndex, setTargetBeatIndex] = useState<number | undefined>(1);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        actor_id: 'operator-web',
        rejection_type: rejectionType,
        critique: {
          rubric_dimension: rubricDimension,
          target_beat_index: targetBeatIndex,
          reason: reason.trim(),
        },
      });
      onClose();
    } catch (err) {
      console.error('Failed to submit rejection', err);
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
              <p className="text-xs text-slate-400">Feedback is typed into downstream regeneration cycles</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Rejection Route Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Rejection Route Action
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setRejectionType('regenerate')}
                className={`py-2.5 px-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  rejectionType === 'regenerate'
                    ? 'bg-amber-950/60 border-amber-500 text-amber-300 font-bold'
                    : 'bg-[#1e2230] border-[#2d3345] text-slate-400 hover:text-slate-200'
                }`}
              >
                <RotateCcw className="w-4 h-4" />
                Regenerate
              </button>
              <button
                type="button"
                onClick={() => setRejectionType('branch')}
                className={`py-2.5 px-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  rejectionType === 'branch'
                    ? 'bg-purple-950/60 border-purple-500 text-purple-300 font-bold'
                    : 'bg-[#1e2230] border-[#2d3345] text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitBranch className="w-4 h-4" />
                Branch Angle
              </button>
              <button
                type="button"
                onClick={() => setRejectionType('abandon')}
                className={`py-2.5 px-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  rejectionType === 'abandon'
                    ? 'bg-red-950/60 border-red-500 text-red-300 font-bold'
                    : 'bg-[#1e2230] border-[#2d3345] text-slate-400 hover:text-slate-200'
                }`}
              >
                <Ban className="w-4 h-4" />
                Abandon Run
              </button>
            </div>
          </div>

          {/* Rubric Dimension */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Rubric Dimension Violated
            </label>
            <select
              value={rubricDimension}
              onChange={(e) => setRubricDimension(e.target.value)}
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-red-500"
            >
              <option value="sourcing_integrity">Sourcing Integrity (Missing primary source or weak evidence)</option>
              <option value="hook_strength">Hook Strength (Weak first 3 seconds)</option>
              <option value="narrative_arc">Narrative Arc & Payoff</option>
              <option value="language_craft">Language Craft (AI generic phrasing detected)</option>
              <option value="factual_density">Factual Density (Low insight per second)</option>
              <option value="visual_coherence">Visual Coherence & Image Relevance</option>
              <option value="technical_compliance">Technical Compliance (Safe margins / pacing exceeded)</option>
            </select>
          </div>

          {/* Target Beat or Asset */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Target Beat Index (Optional)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={targetBeatIndex || ''}
              onChange={(e) => setTargetBeatIndex(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="e.g. 2"
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-red-500 font-mono"
            />
          </div>

          {/* Detailed Reason */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Critique & Feedback Explanation <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain precisely why this asset/beat fails the rubric so the next LLM prompt cycle corrects it..."
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg p-3 text-sm text-white focus:outline-none focus:border-red-500"
              required
            />
          </div>

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
              disabled={isSubmitting || !reason.trim()}
              className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-red-950/60 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Submitting...' : 'Reject with Critique (R)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
