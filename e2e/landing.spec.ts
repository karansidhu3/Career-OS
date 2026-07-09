/**
 * E2E: Signed-out landing page
 *
 * Deliberately does NOT sign in — the whole point is the pre-auth experience.
 */
import { test, expect } from '@playwright/test'

test.describe('signed-out landing page', () => {
  test('shows the landing form, not the core app', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: 'CareerOS' })).toBeVisible()
    await expect(page.getByText(/paste a job description/i)).toBeVisible()
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible()
    // The real app's textarea must not be reachable without signing in.
    await expect(page.locator('textarea')).toHaveCount(0)
  })

  test('entering email navigates to sign-up', async ({ page }) => {
    await page.goto('/')

    await page.getByPlaceholder('you@example.com').fill('friend@example.com')
    await page.getByRole('button', { name: /get started/i }).click()

    await expect(page).toHaveURL(/\/sign-up/)
  })

  test('has a sign-in link for existing users', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/sign-in/)
  })
})
