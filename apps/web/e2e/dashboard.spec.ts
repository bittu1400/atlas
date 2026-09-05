import { test, expect } from '@playwright/test';

// Task T-55: Browser tests verifying that the operator dashboard renders
// real API responses rather than invented fixtures or fallbacks.
//
// These 4 assertions directly map to what broke during defect V-03:
// 1. A Run row renders the API's topic_id (not hardcoded Rosetta Stone).
// 2. A pending Gate renders its step_id.
// 3. A failed approve displays the error banner and leaves the gate pending.
// 4. The Knowledge panel renders the snapshot_sha256 returned by the API.

test.describe('Operator Dashboard (Anti-Fabrication & API Honesty)', () => {
  test('Assertion 1: a Run row renders the API topic_id', async ({ page }) => {
    const dynamicTopic = 'topic_synth_experimental_physics_99';
    const runId = 'run_e2e_001';

    await page.route('/api/runs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: runId,
            topic_id: dynamicTopic,
            channel_id: 'channel_synth_01',
            status: 'running',
            actor_id: 'op_e2e',
            error: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            completed_at: null,
          },
        ]),
      });
    });

    await page.route('/api/gates/pending', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/');

    // Expect the table to render the run ID and the exact topic_id returned from API
    await expect(page.getByText(runId)).toBeVisible();
    await expect(page.getByText(dynamicTopic)).toBeVisible();
  });

  test('Assertion 2: a pending Gate renders its step_id', async ({ page }) => {
    const dynamicStep = 'step_synth_asset_review_42';
    const gateId = 'gate_e2e_002';
    const runId = 'run_e2e_002';

    await page.route('/api/runs', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.route('/api/gates/pending', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: gateId,
            run_id: runId,
            step_id: dynamicStep,
            gate_type: 'asset_selection',
            status: 'pending',
            requested_at: new Date().toISOString(),
            resolved_at: null,
          },
        ]),
      });
    });

    await page.goto('/');

    // Navigate to Approval Queue
    await page.getByRole('button', { name: /Approval Queue/i }).click();

    // Verify the gate step_id is rendered on the screen
    await expect(page.getByRole('heading', { name: dynamicStep })).toBeVisible();
    await expect(page.getByText(`Run: ${runId}`)).toBeVisible();
  });

  test('Assertion 3: a failed approve shows an error and leaves the gate pending', async ({ page }) => {
    const dynamicStep = 'step_synth_fail_gate_07';
    const gateId = 'gate_e2e_003';
    const runId = 'run_e2e_003';
    const errorDetail = 'Database write rejected by lock policy';

    await page.route('/api/runs', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.route('/api/gates/pending', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: gateId,
            run_id: runId,
            step_id: dynamicStep,
            gate_type: 'script_approval',
            status: 'pending',
            requested_at: new Date().toISOString(),
            resolved_at: null,
          },
        ]),
      });
    });

    // Mock approve failure
    await page.route(`/api/gates/${gateId}/approve`, async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'text/plain',
        body: errorDetail,
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /Approval Queue/i }).click();

    // Click Approve button
    await page.getByRole('button', { name: /Approve & Resume/i }).click();

    // Verify the error banner appears with the failure details
    const errorBanner = page.getByText(/Gate action failed, nothing was recorded:/i);
    await expect(errorBanner).toBeVisible();
    await expect(page.getByText(errorDetail)).toBeVisible();

    // Verify the gate remains pending on screen (not marked approved or resolved)
    await expect(page.getByRole('heading', { name: dynamicStep })).toBeVisible();
  });

  test('Assertion 4: Knowledge panel renders the snapshot_sha256 returned by API', async ({ page }) => {
    const runId = 'run_e2e_004';
    const dynamicShaPrefix = '1234567890abcdef';
    const fullSha = `${dynamicShaPrefix}fedcba09876543211234567890abcdef1234567890abcdef1234567890abcdef`;

    await page.route('/api/runs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: runId,
            topic_id: 'topic_synth_origins',
            channel_id: 'channel_synth',
            status: 'completed',
            actor_id: 'op_e2e',
            error: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.route('/api/gates/pending', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.route(`/api/runs/${runId}/knowledge`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: runId,
          topic_id: 'topic_synth_origins',
          ko_id: 'KO-SYNTH-E2E',
          ko_version: 1,
          claims: [
            {
              claim_id: 'CLM-SYNTH-01',
              version: 1,
              text: 'Synthetic statement for browser verification.',
              assertion_type: 'fact',
              status: 'verified',
              confidence: 0.95,
              evidence: [
                {
                  evidence_id: 'EV-SYNTH-01',
                  quote: 'Synthetic quote from primary source.',
                  source_url: 'https://example.com/synth-evidence',
                  source_title: 'Synthetic Primary Archive',
                  source_tier: 1,
                  stance: 'supports',
                  snapshot_sha256: fullSha,
                  retrieved_at: new Date().toISOString(),
                },
              ],
            },
          ],
        }),
      });
    });

    await page.goto('/');

    // Inspect selects the Run and opens the Pipeline tab, which is where a
    // suspended Run's stage actually is. The Knowledge panel is one tab over
    // and keeps the selection; this assertion is about what that panel renders,
    // not about which tab Inspect lands on.
    await page.getByRole('button', { name: /Inspect/i }).click();
    await page.getByRole('button', { name: 'Knowledge' }).click();

    // Verify Knowledge Object header and dynamic claim text
    await expect(page.getByText('Knowledge Object KO-SYNTH-E2E (v1)')).toBeVisible();
    await expect(page.getByText('Synthetic statement for browser verification.')).toBeVisible();

    // Verify that the screen renders the exact snapshot_sha256 prefix from the API response
    // Format rendered: sha256:{ev.snapshot_sha256.slice(0, 16)}…
    await expect(page.getByText(`sha256:${dynamicShaPrefix}…`)).toBeVisible();
  });
});

