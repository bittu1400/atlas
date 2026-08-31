import React, { useState } from 'react';
import { Compass, Play } from 'lucide-react';
import { api } from '../api/client';

// The form collects exactly what `POST /runs` accepts. It used to collect a
// domain field, a free-text focus note, a scope mode, a duration and a pair of
// render targets, none of which the endpoint has a parameter for — and then
// posted a body with no `topic_id`, which the API rejects with a 422. The
// failure was swallowed and reported to the operator as a created Run
// (defect V-03). A Run's Focus is captured server-side from the active Focus
// (Invariant 6), so it is chosen here by ID or left to the default.

interface FocusLauncherProps {
  onRunCreated: () => void;
}

export const FocusLauncher: React.FC<FocusLauncherProps> = ({ onRunCreated }) => {
  const [topicId, setTopicId] = useState('');
  const [channelId, setChannelId] = useState('origins');
  const [focusId, setFocusId] = useState('');
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLaunching(true);
    setError(null);
    setCreatedRunId(null);

    try {
      const run = await api.createRun({
        topic_id: topicId.trim(),
        channel_id: channelId.trim(),
        actor_id: 'operator-web',
        ...(focusId.trim() ? { focus_id: focusId.trim() } : {}),
      });
      setCreatedRunId(run.id);
      onRunCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl">
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
          <Compass className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white font-display">Launch a Run</h2>
          <p className="text-xs text-slate-400">
            The Run captures the active Focus by value when it is created.
          </p>
        </div>
      </div>

      <form onSubmit={handleLaunch} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label
              htmlFor="topic-id"
              className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Topic ID <span className="text-red-400">*</span>
            </label>
            <input
              id="topic-id"
              type="text"
              value={topicId}
              onChange={(e) => setTopicId(e.target.value)}
              placeholder="topic_origin_of_chess"
              required
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label
              htmlFor="channel-id"
              className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Channel
            </label>
            <input
              id="channel-id"
              type="text"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-orange-500"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="focus-id"
            className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5"
          >
            Focus ID (optional — defaults to the active Focus)
          </label>
          <input
            id="focus-id"
            type="text"
            value={focusId}
            onChange={(e) => setFocusId(e.target.value)}
            placeholder="foc_…"
            className="w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-orange-500"
          />
        </div>

        {error && (
          <div className="text-red-400 text-xs bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg font-mono">
            {error}
          </div>
        )}
        {createdRunId && (
          <div className="text-emerald-400 text-xs bg-emerald-950/50 border border-emerald-800/50 p-2.5 rounded-lg font-mono">
            Run created: {createdRunId}
          </div>
        )}

        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={isLaunching || !topicId.trim()}
            className="flex items-center gap-2 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-semibold text-sm px-6 py-2.5 rounded-lg shadow-lg shadow-orange-950/60 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-white" />
            {isLaunching ? 'Creating…' : 'Create Run'}
          </button>
        </div>
      </form>
    </div>
  );
};
