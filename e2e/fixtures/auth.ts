/**
 * Shared Clerk sign-in helper for E2E tests. Signs in as a dedicated test user
 * (careeros-e2e-test@example.com) created via Clerk's Backend API specifically
 * for CI — not a real person's account. See docs/roadmap.md's Phase 6 notes.
 *
 * Uses the emailAddress (ticket-based) sign-in mode rather than a password:
 * Clerk's "Client Trust" attack-protection feature requires a second-factor
 * email verification on every password sign-in from an unrecognized device —
 * which every fresh Playwright browser context is — and @clerk/testing's
 * password strategy doesn't handle that status, so the session silently never
 * activates. The emailAddress mode creates a sign-in token via the Backend API
 * and bypasses all verification (including Client Trust and MFA) by design.
 *
 * Requires CLERK_E2E_TEST_EMAIL and CLERK_SECRET_KEY in the environment.
 */
import { clerk } from '@clerk/testing/playwright'
import { Page } from '@playwright/test'

export async function signInTestUser(page: Page) {
  const emailAddress = process.env.CLERK_E2E_TEST_EMAIL
  if (!emailAddress) {
    throw new Error('CLERK_E2E_TEST_EMAIL must be set to run authenticated E2E tests.')
  }

  // clerk.signIn() requires an already-loaded, unprotected page that loads Clerk.
  await page.goto('/sign-in')
  await clerk.signIn({ page, emailAddress })
}
