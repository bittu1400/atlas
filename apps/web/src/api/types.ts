// Wire types for the Atlas API.
//
// Every interface here mirrors a response model in `apps/api/schemas.py` or
// `atlas.application.usecases.inspect_run`. The previous version described an
// API that did not exist — `current_stage`, `gate.stage`, `gate.metadata`, a
// `'open'` gate status — so the dashboard only ever rendered against the mock
// fallbacks that used to live in `client.ts` (defect V-03).

export type RunStatus =
  | 'pending'
  | 'running'
  | 'suspended'
  | 'reworking'
  | 'completed'
  | 'failed'
  | 'abandoned';

export type StepStatus =
  | 'pending'
  | 'running'
  | 'suspended'
  | 'succeeded'
  | 'failed'
  | 'skipped';

export type GateStatus = 'pending' | 'approved' | 'rejected';
export type GateType = 'automatic' | 'manual' | 'hybrid';

export type AssertionType = 'fact' | 'inference' | 'opinion' | 'contested';
export type ClaimStatus =
  | 'verified'
  | 'unverified'
  | 'unsupported'
  | 'refuted'
  | 'contested';

/** `RunResponse` */
export interface RunItem {
  id: string;
  topic_id: string;
  channel_id: string;
  status: RunStatus;
  captured_focus: Record<string, unknown>;
  trace_id: string;
  actor_id: string;
  error?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

/** `StepResponse` */
export interface StepItem {
  id: string;
  run_id: string;
  step_name: string;
  step_index: number;
  status: StepStatus;
  input_hash: string;
  output_artifact_ref?: string | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

/** `GateResponse` */
export interface GateItem {
  id: string;
  run_id: string;
  step_id: string;
  gate_type: GateType;
  status: GateStatus;
  requested_at: string;
  resolved_at?: string | null;
}

/** `ApproveGateRequest` */
export interface ApproveGatePayload {
  actor_id: string;
}

export type RejectionAction = 'regenerate' | 'branch' | 'abandon';

/** `RejectGateRequest` — every field is mandatory server-side (SPEC §7). */
export interface RejectGatePayload {
  target_ref: string;
  rubric_dimension: string;
  reason: string;
  action: RejectionAction;
  actor_id: string;
}

/** `ApprovalResponse` */
export interface ApprovalItem {
  id: string;
  gate_id: string;
  run_id: string;
  actor_id: string;
  decision: 'approved' | 'rejected';
  feedback?: Record<string, unknown> | null;
  created_at: string;
}

/** `QuotaStatusResponse` */
export interface QuotaStatus {
  status: string;
  providers: Record<
    string,
    { rpm_remaining: number; rpd_remaining: number; status: string }
  >;
}

/** `EvidenceView` */
export interface EvidenceItem {
  evidence_id: string;
  quote: string;
  locator: string;
  stance: 'supports' | 'contradicts';
  source_id: string;
  source_title: string;
  source_url: string;
  source_tier: string;
  snapshot_id: string;
  snapshot_sha256: string;
  retrieved_at: string;
}

/** `ClaimView` */
export interface ClaimItem {
  claim_id: string;
  version: number;
  text: string;
  assertion_type: AssertionType;
  status: ClaimStatus;
  confidence: number;
  evidence: EvidenceItem[];
}

/** `RunKnowledgeView` */
export interface RunKnowledge {
  run_id: string;
  topic_id: string;
  ko_id?: string | null;
  ko_version?: number | null;
  claims: ClaimItem[];
}

/** `TelemetryEvent` */
export interface TelemetryEvent {
  id: string;
  timestamp: string;
  kind: 'step' | 'model_call';
  stage: string;
  event: string;
  status: string;
  detail: Record<string, string>;
}
