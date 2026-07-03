import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// /api/health must stay public — it's the uptime-monitor healthcheck target,
// and the probe never carries a Clerk session. / is public (Phase 8) so signed-out
// visitors see the waitlist landing page instead of being redirected to sign-in —
// app/page.tsx itself branches on auth state to render landing vs. the real app.
// /api/waitlist is the pre-auth signup's own backend pass-through (same reasoning).
const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/api/health', '/', '/api/waitlist'])

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
