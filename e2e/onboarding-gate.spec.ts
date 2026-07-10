/**
 * E2E: Onboarding gate resilience (app/page.tsx)
 *
 * Regression coverage for a real bug: a brand-new user's very first load fires
 * two concurrent authenticated requests (Promise.all([getProfile, getApiKeyStatus]))
 * against a backend that JIT-provisions the local user row on first sighting.
 * That JIT provisioning used to race under concurrency and occasionally 500
 * (see backend/tests/integration/test_auth.py's
 * test_concurrent_first_sign_in_does_not_500_on_jit_race for the server-side fix).
 * The frontend's response to any failure during the gate check was to fail
 * open straight to the idle/generation screen — which, for a user we've never
 * successfully checked, is exactly backwards: it skipped profile and API-key
 * gating entirely.
 *
 * These tests intercept /admin/profile at the network layer to simulate that
 * failure directly, without depending on the backend's race actually firing.
 */
import { test, expect, Page } from '@playwright/test'
import { signInTestUser } from './fixtures/auth'

test.beforeEach(async ({ page }) => {
  await signInTestUser(page)
})

const API_KEY_OK = {
  provider: 'anthropic',
  has_key: true,
  key_hint: 'sk-ant-...xyz',
  label: null,
  last_verified_at: new Date().toISOString(),
}

const EMPTY_PROFILE = {
  personal: null,
  education: [],
  experience: [],
  projects: [],
  skills: [],
}

async function mockApiKeyAlwaysOk(page: Page) {
  await page.route('**/admin/settings/api-key', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(API_KEY_OK) })
  )
}

test('recovers via retry when the first onboarding-gate check fails, instead of skipping straight to the generation screen', async ({ page }) => {
  await mockApiKeyAlwaysOk(page)

  let profileCallCount = 0
  await page.route('**/admin/profile', route => {
    profileCallCount++
    if (profileCallCount === 1) {
      // Simulates the losing side of the JIT-provisioning race.
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal Server Error' }) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_PROFILE) })
  })

  await page.goto('/')

  // Must land on the real profile-setup gate — not the bare generation textarea,
  // which would mean the failed first attempt was silently treated as "all clear."
  await expect(page.getByRole('heading', { name: /set up your profile/i })).toBeVisible({ timeout: 10_000 })
  await expect(page.getByPlaceholder('Paste a job description…')).not.toBeVisible()

  expect(profileCallCount).toBeGreaterThanOrEqual(2)
})

test('still falls open to idle if every retry fails, rather than leaving the user stuck', async ({ page }) => {
  await mockApiKeyAlwaysOk(page)
  await page.route('**/admin/profile', route =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal Server Error' }) })
  )
  await page.route('**/admin/jobs/insights', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, headline: null, observed: null, gap: null, action: null }) })
  )

  await page.goto('/')

  await expect(page.getByPlaceholder('Paste a job description…')).toBeVisible({ timeout: 10_000 })
})