// Task T-64: the Launch form's three inputs were free text over IDs only the
// terminal could reveal, so an operator's first feedback on a typo was a 404.
// These assertions hold the pickers to the same standard as the panels above:
// every option is a row the API returned, and an empty table is shown as empty
// rather than filled in with something plausible (R13).

test.describe('Launch form pickers (T-64)', () => {
  const emptyDashboard = async (page: import('@playwright/test').Page) => {
    await page.route('/api/runs', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
    await page.route('/api/gates/pending', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
  };

  test('Assertion 5: the Topic picker lists exactly what /topics returned', async ({ page }) => {
    const synthTopic = 'topic_synth_cartography_77';

    await emptyDashboard(page);
    await page.route('/api/topics', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: synthTopic,
            title: 'PLACEHOLDER_SYNTH_TITLE',
            domain_id: 'dom_synth_01',
            entity_id: null,
            status: 'proposed',
            created_at: new Date().toISOString(),
          },
        ]),
      }),
    );
    await page.route('/api/channels', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
    await page.route('/api/domains', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
    await page.route('/api/focuses', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );

    await page.goto('/');

    const picker = page.locator('#topic-id');
    await expect(picker.locator('option', { hasText: synthTopic })).toHaveCount(1);
    // One synthetic Topic plus the placeholder option, and nothing invented.
    await expect(picker.locator('option')).toHaveCount(2);
  });

  test('Assertion 6: an empty /topics is shown as empty, not filled in', async ({ page }) => {
    await emptyDashboard(page);
    for (const path of ['/api/topics', '/api/channels', '/api/domains', '/api/focuses']) {
      await page.route(path, (route) =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
      );
    }

    await page.goto('/');

    await expect(page.locator('#topic-id')).toContainText('No Topics exist yet');
    await expect(page.locator('#topic-id').locator('option')).toHaveCount(1);
  });

  test('Assertion 7: a refused Topic creation is reported, not swallowed', async ({ page }) => {
    await emptyDashboard(page);
    await page.route('/api/topics', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'DuplicateEntityError',
            message: "Topic 'topic_synth_dupe_01' already exists",
            entity_type: 'Topic',
            entity_id: 'topic_synth_dupe_01',
          }),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });
    await page.route('/api/channels', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
    await page.route('/api/focuses', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    );
    await page.route('/api/domains', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'dom_synth_01',
            name: 'PLACEHOLDER_SYNTH_DOMAIN',
            description: 'PLACEHOLDER_SYNTH_DESCRIPTION',
            research_profile: {},
          },
        ]),
      }),
    );

    await page.goto('/');

    await page.getByRole('button', { name: 'New topic' }).click();
    await page.locator('#new-topic-id').fill('topic_synth_dupe_01');
    await page.locator('#new-topic-title').fill('PLACEHOLDER_SYNTH_TITLE');
    await page.locator('#new-topic-domain').selectOption('dom_synth_01');
    await page.getByRole('button', { name: 'Create Topic' }).click();

    await expect(page.getByTestId('launcher-error')).toContainText('409');
    await expect(page.locator('#new-topic-id')).toHaveValue('topic_synth_dupe_01');
  });
});

// The Catalog tab and the Pipeline tab, added 2026-09-05. The Catalog is the
// only place an operator can create a Domain or a Focus at all; the Pipeline
// tab is the first thing in the dashboard to read `/runs/{id}/steps` and
// `/runs/{id}/gates`, which had existed unread since Phase 3.

