/// <reference types="vite/client" />
import {
  RunItem,
  GateItem,
  ApproveGatePayload,
  RejectGatePayload,
  QuotaSummary,
} from './types';

const API_BASE = '/api';
const API_KEY = import.meta.env.VITE_API_KEY || 'atlas-dev-key'; // Default development API key
const MOCK_API = import.meta.env.VITE_MOCK_API === 'true';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  headers.set('X-API-Key', API_KEY);

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorBody}`);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<{ status: string; version?: string }>('/health'),

  getRuns: async (): Promise<RunItem[]> => {
    try {
      return await request<RunItem[]>('/runs');
    } catch (e) {
      if (!(import.meta.env.DEV && MOCK_API)) throw e;
      // Return simulated mock fallback when backend worker is not running in dev
      return [
        {
          id: 'run-8323-001',
          channel_id: 'ORIGINS',
          status: 'suspended',
          current_stage: 'asset_selection',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          updated_at: new Date().toISOString(),
          config: {
            focus_field: 'History',
            focus_note: 'Rosetta Stone decipherment',
            scope_mode: 'soft',
            duration_target: 60,
          },
        },
        {
          id: 'run-8323-002',
          channel_id: 'ORIGINS',
          status: 'completed',
          current_stage: 'final_approval',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          updated_at: new Date(Date.now() - 1800000).toISOString(),
          config: {
            focus_field: 'Science',
            focus_note: 'Discovery of Cosmic Microwave Background',
            scope_mode: 'soft',
            duration_target: 60,
          },
        },
      ];
    }
  },

  getRun: (id: string): Promise<RunItem> => request<RunItem>(`/runs/${id}`),

  createRun: async (payload: {
    channel_id: string;
    focus_field: string;
    focus_note: string;
    scope_mode: string;
    duration: number;
    render_targets: string[];
  }): Promise<RunItem> => {
    return request<RunItem>('/runs', {
      method: 'POST',
      body: JSON.stringify({
        channel_id: payload.channel_id,
        actor_id: 'operator-web',
        config: {
          field: payload.focus_field,
          note: payload.focus_note,
          scope_mode: payload.scope_mode,
          duration: payload.duration,
          render_targets: payload.render_targets,
        },
      }),
    });
  },

  getGates: async (): Promise<GateItem[]> => {
    try {
      return await request<GateItem[]>('/gates');
    } catch (e) {
      if (!(import.meta.env.DEV && MOCK_API)) throw e;
      // Mock pending gate for Rosetta Stone video review
      return [
        {
          id: 'gate-asset-001',
          run_id: 'run-8323-001',
          stage: 'asset_selection',
          gate_type: 'manual',
          status: 'open',
          reason: 'Invariant 9: Human review required for visual assets and AI image clearances',
          created_at: new Date(Date.now() - 1200000).toISOString(),
          metadata: {
            assets: [
              {
                id: 'ast-1',
                title: 'Rosetta Stone granodiorite slab archival scan',
                author: 'British Museum Archival Collection',
                license: 'Public Domain',
                is_ai_generated: false,
              },
              {
                id: 'ast-2',
                title: 'Horapollo Hieroglyphica woodcut (1505)',
                author: 'Bibliothèque nationale de France',
                license: 'Public Domain',
                is_ai_generated: false,
              },
              {
                id: 'ast-3',
                title: 'Champollion portrait by Léon Cogniet (1831)',
                author: 'Musée du Louvre',
                license: 'Public Domain',
                is_ai_generated: false,
              },
              {
                id: 'ast-4',
                title: 'Neural reconstruction of Rosetta discovery site at Rashid fort (1799)',
                author: 'Atlas Stable Diffusion Local (Prompt v3.2)',
                license: 'AI-Generated (Requires Human Clearance)',
                is_ai_generated: true,
              },
            ],
            script: {
              beats: [
                {
                  index: 1,
                  text: 'July 1799. French soldiers uncover a granodiorite slab near Rashid.',
                  claim_ids: ['CLM-001'],
                  char_count: 67,
                },
                {
                  index: 2,
                  text: 'Carved with three scripts: Ancient Greek, Demotic, and Egyptian Hieroglyphs.',
                  claim_ids: ['CLM-002'],
                  char_count: 75,
                },
                {
                  index: 3,
                  text: 'He isolates the letters for Ptolemy proving hieroglyphs spell phonetic sounds.',
                  claim_ids: ['CLM-005'],
                  char_count: 78,
                },
              ],
            },
            quality_report: {
              overall_score: 84.5,
              passed: true,
              dimensions: {
                sourcing_integrity: { score: 95, weight: 20, status: 'pass' },
                hook_strength: { score: 82, weight: 15, status: 'pass' },
                narrative_arc: { score: 80, weight: 15, status: 'pass' },
                language_craft: { score: 88, weight: 15, status: 'pass' },
                factual_density: { score: 85, weight: 10, status: 'pass' },
                novelty: { score: 80, weight: 10, status: 'pass' },
                visual_coherence: { score: 82, weight: 10, status: 'pass' },
                technical_compliance: { score: 95, weight: 5, status: 'pass' },
              },
              deterministic_checks: [
                { name: 'All beats carry Claims', passed: true, message: '3/3 beats verified' },
                { name: 'Licenses verified', passed: true, message: 'All assets cleared' },
                { name: 'Duration within ±2s', passed: true, message: '60.0s exact' },
                { name: 'Loudness −14 LUFS', passed: true, message: '-14.1 LUFS' },
              ],
            },
          },
        },
      ];
    }
  },

  approveGate: (gateId: string, payload: ApproveGatePayload) =>
    request<{ success: boolean; gate_id: string; resumed: boolean }>(
      `/gates/${gateId}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  rejectGate: (gateId: string, payload: RejectGatePayload) =>
    request<{ success: boolean; gate_id: string; rejection_type: string }>(
      `/gates/${gateId}/reject`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  getQuota: async (): Promise<QuotaSummary[]> => {
    return [
      {
        provider: 'Google Gemini 2.0 Flash (Tier 2)',
        consumed: 18,
        limit_per_day: 1500,
        unit: 'RPM / RPD',
        reset_in_seconds: 43200,
      },
      {
        provider: 'Ollama Qwen 3 8B Local (Tier 1)',
        consumed: 94,
        limit_per_day: 999999,
        unit: 'Calls (Unlimited GPU)',
        reset_in_seconds: 0,
      },
      {
        provider: 'Nomic Embed Text (Tier 1)',
        consumed: 142,
        limit_per_day: 999999,
        unit: 'Embeddings (Local GPU)',
        reset_in_seconds: 0,
      },
    ];
  },
};
