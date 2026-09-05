/// <reference types="vite/client" />
import {
  ApprovalItem,
  ChannelItem,
  ApproveGatePayload,
  GateItem,
  QuotaStatus,
  RejectGatePayload,
  DomainItem,
  FocusItem,
  RunItem,
  RunKnowledge,
  StepItem,
  TelemetryEvent,
  TopicItem,
} from './types';

// There are no mock fallbacks here, in any environment.
//
// This module used to answer `getRuns`, `getGates` and `getQuota` with invented
// Rosetta Stone runs, invented archival assets and an invented passing quality
// report whenever the backend was unreachable — and `getQuota` returned invented
// numbers even when it was reachable. An operator could not tell a real run from
// a fixture, which is rule R4 broken at the last surface before a human
// (defect V-03). A failed request now fails.

const API_BASE = '/api';
const API_KEY = import.meta.env.VITE_API_KEY || 'atlas-dev-key';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  headers.set('X-API-Key', API_KEY);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<{ status: string; version?: string }>('/health'),

  getRuns: () => request<RunItem[]>('/runs'),

  getRun: (runId: string) => request<RunItem>(`/runs/${runId}`),

  getRunSteps: (runId: string) => request<StepItem[]>(`/runs/${runId}/steps`),

  getRunKnowledge: (runId: string) =>
    request<RunKnowledge>(`/runs/${runId}/knowledge`),

  getRunTelemetry: (runId: string) =>
    request<TelemetryEvent[]>(`/runs/${runId}/telemetry`),

  createRun: (payload: {
    topic_id: string;
    channel_id: string;
    actor_id: string;
    focus_id?: string;
  }) =>
    request<RunItem>('/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // The route is `/gates/pending`; `/gates` has never existed.
  getPendingGates: () => request<GateItem[]>('/gates/pending'),

  approveGate: (gateId: string, payload: ApproveGatePayload) =>
    request<ApprovalItem>(`/gates/${gateId}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rejectGate: (gateId: string, payload: RejectGatePayload) =>
    request<ApprovalItem>(`/gates/${gateId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getQuota: () => request<QuotaStatus>('/quota'),

  // The rows a Run needs before it can exist (T-64). Until these routes
  // existed the Launch form was three free-text boxes over IDs only the
  // terminal could reveal.
  getDomains: () => request<DomainItem[]>('/domains'),

  createDomain: (payload: { id: string; name: string; description: string }) =>
    request<DomainItem>('/domains', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getTopics: () => request<TopicItem[]>('/topics'),

  createTopic: (payload: {
    id: string;
    title: string;
    domain_id: string;
    entity_id?: string;
  }) =>
    request<TopicItem>('/topics', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getChannels: () => request<ChannelItem[]>('/channels'),

  createChannel: (payload: {
    id: string;
    name: string;
    audience_timezone: string;
  }) =>
    request<ChannelItem>('/channels', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getFocuses: () => request<FocusItem[]>('/focuses'),

  createFocus: (payload: {
    name: string;
    facets: { dimension: string; value: string }[];
    scope_mode: string;
    actor_id: string;
  }) =>
    request<FocusItem>('/focuses', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
