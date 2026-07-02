/**
 * Playwright global setup — fetches a Clerk Testing Token before any test runs.
 * This disables Clerk's bot-detection for the test run so clerk.signIn() (used
 * in generate.spec.ts) can authenticate without hitting a CAPTCHA/bot check.
 *
 * Reuses the same dev Clerk instance as local dev and production (not a
 * separate CI-only Clerk application) — see docs/roadmap.md's Phase 6 notes
 * for why. Requires NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY to
 * already be set in the environment (same vars the frontend app itself reads).
 */
import { clerkSetup } from '@clerk/testing/playwright'

export default async function globalSetup() {
  await clerkSetup({
    publishableKey: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
    secretKey: process.env.CLERK_SECRET_KEY,
  })
}
