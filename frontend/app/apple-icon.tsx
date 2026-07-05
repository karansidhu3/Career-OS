import { ImageResponse } from 'next/og'
import { ringIcon } from '@/lib/ringMark'

export const size = { width: 180, height: 180 }
export const contentType = 'image/png'

export default function AppleIcon() {
  return new ImageResponse(ringIcon(112, 4), { ...size })
}
