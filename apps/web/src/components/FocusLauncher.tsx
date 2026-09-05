import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Compass, Play, Plus } from 'lucide-react';
import { api } from '../api/client';
import { FieldNote } from './FieldNote';

// The form collects exactly what `POST /runs` accepts. It used to collect a
// domain field, a free-text focus note, a scope mode, a duration and a pair of
// render targets, none of which the endpoint has a parameter for — and then
// posted a body with no `topic_id`, which the API rejects with a 422. The
// failure was swallowed and reported to the operator as a created Run
// (defect V-03).
//
// Its three inputs were then free text over IDs only the terminal could reveal,
// so an operator's only feedback on a typo was a 404 (T-64). They are pickers
// now, fed by `/topics`, `/channels` and `/focuses`, with inline creation for
// the first two. Nothing here holds a default list: an empty dropdown means an
// empty table, which is a fact about the database and not a reason to invent
// options (**R13**).

interface FocusLauncherProps {
  onRunCreated: () => void;
}

const errorText = (err: unknown): string =>
  err instanceof Error ? err.message : String(err);

export const FocusLauncher: React.FC<FocusLauncherProps> = ({ onRunCreated }) => {
  const queryClient = useQueryClient();

  const [topicId, setTopicId] = useState('');
  const [channelId, setChannelId] = useState('');
  const [focusId, setFocusId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

  const [showNewTopic, setShowNewTopic] = useState(false);
  const [newTopic, setNewTopic] = useState({ id: '', title: '', domain_id: '' });
  const [showNewChannel, setShowNewChannel] = useState(false);
  const [newChannel, setNewChannel] = useState({
    id: '',
    name: '',
    audience_timezone: 'America/New_York',
  });

  const topics = useQuery({ queryKey: ['topics'], queryFn: api.getTopics });
  const channels = useQuery({ queryKey: ['channels'], queryFn: api.getChannels });
  const domains = useQuery({ queryKey: ['domains'], queryFn: api.getDomains });
  const focuses = useQuery({ queryKey: ['focuses'], queryFn: api.getFocuses });

  const activeFocus = (focuses.data ?? []).find((f) => f.is_active);

  const createTopic = useMutation({
    mutationFn: api.createTopic,
    onSuccess: (topic) => {
      setError(null);
      setShowNewTopic(false);
      setNewTopic({ id: '', title: '', domain_id: '' });
      setTopicId(topic.id);
      queryClient.invalidateQueries({ queryKey: ['topics'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const createChannel = useMutation({
    mutationFn: api.createChannel,
    onSuccess: (channel) => {
      setError(null);
      setShowNewChannel(false);
      setNewChannel({ id: '', name: '', audience_timezone: 'America/New_York' });
      setChannelId(channel.id);
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
    onError: (err) => setError(errorText(err)),
  });

  const createRun = useMutation({
    mutationFn: api.createRun,
    onSuccess: (run) => {
      setError(null);
      setCreatedRunId(run.id);
      onRunCreated();
    },
    onError: (err) => {
      setCreatedRunId(null);
      setError(errorText(err));
    },
  });

  const handleLaunch = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreatedRunId(null);
    createRun.mutate({
      topic_id: topicId,
      channel_id: channelId,
      actor_id: 'operator-web',
      ...(focusId ? { focus_id: focusId } : {}),
    });
  };

  const selectClass =
    'w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-orange-500 disabled:opacity-50';
  const inputClass = selectClass;
  const labelClass =
    'block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5';

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl">
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
          <Compass className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white font-display">Launch a Run</h2>
          <p className="text-xs text-slate-400">
            One execution of the pipeline for one Topic under one captured Focus.
          </p>
        </div>
      </div>

      <form onSubmit={handleLaunch} className="space-y-5">
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="topic-id" className={labelClass}>
              Topic <span className="text-red-400">*</span>
            </label>
            <button
              type="button"
              onClick={() => setShowNewTopic((open) => !open)}
              className="flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 cursor-pointer"
            >
              <Plus className="w-3 h-3" />
              {showNewTopic ? 'Cancel' : 'New topic'}
            </button>
          </div>
          <select
            id="topic-id"
            value={topicId}
            onChange={(e) => setTopicId(e.target.value)}
            required
            className={selectClass}
          >
            <option value="">
              {topics.isLoading
                ? 'Loading…'
                : (topics.data ?? []).length === 0
                  ? 'No Topics exist yet — create one'
                  : 'Select a Topic'}
            </option>
            {(topics.data ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.title} · {t.id} · {t.status}
              </option>
            ))}
          </select>
          <FieldNote>
            A candidate subject for one output, with its own lifecycle:{' '}
            <span className="font-mono">proposed → approved → researching → knowledge_ready</span>.
          </FieldNote>
          {topics.error && (
            <p className="mt-1.5 text-xs text-red-400 font-mono">{errorText(topics.error)}</p>
          )}

          {showNewTopic && (
            <div className="mt-3 space-y-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="new-topic-id" className={labelClass}>
                    Topic ID
                  </label>
                  <input
                    id="new-topic-id"
                    value={newTopic.id}
                    onChange={(e) => setNewTopic({ ...newTopic, id: e.target.value })}
                    placeholder="topic_origin_of_chess"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label htmlFor="new-topic-title" className={labelClass}>
                    Title
                  </label>
                  <input
                    id="new-topic-title"
                    value={newTopic.title}
                    onChange={(e) => setNewTopic({ ...newTopic, title: e.target.value })}
                    placeholder="The Origin of Chess"
                    className={inputClass}
                  />
                </div>
              </div>
              <div>
                <label htmlFor="new-topic-domain" className={labelClass}>
                  Domain
                </label>
                <select
                  id="new-topic-domain"
                  value={newTopic.domain_id}
                  onChange={(e) => setNewTopic({ ...newTopic, domain_id: e.target.value })}
                  className={selectClass}
                >
                  <option value="">Select a Domain</option>
                  {(domains.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} · {d.id}
                    </option>
                  ))}
                </select>
                <FieldNote>
                  A named area of knowledge carrying a Research Profile — preferred APIs, source
                  allowlist and source tier floor. Data, not a tag: it decides which sources this
                  Topic may draw on.
                </FieldNote>
              </div>
              <button
                type="button"
                disabled={
                  createTopic.isPending ||
                  !newTopic.id.trim() ||
                  !newTopic.title.trim() ||
                  !newTopic.domain_id
                }
                onClick={() =>
                  createTopic.mutate({
                    id: newTopic.id.trim(),
                    title: newTopic.title.trim(),
                    domain_id: newTopic.domain_id,
                  })
                }
                className="text-sm bg-[#242938] hover:bg-[#2d3345] border border-[#2d3345] text-white px-4 py-2 rounded-lg disabled:opacity-50 cursor-pointer"
              >
                {createTopic.isPending ? 'Creating…' : 'Create Topic'}
              </button>
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="channel-id" className={labelClass}>
              Channel <span className="text-red-400">*</span>
            </label>
            <button
              type="button"
              onClick={() => setShowNewChannel((open) => !open)}
              className="flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 cursor-pointer"
            >
              <Plus className="w-3 h-3" />
              {showNewChannel ? 'Cancel' : 'New channel'}
            </button>
          </div>
          <select
            id="channel-id"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            required
            className={selectClass}
          >
            <option value="">
              {channels.isLoading ? 'Loading…' : 'Select a Channel'}
            </option>
            {(channels.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} · {c.id} · {c.audience_timezone}
              </option>
            ))}
          </select>
          <FieldNote>
            A publishing identity carrying a Style Profile and an audience clock. The timezone is the
            only clock that computes publish slots.
          </FieldNote>

          {showNewChannel && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
              <div>
                <label htmlFor="new-channel-id" className={labelClass}>
                  Channel ID
                </label>
                <input
                  id="new-channel-id"
                  value={newChannel.id}
                  onChange={(e) => setNewChannel({ ...newChannel, id: e.target.value })}
                  placeholder="origins"
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="new-channel-name" className={labelClass}>
                  Name
                </label>
                <input
                  id="new-channel-name"
                  value={newChannel.name}
                  onChange={(e) => setNewChannel({ ...newChannel, name: e.target.value })}
                  placeholder="ORIGINS"
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="new-channel-tz" className={labelClass}>
                  Audience timezone
                </label>
                <input
                  id="new-channel-tz"
                  value={newChannel.audience_timezone}
                  onChange={(e) =>
                    setNewChannel({ ...newChannel, audience_timezone: e.target.value })
                  }
                  className={inputClass}
                />
              </div>
              <div className="md:col-span-3">
                <button
                  type="button"
                  disabled={
                    createChannel.isPending || !newChannel.id.trim() || !newChannel.name.trim()
                  }
                  onClick={() =>
                    createChannel.mutate({
                      id: newChannel.id.trim(),
                      name: newChannel.name.trim(),
                      audience_timezone: newChannel.audience_timezone.trim(),
                    })
                  }
                  className="text-sm bg-[#242938] hover:bg-[#2d3345] border border-[#2d3345] text-white px-4 py-2 rounded-lg disabled:opacity-50 cursor-pointer"
                >
                  {createChannel.isPending ? 'Creating…' : 'Create Channel'}
                </button>
              </div>
            </div>
          )}
        </div>

        <div>
          <label htmlFor="focus-id" className={labelClass}>
            Focus
          </label>
          <select
            id="focus-id"
            value={focusId}
            onChange={(e) => setFocusId(e.target.value)}
            className={selectClass}
          >
            <option value="">
              {activeFocus
                ? `Use the Active Focus — ${activeFocus.name}`
                : 'No Active Focus — a default Focus is captured'}
            </option>
            {(focuses.data ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} · {f.scope_mode}
                {f.is_active ? ' · active' : ''}
              </option>
            ))}
          </select>
          <FieldNote>
            A named set of Facets plus a Scope Mode (<span className="font-mono">hard</span>,{' '}
            <span className="font-mono">soft</span>, <span className="font-mono">exploratory</span>).
            It is captured by value into the Run and never mutated afterwards, so changing a Focus
            later cannot alter a Run already in flight.
          </FieldNote>
        </div>

        {error && (
          <div
            data-testid="launcher-error"
            className="text-red-400 text-xs bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg font-mono"
          >
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
            disabled={createRun.isPending || !topicId || !channelId}
            className="flex items-center gap-2 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-semibold text-sm px-6 py-2.5 rounded-lg shadow-lg shadow-orange-950/60 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-white" />
            {createRun.isPending ? 'Creating…' : 'Create Run'}
          </button>
        </div>
      </form>
    </div>
  );
};
