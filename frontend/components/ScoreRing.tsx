'use client'

import { motion } from 'framer-motion'
import { useCountUp } from '@/lib/hooks'

// ─── Per-size geometry ───────────────────────────────────────────
const CONFIG = {
  64:  { r: 25, sw: 5,   fontSize: 13, fontWeight: 700 },
  96:  { r: 38, sw: 5.5, fontSize: 20, fontWeight: 700 },
  120: { r: 48, sw: 6,   fontSize: 24, fontWeight: 700 },
} as const

type RingSize = keyof typeof CONFIG

// ─── Semantic color tokens ────────────────────────────────────────
function scoreTokens(score: number) {
  if (score >= 8) return {
    accent: 'var(--c-success)',
    ring:   'var(--c-success-border)',
  }
  if (score >= 6) return {
    accent: 'var(--c-warn)',
    ring:   'var(--c-warn-border)',
  }
  return {
    accent: 'var(--c-danger)',
    ring:   'var(--c-danger-border)',
  }
}

// ─── Component ───────────────────────────────────────────────────
type ScoreRingProps = {
  score: number
  size?: RingSize
}

export function ScoreRing({ score, size = 96 }: ScoreRingProps) {
  const { r, sw, fontSize, fontWeight } = CONFIG[size]
  const center = size / 2
  const circumference = 2 * Math.PI * r
  const tokens = scoreTokens(score)
  const displayScore = useCountUp(score, 700)
  const targetOffset = circumference * (1 - score / 10)

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      {/* SVG ring — rotated so arc starts at top */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)', display: 'block' }}
      >
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={tokens.ring}
          strokeWidth={sw}
        />
        {/* Animated fill */}
        <motion.circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={tokens.accent}
          strokeWidth={sw}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: targetOffset }}
          transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
        />
      </svg>

      {/* Centered score number */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            fontSize,
            fontWeight,
            color: tokens.accent,
            lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {displayScore}
        </span>
      </div>
    </div>
  )
}
