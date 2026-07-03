/**
 * E2E: Signed-out waitlist landing page (Phase 8)
 *
 * Deliberately does NOT sign in — the whole point is the pre-auth experience.
 * A real browser (unlike the embedded preview tool, which cannot complete
 * navigation to this app in this environment — see feedback memory) is the
 * only way this session could visually/functionally confirm this feature.
 */
import { test, expect } from '@playwright/test'

test.describe('signed-out landing page', () => {
  test('shows the waitlist form, not the core app', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: 'CareerOS' })).toBeVisible()
    await expect(page.getByText(/you bring your own ai key/i)).toBeVisible()
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible()
    // The real app's textarea must not be reachable without signing in.
    await expect(page.locator('textarea')).toHaveCount(0)
  })

  test('joining the waitlist shows a confirmation', async ({ page }) => {
    await page.route('**/api/waitlist', route =>
      route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ status: 'joined' }) })
    )
    await page.goto('/')

    await page.getByPlaceholder('you@example.com').fill('friend@example.com')
    await page.getByRole('button', { name: /join the waitlist/i }).click()

    await expect(page.getByText(/you.re on the list/i)).toBeVisible()
  })

  test('has a sign-in link for already-invited users', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/sign-in/)
  })
})
