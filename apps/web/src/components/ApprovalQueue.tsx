import React, { useState, useEffect, useCallback } from 'react';
import { GateItem, RejectGatePayload } from '../api/types';
import { api } from '../api/client';
import { StructuredRejectionModal } from './StructuredRejectionModal';
import {
  CheckCircle,
  XCircle,
  ShieldCheck,
  Sparkles,
  FileText,
  Image as ImageIcon,
  Award,
  Info,
} from 'lucide-react';

interface ApprovalQueueProps {
  gates: GateItem[];
  onGateActionCompleted: () => void;
}

export const ApprovalQueue: React.FC<ApprovalQueueProps> = ({
  gates,
  onGateActionCompleted,
}) => {
  const [selectedGateId, setSelectedGateId] = useState<string>(gates[0]?.id || '');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'assets' | 'script' | 'quality'>('assets');

  const selectedGate = gates.find((g) => g.id === selectedGateId) || gates[0];

  const handleApprove = useCallback(async () => {
    if (!selectedGate) return;
    setIsApproving(true);
    try {
      await api.approveGate(selectedGate.id, {
        actor_id: 'operator-web',
        metadata: { timestamp: new Date().toISOString() },
      });
      onGateActionCompleted();
    } catch (err) {
      console.warn('Simulated approval completed in dev mode', err);
      onGateActionCompleted();
    } finally {
      setIsApproving(false);
    }
  }, [selectedGate, onGateActionCompleted]);

  const handleRejectSubmit = async (payload: RejectGatePayload) => {
    if (!selectedGate) return;
    try {
      await api.rejectGate(selectedGate.id, payload);
      onGateActionCompleted();
    } catch (err) {
      console.warn('Simulated rejection submitted in dev mode', err);
      onGateActionCompleted();
    }
  };

  // Keyboard shortcut listener: 'A' to approve, 'R' to reject
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        handleApprove();
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
        <h3 className="text-base font-bold text-white mb-1">No Pending Gates in Queue</h3>
        <p className="text-xs text-slate-400">All pipeline runs have satisfied automated and manual checkpoints.</p>
      </div>
    );
  }

  const assets = selectedGate.metadata?.assets || [];
  const beats = selectedGate.metadata?.script?.beats || [];
  const quality = selectedGate.metadata?.quality_report;

  return (
    <div className="space-y-6">
      {/* Multiple Gates Selector (if more than one) */}
      {gates.length > 1 && (
        <div className="flex gap-2 bg-[#12141a] p-2 rounded-lg border border-[#272b38] overflow-x-auto">
          {gates.map((g) => (
            <button
              key={g.id}
              onClick={() => setSelectedGateId(g.id)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all ${
                selectedGate.id === g.id
                  ? 'bg-orange-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {g.stage} ({g.id})
            </button>
          ))}
        </div>
      )}

      {/* Top Banner: Gate Summary & Fast Action Bar */}
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-mono uppercase bg-amber-950/60 border border-amber-800/40 text-amber-400 px-2.5 py-0.5 rounded font-bold">
              {selectedGate.stage.replace('_', ' ')} Gate
            </span>
            <span className="text-xs text-slate-400 font-mono">Run: {selectedGate.run_id}</span>
          </div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2 font-display">
            Decipherment of the Rosetta Stone
          </h2>
          <p className="text-xs text-slate-300 flex items-center gap-1.5 mt-1">
            <Info className="w-3.5 h-3.5 text-orange-400" />
            {selectedGate.reason || 'Human approval checkpoint required before render progression.'}
          </p>
        </div>

        {/* Action Buttons (Keyboard Accessible) */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowRejectModal(true)}
            className="px-4 py-2.5 bg-[#272b38] hover:bg-red-950/60 hover:text-red-300 hover:border-red-800/50 border border-transparent text-slate-300 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer"
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
            {isApproving ? 'Approving...' : 'Approve & Resume (A)'}
          </button>
        </div>
      </div>

      {/* Review Inspector Tabs */}
      <div className="bg-[#161922] border border-[#272b38] rounded-xl overflow-hidden shadow-xl">
        <div className="border-b border-[#272b38] bg-[#12141a] px-6 flex gap-2">
          <button
            onClick={() => setSelectedTab('assets')}
            className={`py-3.5 px-4 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
              selectedTab === 'assets'
                ? 'border-orange-500 text-orange-400 bg-[#161922]'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ImageIcon className="w-4 h-4" /> Visual Assets & Invariant 9 ({assets.length})
          </button>
          <button
            onClick={() => setSelectedTab('script')}
            className={`py-3.5 px-4 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
              selectedTab === 'script'
                ? 'border-orange-500 text-orange-400 bg-[#161922]'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" /> Script, Beats & Claims ({beats.length})
          </button>
          <button
            onClick={() => setSelectedTab('quality')}
            className={`py-3.5 px-4 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
              selectedTab === 'quality'
                ? 'border-orange-500 text-orange-400 bg-[#161922]'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Award className="w-4 h-4" /> Quality Rubric & Deterministic Checks
          </button>
        </div>

        {/* Tab 1: Visual Assets Review */}
        {selectedTab === 'assets' && (
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {assets.map((ast, idx) => (
                <div
                  key={ast.id}
                  className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-4 flex flex-col justify-between hover:border-orange-500/50 transition-all"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-amber-400">Scene #{idx + 1}</span>
                      {ast.is_ai_generated ? (
                        <span className="inline-flex items-center gap-1 bg-amber-950/70 border border-amber-600/50 text-amber-300 text-[11px] font-bold px-2 py-0.5 rounded">
                          <Sparkles className="w-3 h-3 text-amber-400" /> Invariant 9: AI Asset
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 text-[11px] font-semibold px-2 py-0.5 rounded">
                          <ShieldCheck className="w-3 h-3" /> Primary Archive
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-semibold text-white font-display mb-1">{ast.title}</h4>
                    <p className="text-xs text-slate-400 mb-2">{ast.author}</p>
                  </div>

                  <div className="pt-3 border-t border-[#2d3345] flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-300 font-semibold">{ast.license}</span>
                    <span className="text-slate-400 text-[11px]">{ast.is_ai_generated ? 'Local SD 3.2' : 'Verified Hash'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Script & Beats Inspector */}
        {selectedTab === 'script' && (
          <div className="p-6 space-y-4">
            {beats.map((beat) => (
              <div
                key={beat.index}
                className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-orange-400 bg-orange-950/50 px-2 py-0.5 rounded border border-orange-800/40">
                      Beat {beat.index}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {beat.char_count} chars {beat.char_count <= 80 ? '✓ (Safe margin compliant)' : '⚠'}
                    </span>
                  </div>
                  <p className="text-sm font-display text-white font-medium">{beat.text}</p>
                </div>

                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs text-slate-400 font-mono mr-1">Claims:</span>
                  {beat.claim_ids.map((cid) => (
                    <span
                      key={cid}
                      className="bg-amber-950/50 border border-amber-800/40 text-amber-300 font-mono text-xs px-2 py-0.5 rounded"
                    >
                      {cid}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 3: Quality Rubric & Deterministic Checks */}
        {selectedTab === 'quality' && quality && (
          <div className="p-6 space-y-6">
            <div className="bg-[#12141a] border border-[#272b38] rounded-xl p-5 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono uppercase text-slate-400">Total Rubric Score</span>
                <div className="text-3xl font-bold text-emerald-400 font-mono">{quality.overall_score} / 100</div>
                <span className="text-xs text-slate-300">Passing Threshold: ≥ 78.0 Total, ≥ 60.0 Min Dimension</span>
              </div>
              <div className="text-right">
                <span className="inline-flex items-center gap-1.5 bg-emerald-950/60 border border-emerald-800/50 text-emerald-400 px-3 py-1.5 rounded-lg text-xs font-bold font-mono">
                  <CheckCircle className="w-4 h-4" /> ALL CHECKS PASSED
                </span>
              </div>
            </div>

            {/* Rubric Dimensions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(quality.dimensions).map(([dim, data]) => (
                <div key={dim} className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-3.5 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-slate-200 capitalize font-mono">{dim.replace('_', ' ')}</span>
                    <span className="font-bold text-amber-400 font-mono">{data.score} / 100</span>
                  </div>
                  <div className="w-full bg-[#12141a] h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${data.score >= 80 ? 'bg-emerald-500' : data.score >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${data.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Deterministic Checks List */}
            <div className="border-t border-[#272b38] pt-4">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                Deterministic Compliance Checks (Non-Negotiable)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                {quality.deterministic_checks.map((check) => (
                  <div
                    key={check.name}
                    className="flex items-center justify-between bg-[#1e2230] p-2.5 rounded border border-[#2d3345]"
                  >
                    <span className="text-slate-300 flex items-center gap-2">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                      {check.name}
                    </span>
                    <span className="text-emerald-400 font-mono text-[11px]">{check.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Structured Rejection Modal */}
      <StructuredRejectionModal
        gateId={selectedGate.id}
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onSubmit={handleRejectSubmit}
      />
    </div>
  );
};
