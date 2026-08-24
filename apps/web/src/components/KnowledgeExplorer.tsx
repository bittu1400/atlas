import React from 'react';
import { Database, Link2, FileCheck } from 'lucide-react';

export const KnowledgeExplorer: React.FC = () => {
  const claims = [
    {
      id: 'CLM-001',
      assertionType: 'fact',
      text: 'Pierre-François Bouchard discovered the Rosetta Stone during excavations at Fort Julien near Rashid in July 1799.',
      evidenceCount: 3,
      source: 'British Museum Archival Monograph (1904) / Discovery Log',
      snapshotHash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    },
    {
      id: 'CLM-002',
      assertionType: 'fact',
      text: 'The stone contains three versions of a decree issued in Memphis in 196 BC on behalf of King Ptolemy V Epiphanes.',
      evidenceCount: 4,
      source: 'Corpus Inscriptionum Graecarum / BnF Gallica',
      snapshotHash: 'sha256:4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    },
    {
      id: 'CLM-005',
      assertionType: 'fact',
      text: 'Thomas Young identified that cartouches enclosed foreign royal names and isolated phonetic glyphs for Ptolemaios.',
      evidenceCount: 2,
      source: 'Philosophical Transactions of the Royal Society (1814)',
      snapshotHash: 'sha256:ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
    },
    {
      id: 'CLM-007',
      assertionType: 'fact',
      text: 'Jean-François Champollion matched the Coptic word for sun (Ra) to the cartouche of Ramesses in 1822.',
      evidenceCount: 3,
      source: 'Lettre à M. Dacier relative à l alphabet des hiéroglyphes phonétiques (1822)',
      snapshotHash: 'sha256:88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589',
    },
  ];

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex items-center justify-between border-b border-[#272b38] pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-teal-950/60 border border-teal-800/40 text-teal-400">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2 font-display">
              Canonical Knowledge Object : KO-8323-001 (v1.0)
            </h2>
            <p className="text-xs text-slate-400">
              Immutable append-only knowledge graph with complete primary source snapshot provenance
            </p>
          </div>
        </div>

        <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2.5 py-1 rounded">
          Invariant 1 & 4 Enforced
        </span>
      </div>

      <div className="space-y-4">
        {claims.map((claim) => (
          <div
            key={claim.id}
            className="bg-[#1e2230] border border-[#2d3345] rounded-xl p-5 hover:border-teal-500/50 transition-all space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="bg-amber-950/60 border border-amber-800/40 text-amber-300 font-mono text-xs font-bold px-2 py-0.5 rounded">
                  {claim.id}
                </span>
                <span className="bg-blue-950/50 border border-blue-800/40 text-blue-300 font-mono text-[11px] px-2 py-0.5 rounded uppercase">
                  {claim.assertionType}
                </span>
              </div>
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                {claim.evidenceCount} Verified Evidence Locators
              </span>
            </div>

            <p className="text-sm text-slate-100 font-medium font-sans leading-relaxed">{claim.text}</p>

            <div className="pt-3 border-t border-[#2d3345] flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 font-mono gap-2">
              <span className="truncate flex items-center gap-1">
                <Link2 className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                {claim.source}
              </span>
              <span className="text-[10px] text-slate-500 truncate max-w-xs">{claim.snapshotHash}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
