import { ImageResponse } from 'next/og'
import { ringIcon } from '@/lib/ringMark'

export const size = { width: 32, height: 32 }
export const contentType = 'image/png'

export default function Icon() {
  return new ImageResponse(ringIcon(20, 2), { ...size })
}
