import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Database, FileCheck, Link2 } from 'lucide-react';
import { api } from '../api/client';
import { ClaimItem, ClaimStatus } from '../api/types';

// Every claim, quote, source and snapshot hash on this panel is read from
// `/runs/{id}/knowledge`. The previous version hardcoded four Rosetta Stone
// claims with invented citations and invented SHA-256 hashes under a badge
// reading "Invariant 1 & 4 Enforced" (defect V-03, rule R4).

interface KnowledgeExplorerProps {
  runId?: string;
}

const STATUS_STYLES: Record<ClaimStatus, string> = {
  verified: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40',
  unverified: 'bg-slate-800 text-slate-300 border-slate-700',
  unsupported: 'bg-amber-950/60 text-amber-400 border-amber-800/40',
  refuted: 'bg-red-950/60 text-red-400 border-red-800/40',
  contested: 'bg-purple-950/60 text-purple-300 border-purple-800/40',
};

const ClaimCard: React.FC<{ claim: ClaimItem }> = ({ claim }) => (
  <div className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-4 space-y-3">
    <div className="flex items-start justify-between gap-4">
      <p className="text-sm text-white font-display leading-relaxed">{claim.text}</p>
      <span
        className={`shrink-0 text-[11px] font-mono uppercase px-2 py-0.5 rounded border ${STATUS_STYLES[claim.status]}`}
      >
        {claim.status}
      </span>
    </div>

    <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
      <span className="text-amber-400">{claim.claim_id}</span>
      <span>v{claim.version}</span>
      <span>{claim.assertion_type}</span>
      <span>confidence {claim.confidence.toFixed(2)}</span>
      <span className="inline-flex items-center gap-1">
        <Link2 className="w-3 h-3" />
        {claim.evidence.length} evidence
      </span>
    </div>

    {claim.evidence.length === 0 ? (
      <p className="text-xs text-amber-400 font-mono">
        No evidence link. This claim cannot reach an output (Invariant 1).
      </p>
    ) : (
      <ul className="space-y-2 border-t border-[#2d3345] pt-3">
        {claim.evidence.map((ev) => (
          <li key={ev.evidence_id} className="space-y-1">
            <blockquote className="text-xs text-slate-200 border-l-2 border-orange-700/60 pl-3 italic">
              “{ev.quote}”
            </blockquote>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400 font-mono pl-3">
              <a
                href={ev.source_url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-teal-400 hover:text-teal-300 underline decoration-dotted"
              >
                {ev.source_title}
              </a>
              <span>tier {ev.source_tier}</span>
              <span>{ev.stance}</span>
              <span className="inline-flex items-center gap-1">
                <FileCheck className="w-3 h-3" />
                sha256:{ev.snapshot_sha256.slice(0, 16)}…
              </span>
              <span>{new Date(ev.retrieved_at).toISOString()}</span>
            </div>
          </li>
        ))}
      </ul>
    )}
  </div>
);

export const KnowledgeExplorer: React.FC<KnowledgeExplorerProps> = ({ runId }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['knowledge', runId],
    queryFn: () => api.getRunKnowledge(runId as string),
    enabled: Boolean(runId),
  });

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex items-center gap-3 border-b border-[#272b38] pb-4">
        <div className="p-2.5 rounded-lg bg-teal-950/60 border border-teal-800/40 text-teal-400">
          <Database className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white font-display">
            {data?.ko_id
              ? `Knowledge Object ${data.ko_id} (v${data.ko_version})`
              : 'Knowledge Object'}
          </h2>
          <p className="text-xs text-slate-400">
            Claim → Evidence → Source → Snapshot, as stored. Nothing here is computed in the browser.
          </p>
        </div>
      </div>

      {!runId && (
        <p className="text-xs text-slate-400">
          Select a Run on the Dashboard tab to inspect its Knowledge Object.
        </p>
      )}
      {runId && isLoading && <p className="text-xs text-slate-400 font-mono">Loading…</p>}
      {runId && error && (
        <p className="text-xs text-red-400 font-mono">{(error as Error).message}</p>
      )}
      {data && data.claims.length === 0 && (
        <p className="text-xs text-slate-400">
          This Run has no Knowledge Object yet. Extraction has not produced one.
        </p>
      )}

      <div className="space-y-3">
        {data?.claims.map((claim) => (
          <ClaimCard key={claim.claim_id} claim={claim} />
        ))}
      </div>
    </div>
  );
};
