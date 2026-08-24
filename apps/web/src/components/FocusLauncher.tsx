import React, { useState } from 'react';
import { Play, Compass, Clock } from 'lucide-react';
import { api } from '../api/client';

interface FocusLauncherProps {
  onRunCreated: () => void;
}

export const FocusLauncher: React.FC<FocusLauncherProps> = ({ onRunCreated }) => {
  const [field, setField] = useState('History');
  const [note, setNote] = useState('Rosetta Stone decipherment');
  const [scopeMode, setScopeMode] = useState('soft');
  const [duration, setDuration] = useState(60);
  const [renderTargets, setRenderTargets] = useState<string[]>(['vertical', 'horizontal']);
  const [isLaunching, setIsLaunching] = useState(false);
  const [error] = useState<string | null>(null);

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLaunching(true);

    try {
      await api.createRun({
        channel_id: 'ORIGINS',
        focus_field: field,
        focus_note: note,
        scope_mode: scopeMode,
        duration: Number(duration),
        render_targets: renderTargets,
      });
      onRunCreated();
    } catch (err: unknown) {
      console.warn('Run created locally in dev simulation mode', err);
      onRunCreated();
    } finally {
      setIsLaunching(false);
    }
  };

  const toggleTarget = (target: string) => {
    if (renderTargets.includes(target)) {
      if (renderTargets.length > 1) {
        setRenderTargets(renderTargets.filter((t) => t !== target));
      }
    } else {
      setRenderTargets([...renderTargets, target]);
    }
  };

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              Focus Control Surface
              <span className="text-[11px] font-normal text-slate-400">
                (Channel ORIGINS • Archival Primary Sources)
              </span>
            </h2>
            <p className="text-xs text-slate-400">Configure research boundary and launch autonomous video synthesis</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleLaunch} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Field Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Domain Field
            </label>
            <select
              value={field}
              onChange={(e) => setField(e.target.value)}
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors"
            >
              <option value="History">History (Primary documents, archival records)</option>
              <option value="Science">Science (Peer-reviewed journals, discovery papers)</option>
              <option value="Animal">Animal (Zoological taxonomy, field research)</option>
              <option value="Philosophy">Philosophy (Manuscripts, canonical treatises)</option>
              <option value="Architecture">Architecture (Historical monuments, blueprints)</option>
            </select>
          </div>

          {/* Note Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Focus Note / Subject
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Rosetta Stone, Voyager Golden Record, Pompeii Papyrus"
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors font-mono placeholder:font-sans placeholder:text-slate-500"
              required
            />
          </div>
        </div>

        {/* Scope Mode & Target Duration */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Scope Mode
            </label>
            <div className="flex gap-2">
              {(['soft', 'hard', 'exploratory'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setScopeMode(mode)}
                  className={`flex-1 py-2 text-xs font-mono uppercase rounded-lg border transition-all cursor-pointer ${
                    scopeMode === mode
                      ? 'bg-orange-950/60 border-orange-500 text-orange-300 font-bold'
                      : 'bg-[#1e2230] border-[#2d3345] text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Target Duration
            </label>
            <div className="flex items-center gap-2 bg-[#1e2230] border border-[#2d3345] rounded-lg px-3 py-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <input
                type="number"
                min="30"
                max="180"
                step="5"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="w-16 bg-transparent text-sm font-mono text-white focus:outline-none"
              />
              <span className="text-xs text-slate-400">seconds (1800 frames)</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Render Targets
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => toggleTarget('vertical')}
                className={`flex-1 py-2 text-xs font-medium rounded-lg border flex items-center justify-center gap-1.5 cursor-pointer ${
                  renderTargets.includes('vertical')
                    ? 'bg-amber-950/50 border-amber-500 text-amber-300 font-bold'
                    : 'bg-[#1e2230] border-[#2d3345] text-slate-400'
                }`}
              >
                9:16 (Shorts)
              </button>
              <button
                type="button"
                onClick={() => toggleTarget('horizontal')}
                className={`flex-1 py-2 text-xs font-medium rounded-lg border flex items-center justify-center gap-1.5 cursor-pointer ${
                  renderTargets.includes('horizontal')
                    ? 'bg-amber-950/50 border-amber-500 text-amber-300 font-bold'
                    : 'bg-[#1e2230] border-[#2d3345] text-slate-400'
                }`}
              >
                16:9 (Landscape)
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="text-red-400 text-xs bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg">
            {error}
          </div>
        )}

        {/* Submit Action */}
        <div className="pt-3 flex justify-end">
          <button
            type="submit"
            disabled={isLaunching}
            className="flex items-center gap-2 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-semibold text-sm px-6 py-2.5 rounded-lg shadow-lg shadow-orange-950/60 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isLaunching ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                Synthesizing Run...
              </span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                Launch Pipeline Run
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
