import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

// Hop-by-hop headers must not be forwarded across a proxy boundary.
// content-encoding is excluded because Node's fetch decompresses automatically —
// forwarding it would claim the response is still compressed when it isn't.
// authorization is excluded too — the browser's own Authorization header (if any)
// is replaced below with the Clerk session token, never passed through verbatim.
const HOP_BY_HOP = new Set([
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-encoding', 'authorization',
])

async function proxy(request: NextRequest, pathSegments: string[]): Promise<NextResponse> {
  const backendPath = '/' + pathSegments.join('/')
  const search = request.nextUrl.search
  const url = `${BACKEND_URL}${backendPath}${search}`

  const { getToken } = await auth()
  const token = await getToken()
  if (!token) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })
  }

  const forwardHeaders = new Headers()
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (!HOP_BY_HOP.has(lower) && lower !== 'host') {
      forwardHeaders.set(key, value)
    }
  })
  forwardHeaders.set('authorization', `Bearer ${token}`)

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD'
  const body = hasBody ? await request.arrayBuffer() : undefined

  let res: Response
  try {
    res = await fetch(url, {
      method: request.method,
      headers: forwardHeaders,
      body: body as BodyInit | undefined,
    })
  } catch (err) {
    console.error('[proxy] Backend unreachable:', err)
    return NextResponse.json({ detail: 'Backend unavailable' }, { status: 502 })
  }

  const responseHeaders = new Headers()
  res.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      responseHeaders.set(key, value)
    }
  })

  return new NextResponse(res.body, {
    status: res.status,
    headers: responseHeaders,
  })
}

type Ctx = { params: Promise<{ path: string[] }> }

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path)
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path)
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path)
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path)
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path)
}