test.describe('Catalog and Pipeline (T-64)', () => {
  const routeJson = async (
    page: import('@playwright/test').Page,
    path: string,
    body: unknown,
  ) => {
    await page.route(path, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      }),
    );
  };

  const synthDomain = {
    id: 'dom_synth_cartography',
    name: 'PLACEHOLDER_SYNTH_DOMAIN',
    description: 'PLACEHOLDER_SYNTH_DESCRIPTION',
    research_profile: {
      source_tier_floor: 'primary',
      preferred_apis: ['synth_api_one'],
      source_allowlist: ['*.placeholder.invalid', '*.placeholder.example'],
    },
  };

  test('Assertion 8: the Catalog renders a Domain Research Profile from the API', async ({
    page,
  }) => {
    await routeJson(page, '/api/runs', []);
    await routeJson(page, '/api/gates/pending', []);
    await routeJson(page, '/api/domains', [synthDomain]);
    await routeJson(page, '/api/topics', []);
    await routeJson(page, '/api/channels', []);
    await routeJson(page, '/api/focuses', []);

    await page.goto('/');
    await page.getByRole('button', { name: 'Catalog' }).click();

    await expect(page.getByText('PLACEHOLDER_SYNTH_DOMAIN')).toBeVisible();
    await expect(page.getByText('dom_synth_cartography')).toBeVisible();
    await expect(page.getByText('synth_api_one')).toBeVisible();
    await expect(page.getByText('2 patterns')).toBeVisible();
    // Empty tables are shown as empty, never filled in.
    await expect(page.getByText('No Topics exist.')).toBeVisible();
    await expect(page.getByText('No Channels exist.')).toBeVisible();
  });

  test('Assertion 9: a Domain can be created from the Catalog', async ({ page }) => {
    await routeJson(page, '/api/runs', []);
    await routeJson(page, '/api/gates/pending', []);
    await routeJson(page, '/api/topics', []);
    await routeJson(page, '/api/channels', []);
    await routeJson(page, '/api/focuses', []);

    let posted: Record<string, unknown> | null = null;
    await page.route('/api/domains', async (route) => {
      if (route.request().method() === 'POST') {
        posted = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(synthDomain),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Catalog' }).click();
    await page.getByRole('button', { name: 'New' }).first().click();

    await page.locator('#domain-id').fill('dom_synth_cartography');
    await page.locator('#domain-name').fill('PLACEHOLDER_SYNTH_DOMAIN');
    await page.locator('#domain-description').fill('PLACEHOLDER_SYNTH_DESCRIPTION');
    await page.getByRole('button', { name: 'Create Domain' }).click();

    await expect.poll(() => posted).toEqual({
      id: 'dom_synth_cartography',
      name: 'PLACEHOLDER_SYNTH_DOMAIN',
      description: 'PLACEHOLDER_SYNTH_DESCRIPTION',
    });
  });

  test('Assertion 10: the Pipeline tab renders Step rows and the Gate holding them', async ({
    page,
  }) => {
    const runId = 'run_synth_pipeline_01';
    const stepId = 'step_synth_script_approval_11';

    await routeJson(page, '/api/runs', [
      {
        id: runId,
        topic_id: 'topic_synth_cartography_77',
        channel_id: 'channel_synth_01',
        status: 'suspended',
        actor_id: 'op_e2e',
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        completed_at: null,
      },
    ]);
    await routeJson(page, '/api/gates/pending', []);
    await routeJson(page, '/api/topics', []);
    await routeJson(page, '/api/channels', []);
    await routeJson(page, '/api/domains', []);
    await routeJson(page, '/api/focuses', []);
    await routeJson(page, `/api/runs/${runId}/steps`, [
      {
        id: 'step_synth_research_02',
        run_id: runId,
        step_index: 2,
        step_name: 'PLACEHOLDER_SYNTH_STAGE_RESEARCH',
        status: 'succeeded',
        output_artifact_ref: 'snp_synth_01',
        error: null,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
      {
        id: stepId,
        run_id: runId,
        step_index: 11,
        step_name: 'PLACEHOLDER_SYNTH_STAGE_SCRIPT_APPROVAL',
        status: 'suspended',
        output_artifact_ref: null,
        error: null,
        started_at: new Date().toISOString(),
        completed_at: null,
      },
    ]);
    await routeJson(page, `/api/runs/${runId}/gates`, [
      {
        id: 'gate_synth_09',
        run_id: runId,
        step_id: stepId,
        gate_type: 'manual',
        status: 'pending',
        requested_at: new Date().toISOString(),
        resolved_at: null,
      },
    ]);

    await page.goto('/');
    await page.getByRole('button', { name: 'Inspect' }).first().click();

    await expect(page.getByText('PLACEHOLDER_SYNTH_STAGE_RESEARCH')).toBeVisible();
    await expect(page.getByText('PLACEHOLDER_SYNTH_STAGE_SCRIPT_APPROVAL')).toBeVisible();
    await expect(page.getByText('gate_synth_09')).toBeVisible();
    await expect(page.getByText('2 of 18 stages recorded')).toBeVisible();
  });
});
