/**
 * E2E: Core generation flow
 *
 * These tests drive the primary product loop: paste JD → generate → view result.
 * The Claude API and PDF compilation are intercepted at the network layer so
 * tests run fast and hermetically without real API credentials.
 */
import { test, expect, Page } from '@playwright/test'
import { readFileSync } from 'fs'
import { join } from 'path'
import { signInTestUser } from './fixtures/auth'

const SAMPLE_JD = readFileSync(join(__dirname, 'fixtures/sample-jd.txt'), 'utf-8')

// Every route these tests visit (/, /applications) sits behind Clerk's auth
// middleware — sign in once per test as the dedicated E2E test user before
// touching any of them.
test.beforeEach(async ({ page }) => {
  await signInTestUser(page)
})

// Stable mock data that mirrors the real API response shape
const MOCK_JOB_PROCESSING = {
  id: 1,
  title: 'Generating…',
  company: null,
  status: 'processing',
  fit_score: null,
  resume_latex: null,
  cover_letter: null,
  strategic_note: null,
  selected_projects: null,
  compression_attempts: null,
  input_tokens: null,
  output_tokens: null,
  cache_read_tokens: null,
  cache_write_tokens: null,
  cost_usd: null,
  created_at: new Date().toISOString(),
  description: SAMPLE_JD,
  url: null,
}

const MOCK_JOB_GENERATED = {
  ...MOCK_JOB_PROCESSING,
  title: 'Senior Software Engineer',
  company: 'Acme Platform Co',
  status: 'generated',
  fit_score: 8,
  strategic_note: [
    'GOOD FIT',
    '• Strong Python and FastAPI background matches core requirements',
    '• PostgreSQL and async experience directly applicable',
    '',
    'GAPS',
    '• No explicit distributed systems production experience listed',
    '',
    'IMPROVEMENT PLAN',
    '• Quantify scale of data handled in MarketMind pipeline',
  ].join('\n'),
  selected_projects: ['MarketMind AI', 'Agentic Market Sentiment System'],
  cover_letter: [
    'The backend platform scope here — async ingestion, PostgreSQL schema ownership, and ML inference in the request path — maps closely to the work I have been doing on CareerOS and MarketMind AI.',
    '',
    'MarketMind AI is a persistent investment intelligence platform I built from scratch. The ingestion layer pulls SEC filings daily through a multi-agent pipeline I designed: a FastAPI async service routes documents through Qdrant for semantic retrieval, with Redis handling rate limiting and cache invalidation. I owned the PostgreSQL schema, including the vector-adjacent metadata tables, and tuned queries for sub-200ms p99 latency at realistic filing volumes.',
    '',
    'I am available immediately and happy to discuss the role further.',
  ].join('\n'),
  resume_latex: '\\documentclass{article}\\begin{document}Test Resume\\end{document}',
  compression_attempts: 0,
  input_tokens: 4500,
  output_tokens: 1200,
  cache_read_tokens: 3000,
  cache_write_tokens: 500,
  cost_usd: 0.032,
}

async function setupMocks(page: Page) {
  let callCount = 0

  // GET /admin/settings/api-key and /admin/profile → mocked so the mount-time
  // onboarding-gate check (page.tsx) always resolves to the idle/textarea
  // state, regardless of the real backend's state for this Clerk test user.
  await page.route('**/admin/settings/api-key', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ provider: 'anthropic', has_key: true, key_hint: 'sk-ant-...xyz', label: null, last_verified_at: new Date().toISOString() }),
    })
  )
  await page.route('**/admin/profile', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        personal: { id: 1, name: 'Test User', email: 'careeros-e2e-test@example.com', phone: null, linkedin: null, github: null, location: null, resume_template: 'jake', custom_preamble: null },
        education: [],
        experience: [{ id: 1, company: 'Acme', title: 'Engineer', start_date: '2024-01', end_date: null, bullets: ['Did things'] }],
        projects: [],
        skills: [],
      }),
    })
  )

  // POST /admin/jobs/generate → returns processing job immediately
  await page.route('**/admin/jobs/generate', route =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_JOB_PROCESSING) })
  )

  // GET /admin/jobs/1 → first call returns processing, subsequent return generated
  await page.route('**/admin/jobs/1', route => {
    callCount++
    const body = callCount <= 1 ? MOCK_JOB_PROCESSING : MOCK_JOB_GENERATED
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  // GET /admin/jobs → empty list (no history)
  await page.route('**/admin/jobs', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  )

  // GET /admin/jobs/insights → below threshold
  await page.route('**/admin/jobs/insights', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 1, headline: null, observed: null, gap: null, action: null }) })
  )

  // PDF preview endpoint → minimal PDF bytes
  await page.route('**/admin/jobs/1/resume-preview.pdf', route =>
    route.fulfill({ status: 200, contentType: 'application/pdf', body: Buffer.from('%PDF-1.4 minimal') })
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('generation flow', () => {
  test('textarea is focused on page load', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeFocused()
  })

  test('generates application from pasted job description', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')

    const textarea = page.locator('textarea').first()
    await textarea.fill(SAMPLE_JD)

    // Submit with Cmd+Enter (Mac) / Ctrl+Enter (others)
    await textarea.press('Meta+Enter')

    // Generating state should appear
    await expect(page.locator('text=Generating').first()).toBeVisible({ timeout: 5_000 })

    // Wait for result state — score ring or company name
    await expect(page.locator('text=Senior Software Engineer').first()).toBeVisible({ timeout: 15_000 })
  })

  test('shows fit score after generation', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')

    await page.locator('textarea').first().fill(SAMPLE_JD)
    await page.locator('textarea').first().press('Meta+Enter')

    await expect(page.locator('text=Acme Platform Co').first()).toBeVisible({ timeout: 15_000 })
    // Score 8 should be visible somewhere on the page
    await expect(page.locator('text=8').first()).toBeVisible()
  })

  test('shows analysis sections after generation', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')

    await page.locator('textarea').first().fill(SAMPLE_JD)
    await page.locator('textarea').first().press('Meta+Enter')

    await expect(page.locator('text=Acme Platform Co').first()).toBeVisible({ timeout: 15_000 })

    await expect(page.locator('text=GOOD FIT').first()).toBeVisible()
    await expect(page.locator('text=GAPS').first()).toBeVisible()
  })

  test('persists JD in sessionStorage and restores on reload', async ({ page }) => {
    await setupMocks(page)
    await page.goto('/')

    const partial = 'Senior Backend Engineer at a fast-growing startup'
    await page.locator('textarea').first().fill(partial)

    await page.reload()
    await setupMocks(page)

    const textarea = page.locator('textarea').first()
    await expect(textarea).toHaveValue(partial, { timeout: 3_000 })
  })
})

test.describe('applications flow', () => {
  test('applications page renders without error', async ({ page }) => {
    await page.route('**/admin/jobs', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    )
    await page.route('**/admin/jobs/insights', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, headline: null, observed: null, gap: null, action: null }) })
    )

    await page.goto('/applications')
    // Should show empty state, not an error
    await expect(page.locator('body')).not.toContainText('Error')
    await expect(page.locator('body')).not.toContainText('500')
  })
})
