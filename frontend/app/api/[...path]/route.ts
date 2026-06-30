import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.API_KEY ?? ''

// Hop-by-hop headers must not be forwarded across a proxy boundary.
// content-encoding is excluded because Node's fetch decompresses automatically —
// forwarding it would claim the response is still compressed when it isn't.
const HOP_BY_HOP = new Set([
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-encoding',
])

async function proxy(request: NextRequest, pathSegments: string[]): Promise<NextResponse> {
  const backendPath = '/' + pathSegments.join('/')
  const search = request.nextUrl.search
  const url = `${BACKEND_URL}${backendPath}${search}`

  const forwardHeaders = new Headers()
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (!HOP_BY_HOP.has(lower) && lower !== 'host') {
      forwardHeaders.set(key, value)
    }
  })
  if (API_KEY) forwardHeaders.set('x-api-key', API_KEY)

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
