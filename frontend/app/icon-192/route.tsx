import { ImageResponse } from 'next/og'
import { ringIcon } from '@/lib/ringMark'

// Plain route (not Next's icon.tsx convention) so the URL is fixed and can be
// referenced directly from manifest.ts's icons array.
export async function GET() {
  return new ImageResponse(ringIcon(120, 4), { width: 192, height: 192 })
}
