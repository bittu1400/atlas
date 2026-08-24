export type RunStatus =
  | 'pending'
  | 'running'
  | 'suspended'
  | 'reworking'
  | 'completed'
  | 'failed'
  | 'abandoned';

export type PipelineStage =
  | 'idea_discovery'
  | 'topic_selection'
  | 'research'
  | 'claim_extraction'
  | 'fact_verification'
  | 'knowledge_object'
  | 'story_angle'
  | 'script'
  | 'timing_plan'
  | 'asset_discovery'
  | 'asset_selection'
  | 'storyboard'
  | 'sound_design'
  | 'render'
  | 'quality_check'
  | 'final_approval'
  | 'publish';

export interface RunItem {
  id: string;
  channel_id: string;
  status: RunStatus;
  current_stage: PipelineStage;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  config?: Record<string, unknown>;
}

export interface GateItem {
  id: string;
  run_id: string;
  stage: string;
  gate_type: 'manual' | 'automatic' | 'hybrid';
  status: 'open' | 'approved' | 'rejected' | 'bypassed';
  reason?: string;
  created_at: string;
  resolved_at?: string | null;
  metadata?: {
    candidate_topics?: Array<{ id: string; title: string; score: number; reason: string }>;
    knowledge_object?: {
      title: string;
      version: number;
      claims: Array<{ id: string; text: string; assertion_type: string; evidence_count: number }>;
    };
    story_angles?: Array<{ id: string; angle: string; hook: string; score: number }>;
    script?: {
      beats: Array<{
        index: number;
        text: string;
        claim_ids: string[];
        char_count: number;
      }>;
    };
    assets?: Array<{
      id: string;
      title: string;
      author: string;
      license: string;
      is_ai_generated: boolean;
      preview_url?: string;
    }>;
    quality_report?: {
      overall_score: number;
      passed: boolean;
      dimensions: Record<string, { score: number; weight: number; status: 'pass' | 'fail' }>;
      deterministic_checks: Array<{ name: string; passed: boolean; message: string }>;
    };
  };
}

export interface ApproveGatePayload {
  actor_id: string;
  artifact_version_id?: string;
  metadata?: Record<string, unknown>;
}

export interface RejectGatePayload {
  actor_id: string;
  rejection_type: 'regenerate' | 'branch' | 'abandon';
  critique: {
    rubric_dimension: string;
    target_beat_index?: number;
    target_asset_id?: string;
    reason: string;
  };
}

export interface QuotaSummary {
  provider: string;
  consumed: number;
  limit_per_day: number;
  unit: string;
  reset_in_seconds: number;
}
