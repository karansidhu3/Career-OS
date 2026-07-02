/**
 * Shared Clerk sign-in helper for E2E tests. Signs in as a dedicated test user
 * (careeros-e2e-test@example.com) created via Clerk's Backend API specifically
 * for CI — not a real person's account. See docs/roadmap.md's Phase 6 notes.
 *
 * Requires CLERK_E2E_TEST_EMAIL / CLERK_E2E_TEST_PASSWORD in the environment.
 */
import { clerk } from '@clerk/testing/playwright'
import { Page } from '@playwright/test'

export async function signInTestUser(page: Page) {
  const identifier = process.env.CLERK_E2E_TEST_EMAIL
  const password = process.env.CLERK_E2E_TEST_PASSWORD
  if (!identifier || !password) {
    throw new Error('CLERK_E2E_TEST_EMAIL and CLERK_E2E_TEST_PASSWORD must be set to run authenticated E2E tests.')
  }

  // clerk.signIn() requires an already-loaded, unprotected page that loads Clerk.
  await page.goto('/sign-in')
  await clerk.signIn({
    page,
    signInParams: { strategy: 'password', identifier, password },
  })
}
