import { ImageResponse } from 'next/og'
import { ringIcon } from '@/lib/ringMark'

export const size = { width: 32, height: 32 }
export const contentType = 'image/png'

export default function Icon() {
  // No glow at this size — at 32px a blurred halo just reads as mud, not light.
  return new ImageResponse(ringIcon(20, 1.2, false), { ...size })
}
