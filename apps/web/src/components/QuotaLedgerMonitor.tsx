import React from 'react';
import { Cpu, Zap, HardDrive, Lock } from 'lucide-react';

export const QuotaLedgerMonitor: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Google Gemini Card */}
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-5 shadow-xl space-y-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <h4 className="text-sm font-bold text-white">Google Gemini (Tier 2)</h4>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded">
            Free Tier Active
          </span>
        </div>
        <div>
          <div className="flex justify-between text-xs font-mono mb-1">
            <span className="text-slate-400">Daily Requests</span>
            <span className="text-white font-bold">18 / 1,500 RPD (1.2%)</span>
          </div>
          <div className="w-full bg-[#0a0b0e] h-2 rounded-full overflow-hidden">
            <div className="bg-amber-500 h-full" style={{ width: '1.2%' }} />
          </div>
        </div>
        <p className="text-[11px] text-slate-400">
          Used for: Claim extraction fidelity, Beat writing, and Rubric judging.
        </p>
      </div>

      {/* Local GPU Card */}
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-5 shadow-xl space-y-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-orange-400" />
            <h4 className="text-sm font-bold text-white">Ollama & SD 3.2 (Tier 1)</h4>
          </div>
          <span className="text-xs font-mono text-blue-400 bg-blue-950/60 border border-blue-800/40 px-2 py-0.5 rounded">
            RTX 5070 8GB
          </span>
        </div>
        <div>
          <div className="flex justify-between text-xs font-mono mb-1">
            <span className="text-slate-400">GPU Semaphore Lease</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <Lock className="w-3 h-3" /> Idle / Released
            </span>
          </div>
          <div className="w-full bg-[#0a0b0e] h-2 rounded-full overflow-hidden">
            <div className="bg-emerald-500 h-full" style={{ width: '10%' }} />
          </div>
        </div>
        <p className="text-[11px] text-slate-400">
          Used for: Local Qwen 3 8B summarization and Stable Diffusion imagery.
        </p>
      </div>

      {/* Snapshot Storage Card */}
      <div className="bg-[#161922] border border-[#272b38] rounded-xl p-5 shadow-xl space-y-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-teal-400" />
            <h4 className="text-sm font-bold text-white">Content-Addressed Blobs</h4>
          </div>
          <span className="text-xs font-mono text-slate-300 bg-[#1e2230] border border-[#2d3345] px-2 py-0.5 rounded">
            SHA-256 Storage
          </span>
        </div>
        <div>
          <div className="flex justify-between text-xs font-mono mb-1">
            <span className="text-slate-400">Storage Used</span>
            <span className="text-white font-bold">42.8 MB / 550 GB Yr 1</span>
          </div>
          <div className="w-full bg-[#0a0b0e] h-2 rounded-full overflow-hidden">
            <div className="bg-teal-500 h-full" style={{ width: '0.1%' }} />
          </div>
        </div>
        <p className="text-[11px] text-slate-400">
          Append-only snapshot bytes stored with immutability triggers.
        </p>
      </div>
    </div>
  );
};
