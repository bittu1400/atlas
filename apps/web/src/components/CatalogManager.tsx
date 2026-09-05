import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Boxes, Compass, Layers, Plus, Radio } from 'lucide-react';
import { api } from '../api/client';
import { FieldNote } from './FieldNote';

// The Catalog: the operator-managed reference data every Run is assembled from
// — Domains, Topics, Channels and Focuses. Until 2026-09-05 none of it could be
// created or even listed outside the terminal, so the Launch form was three
// free-text boxes over IDs the browser had no way to discover (defects V-15,
// V-16; task T-64).
//
// Nothing here holds a default list. An empty section renders as empty, which
// is a fact about the database and never a reason to show a plausible row
// (**R13**). Every failure is surfaced verbatim — a duplicate ID comes back
// 409 and is shown as a refusal, because `create` overwriting a row is exactly
// what defect V-17 was.

const errorText = (err: unknown): string =>
  err instanceof Error ? err.message : String(err);

const input =
  'w-full bg-[#1e2230] border border-[#2d3345] rounded-lg px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-orange-500 disabled:opacity-50';
const label =
  'block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5';
const primaryButton =
  'text-sm bg-[#242938] hover:bg-[#2d3345] border border-[#2d3345] text-white px-4 py-2 rounded-lg disabled:opacity-50 cursor-pointer';

const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  count: number;
  note: React.ReactNode;
  onToggleCreate: () => void;
  createOpen: boolean;
  children: React.ReactNode;
}> = ({ title, icon, count, note, onToggleCreate, createOpen, children }) => (
  <section className="bg-[#161922] border border-[#272b38] rounded-xl shadow-xl overflow-hidden">
    <div className="px-6 py-4 border-b border-[#272b38] flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-orange-950/60 border border-orange-800/40 text-orange-400">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            {title}
            <span className="ml-2 text-slate-500 font-mono normal-case">{count}</span>
          </h3>
          <div className="max-w-2xl">{note}</div>
        </div>
      </div>
      <button
        type="button"
        onClick={onToggleCreate}
        className="shrink-0 flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 cursor-pointer"
      >
        <Plus className="w-3 h-3" />
        {createOpen ? 'Cancel' : 'New'}
      </button>
    </div>
    <div className="p-6 space-y-4">{children}</div>
  </section>
);

const Empty: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-xs text-slate-500 font-mono py-2">{children}</p>
);

const Failure: React.FC<{ error: unknown }> = ({ error }) =>
  error ? (
    <p
      data-testid="catalog-error"
      className="text-xs text-red-400 bg-red-950/50 border border-red-800/50 p-2.5 rounded-lg font-mono"
    >
      {errorText(error)}
    </p>
  ) : null;

