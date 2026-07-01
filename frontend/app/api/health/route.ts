import { NextResponse } from 'next/server'

// Public, unauthenticated endpoint for Railway's health probe. Must stay excluded
// from proxy.ts's auth.protect() — the probe never carries a Clerk session, and
// this is a more specific route than app/api/[...path]/route.ts, so Next.js
// matches this literal path first rather than proxying it to the backend.
export async function GET() {
  return NextResponse.json({ status: 'ok' })
}
