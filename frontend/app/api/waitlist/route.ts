import { NextRequest, NextResponse } from 'next/server'

// Public, unauthenticated pass-through to the backend's POST /waitlist (Phase 8).
// Must stay excluded from proxy.ts's auth.protect() — visitors hitting this have
// no Clerk session yet, that's the whole point of a pre-auth waitlist. Deliberately
// not routed through app/api/[...path]/route.ts, which requires a valid Clerk
// token before forwarding anything — this is a more specific path, so Next.js
// matches it first (same pattern as app/api/health/route.ts).
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

export async function POST(request: NextRequest) {
  const body = await request.text()

  let res: Response
  try {
    res = await fetch(`${BACKEND_URL}/waitlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
  } catch (err) {
    console.error('[waitlist proxy] Backend unreachable:', err)
    return NextResponse.json({ detail: 'Backend unavailable' }, { status: 502 })
  }

  const data = await res.text()
  return new NextResponse(data, {
    status: res.status,
    headers: { 'Content-Type': res.headers.get('content-type') ?? 'application/json' },
  })
}
