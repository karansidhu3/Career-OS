/**
 * E2E: Terms of Service / Privacy Policy pages (Phase 8)
 *
 * Public routes — must be reachable without signing in, and linked from the
 * signed-out landing page.
 */
import { test, expect } from '@playwright/test'

test.describe('legal pages', () => {
  test('/terms is reachable while signed out', async ({ page }) => {
    await page.goto('/terms')
    await expect(page.getByRole('heading', { name: 'Terms of Service' })).toBeVisible()
  })

  test('/privacy is reachable while signed out', async ({ page }) => {
    await page.goto('/privacy')
    await expect(page.getByRole('heading', { name: 'Privacy Policy' })).toBeVisible()
  })

  test('landing page links to both', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: 'Terms' }).click()
    await expect(page).toHaveURL(/\/terms/)

    await page.goto('/')
    await page.getByRole('link', { name: 'Privacy' }).click()
    await expect(page).toHaveURL(/\/privacy/)
  })
})