export const CatalogManager: React.FC = () => {
  const queryClient = useQueryClient();
  const [openForm, setOpenForm] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const [domainDraft, setDomainDraft] = useState({ id: '', name: '', description: '' });
  const [topicDraft, setTopicDraft] = useState({ id: '', title: '', domain_id: '' });
  const [channelDraft, setChannelDraft] = useState({
    id: '',
    name: '',
    audience_timezone: 'America/New_York',
  });
  const [focusDraft, setFocusDraft] = useState({
    name: '',
    scope_mode: 'soft',
    dimension: 'domain',
    value: '',
  });

  const domains = useQuery({ queryKey: ['domains'], queryFn: api.getDomains });
  const topics = useQuery({ queryKey: ['topics'], queryFn: api.getTopics });
  const channels = useQuery({ queryKey: ['channels'], queryFn: api.getChannels });
  const focuses = useQuery({ queryKey: ['focuses'], queryFn: api.getFocuses });

  const afterCreate = (key: string) => {
    setMutationError(null);
    setOpenForm(null);
    queryClient.invalidateQueries({ queryKey: [key] });
  };

  const createDomain = useMutation({
    mutationFn: api.createDomain,
    onSuccess: () => {
      setDomainDraft({ id: '', name: '', description: '' });
      afterCreate('domains');
    },
    onError: (err) => setMutationError(errorText(err)),
  });

  const createTopic = useMutation({
    mutationFn: api.createTopic,
    onSuccess: () => {
      setTopicDraft({ id: '', title: '', domain_id: '' });
      afterCreate('topics');
    },
    onError: (err) => setMutationError(errorText(err)),
  });

  const createChannel = useMutation({
    mutationFn: api.createChannel,
    onSuccess: () => {
      setChannelDraft({ id: '', name: '', audience_timezone: 'America/New_York' });
      afterCreate('channels');
    },
    onError: (err) => setMutationError(errorText(err)),
  });

  const createFocus = useMutation({
    mutationFn: api.createFocus,
    onSuccess: () => {
      setFocusDraft({ name: '', scope_mode: 'soft', dimension: 'domain', value: '' });
      afterCreate('focuses');
    },
    onError: (err) => setMutationError(errorText(err)),
  });

  const toggle = (name: string) => {
    setMutationError(null);
    setOpenForm((current) => (current === name ? null : name));
  };

  return (
    <div className="space-y-8">
      {mutationError && (
        <div
          data-testid="catalog-mutation-error"
          className="text-xs text-red-400 bg-red-950/50 border border-red-800/50 p-3 rounded-lg font-mono"
        >
          {mutationError}
        </div>
      )}

      <Section
        title="Domains"
        icon={<Layers className="w-4 h-4" />}
        count={(domains.data ?? []).length}
        createOpen={openForm === 'domain'}
        onToggleCreate={() => toggle('domain')}
        note={
          <FieldNote>
            A named area of knowledge carrying a Research Profile — preferred APIs, source allowlist
            and source tier floor. Data, not a tag: it decides which sources a Topic in this Domain
            may draw on.
          </FieldNote>
        }
      >
        <Failure error={domains.error} />
        {openForm === 'domain' && (
          <div className="space-y-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label htmlFor="domain-id" className={label}>
                  Domain ID
                </label>
                <input
                  id="domain-id"
                  className={input}
                  placeholder="dom_history"
                  value={domainDraft.id}
                  onChange={(e) => setDomainDraft({ ...domainDraft, id: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="domain-name" className={label}>
                  Name
                </label>
                <input
                  id="domain-name"
                  className={input}
                  placeholder="History"
                  value={domainDraft.name}
                  onChange={(e) => setDomainDraft({ ...domainDraft, name: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label htmlFor="domain-description" className={label}>
                Description
              </label>
              <input
                id="domain-description"
                className={input}
                placeholder="What this Domain covers"
                value={domainDraft.description}
                onChange={(e) =>
                  setDomainDraft({ ...domainDraft, description: e.target.value })
                }
              />
            </div>
            <FieldNote>
              A new Domain starts with an empty Research Profile and a source tier floor of{' '}
              <span className="font-mono">institutional</span>. Editing a Research Profile is not
              possible here yet — and an existing ID is refused rather than overwritten, which is
              what cost `dom_history` its allowlist on 2026-09-05.
            </FieldNote>
            <button
              type="button"
              className={primaryButton}
              disabled={
                createDomain.isPending ||
                !domainDraft.id.trim() ||
                !domainDraft.name.trim() ||
                !domainDraft.description.trim()
              }
              onClick={() =>
                createDomain.mutate({
                  id: domainDraft.id.trim(),
                  name: domainDraft.name.trim(),
                  description: domainDraft.description.trim(),
                })
              }
            >
              {createDomain.isPending ? 'Creating…' : 'Create Domain'}
            </button>
          </div>
        )}

        {(domains.data ?? []).length === 0 && !domains.isLoading && (
          <Empty>No Domains exist. Create one before adding a Topic.</Empty>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {(domains.data ?? []).map((d) => {
            const profile = d.research_profile as {
              source_tier_floor?: string;
              preferred_apis?: string[];
              source_allowlist?: string[];
            };
            return (
              <div
                key={d.id}
                className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-4 space-y-2"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm text-white font-semibold">{d.name}</span>
                  <span className="text-[11px] text-amber-400 font-mono">{d.id}</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{d.description}</p>
                <dl className="text-[11px] font-mono text-slate-400 space-y-1">
                  <div className="flex justify-between gap-3">
                    <dt>source tier floor</dt>
                    <dd className="text-white">{profile.source_tier_floor ?? '—'}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt>preferred APIs</dt>
                    <dd className="text-white text-right">
                      {(profile.preferred_apis ?? []).join(', ') || '—'}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt>allowlist</dt>
                    <dd className="text-white text-right">
                      {(profile.source_allowlist ?? []).length || 0} patterns
                    </dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      </Section>

      <Section
        title="Topics"
        icon={<Boxes className="w-4 h-4" />}
        count={(topics.data ?? []).length}
        createOpen={openForm === 'topic'}
        onToggleCreate={() => toggle('topic')}
        note={
          <FieldNote>
            A candidate subject for one output, with its own lifecycle:{' '}
            <span className="font-mono">
              proposed → approved → researching → knowledge_ready → published
            </span>
            . A Run is one execution of the pipeline for one Topic.
          </FieldNote>
        }
      >
        <Failure error={topics.error} />
        {openForm === 'topic' && (
          <div className="space-y-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label htmlFor="topic-new-id" className={label}>
                  Topic ID
                </label>
                <input
                  id="topic-new-id"
                  className={input}
                  placeholder="topic_origin_of_chess"
                  value={topicDraft.id}
                  onChange={(e) => setTopicDraft({ ...topicDraft, id: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="topic-new-title" className={label}>
                  Title
                </label>
                <input
                  id="topic-new-title"
                  className={input}
                  placeholder="The Origin of Chess"
                  value={topicDraft.title}
                  onChange={(e) => setTopicDraft({ ...topicDraft, title: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label htmlFor="topic-new-domain" className={label}>
                Domain
              </label>
              <select
                id="topic-new-domain"
                className={input}
                value={topicDraft.domain_id}
                onChange={(e) => setTopicDraft({ ...topicDraft, domain_id: e.target.value })}
              >
                <option value="">
                  {(domains.data ?? []).length === 0
                    ? 'No Domains exist yet — create one above'
                    : 'Select a Domain'}
                </option>
                {(domains.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} · {d.id}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className={primaryButton}
              disabled={
                createTopic.isPending ||
                !topicDraft.id.trim() ||
                !topicDraft.title.trim() ||
                !topicDraft.domain_id
              }
              onClick={() =>
                createTopic.mutate({
                  id: topicDraft.id.trim(),
                  title: topicDraft.title.trim(),
                  domain_id: topicDraft.domain_id,
                })
              }
            >
              {createTopic.isPending ? 'Creating…' : 'Create Topic'}
            </button>
          </div>
        )}

        {(topics.data ?? []).length === 0 && !topics.isLoading && (
          <Empty>No Topics exist. A Run cannot be created until one does.</Empty>
        )}
        <ul className="divide-y divide-[#1f2430]">
          {(topics.data ?? []).map((t) => (
            <li key={t.id} className="py-2.5 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm text-white truncate">{t.title}</p>
                <p className="text-[11px] font-mono text-slate-500 truncate">
                  {t.id} · {t.domain_id}
                  {t.entity_id ? ` · ${t.entity_id}` : ''}
                </p>
              </div>
              <span className="shrink-0 text-[11px] font-mono uppercase px-2 py-0.5 rounded border bg-slate-800 text-slate-300 border-slate-700">
                {t.status}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        title="Channels"
        icon={<Radio className="w-4 h-4" />}
        count={(channels.data ?? []).length}
        createOpen={openForm === 'channel'}
        onToggleCreate={() => toggle('channel')}
        note={
          <FieldNote>
            A publishing identity carrying a Style Profile. Its audience timezone is the only clock
            that computes publish slots.
          </FieldNote>
        }
      >
        <Failure error={channels.error} />
        {openForm === 'channel' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
            <div>
              <label htmlFor="channel-new-id" className={label}>
                Channel ID
              </label>
              <input
                id="channel-new-id"
                className={input}
                placeholder="origins"
                value={channelDraft.id}
                onChange={(e) => setChannelDraft({ ...channelDraft, id: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="channel-new-name" className={label}>
                Name
              </label>
              <input
                id="channel-new-name"
                className={input}
                placeholder="ORIGINS"
                value={channelDraft.name}
                onChange={(e) => setChannelDraft({ ...channelDraft, name: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="channel-new-tz" className={label}>
                Audience timezone
              </label>
              <input
                id="channel-new-tz"
                className={input}
                value={channelDraft.audience_timezone}
                onChange={(e) =>
                  setChannelDraft({ ...channelDraft, audience_timezone: e.target.value })
                }
              />
            </div>
            <div className="md:col-span-3">
              <button
                type="button"
                className={primaryButton}
                disabled={
                  createChannel.isPending ||
                  !channelDraft.id.trim() ||
                  !channelDraft.name.trim()
                }
                onClick={() =>
                  createChannel.mutate({
                    id: channelDraft.id.trim(),
                    name: channelDraft.name.trim(),
                    audience_timezone: channelDraft.audience_timezone.trim(),
                  })
                }
              >
                {createChannel.isPending ? 'Creating…' : 'Create Channel'}
              </button>
            </div>
          </div>
        )}

        {(channels.data ?? []).length === 0 && !channels.isLoading && (
          <Empty>No Channels exist.</Empty>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {(channels.data ?? []).map((c) => {
            const style = c.style_profile as {
              display_font?: string;
              motion_style?: string;
              sound_profile?: string;
              target_duration_seconds?: number;
            };
            const hasStyle = Object.keys(c.style_profile ?? {}).length > 0;
            return (
              <div
                key={c.id}
                className="bg-[#1e2230] border border-[#2d3345] rounded-lg p-4 space-y-2"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm text-white font-semibold">{c.name}</span>
                  <span className="text-[11px] text-amber-400 font-mono">{c.id}</span>
                </div>
                <p className="text-[11px] font-mono text-slate-400">{c.audience_timezone}</p>
                {hasStyle ? (
                  <dl className="text-[11px] font-mono text-slate-400 space-y-1">
                    <div className="flex justify-between gap-3">
                      <dt>display font</dt>
                      <dd className="text-white">{style.display_font ?? '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>motion</dt>
                      <dd className="text-white">{style.motion_style ?? '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>sound</dt>
                      <dd className="text-white">{style.sound_profile ?? '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>target duration</dt>
                      <dd className="text-white">
                        {style.target_duration_seconds
                          ? `${style.target_duration_seconds}s`
                          : '—'}
                      </dd>
                    </div>
                  </dl>
                ) : (
                  <p className="text-[11px] font-mono text-amber-400">
                    No Style Profile on this Channel.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      <Section
        title="Focuses"
        icon={<Compass className="w-4 h-4" />}
        count={(focuses.data ?? []).length}
        createOpen={openForm === 'focus'}
        onToggleCreate={() => toggle('focus')}
        note={
          <FieldNote>
            A named set of Facets plus a Scope Mode. Captured by value into every Run that uses it
            and never mutated afterwards, so editing one later cannot change a Run already in
            flight. The Active Focus supplies the default for newly created Runs.
          </FieldNote>
        }
      >
        <Failure error={focuses.error} />
        {openForm === 'focus' && (
          <div className="space-y-3 border border-[#2d3345] rounded-lg p-4 bg-[#12151d]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label htmlFor="focus-new-name" className={label}>
                  Name
                </label>
                <input
                  id="focus-new-name"
                  className={input}
                  placeholder="History — primary sources"
                  value={focusDraft.name}
                  onChange={(e) => setFocusDraft({ ...focusDraft, name: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="focus-new-scope" className={label}>
                  Scope Mode
                </label>
                <select
                  id="focus-new-scope"
                  className={input}
                  value={focusDraft.scope_mode}
                  onChange={(e) => setFocusDraft({ ...focusDraft, scope_mode: e.target.value })}
                >
                  <option value="hard">hard — never leave the Focus</option>
                  <option value="soft">soft — prefer it, allow adjacent nodes</option>
                  <option value="exploratory">exploratory — the Focus is a seed</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label htmlFor="focus-new-dimension" className={label}>
                  Facet dimension
                </label>
                <input
                  id="focus-new-dimension"
                  className={input}
                  placeholder="domain"
                  value={focusDraft.dimension}
                  onChange={(e) => setFocusDraft({ ...focusDraft, dimension: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="focus-new-value" className={label}>
                  Facet value
                </label>
                <input
                  id="focus-new-value"
                  className={input}
                  placeholder="dom_history"
                  value={focusDraft.value}
                  onChange={(e) => setFocusDraft({ ...focusDraft, value: e.target.value })}
                />
              </div>
            </div>
            <FieldNote>
              One Facet is enough to start; the model holds a list. Creating a Focus does not make
              it the Active Focus — that pointer is a separate act, and it is not settable from here
              yet.
            </FieldNote>
            <button
              type="button"
              className={primaryButton}
              disabled={
                createFocus.isPending ||
                !focusDraft.name.trim() ||
                !focusDraft.dimension.trim() ||
                !focusDraft.value.trim()
              }
              onClick={() =>
                createFocus.mutate({
                  name: focusDraft.name.trim(),
                  scope_mode: focusDraft.scope_mode,
                  facets: [
                    {
                      dimension: focusDraft.dimension.trim(),
                      value: focusDraft.value.trim(),
                    },
                  ],
                  actor_id: 'operator-web',
                })
              }
            >
              {createFocus.isPending ? 'Creating…' : 'Create Focus'}
            </button>
          </div>
        )}

        {(focuses.data ?? []).length === 0 && !focuses.isLoading && (
          <Empty>
            No Focuses exist. A Run created now captures a default Focus built in memory rather than
            a stored one.
          </Empty>
        )}
        <ul className="divide-y divide-[#1f2430]">
          {(focuses.data ?? []).map((f) => (
            <li key={f.id} className="py-2.5 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm text-white truncate">
                  {f.name}
                  {f.is_active && (
                    <span className="ml-2 text-[11px] font-mono uppercase text-emerald-400">
                      active
                    </span>
                  )}
                </p>
                <p className="text-[11px] font-mono text-slate-500 truncate">
                  {f.id} · {f.scope_mode} ·{' '}
                  {f.facets.map((facet) => `${facet.dimension}=${facet.value}`).join(', ') ||
                    'no facets'}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
};
