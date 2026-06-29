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

// Raw RGB channels for drop-shadow layers (can't use opacity on CSS vars)
function scoreGlowRgb(score: number): string {
  if (score >= 8) return '16, 185, 129'
  if (score >= 6) return '245, 158, 11'
  return '239, 68, 68'
}

function buildFilters(rgb: string) {
  return {
    arc: [
      `drop-shadow(0 0 2px rgba(${rgb},0.95))`,
      `drop-shadow(0 0 8px rgba(${rgb},0.55))`,
      `drop-shadow(0 0 22px rgba(${rgb},0.28))`,
    ].join(' '),
    number: [
      `drop-shadow(0 0 3px rgba(${rgb},1.00))`,
      `drop-shadow(0 0 12px rgba(${rgb},0.60))`,
      `drop-shadow(0 0 28px rgba(${rgb},0.25))`,
    ].join(' '),
    ambient: `radial-gradient(circle, rgba(${rgb},0.10) 0%, transparent 68%)`,
  }
}

// ─── Component ───────────────────────────────────────────────────
type ScoreRingProps = {
  score: number
  size?: RingSize
  /** Fires a sonar-ping celebration on mount when score ≥ 8 */
  celebrate?: boolean
}

export function ScoreRing({ score, size = 96, celebrate }: ScoreRingProps) {
  const { r, sw, fontSize, fontWeight } = CONFIG[size]
  const center = size / 2
  const circumference = 2 * Math.PI * r
  const tokens = scoreTokens(score)
  const filters = buildFilters(scoreGlowRgb(score))
  const displayScore = useCountUp(score, 700)
  const targetOffset = circumference * (1 - score / 10)

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0, background: filters.ambient, borderRadius: '50%' }}>
      {/* Celebration ping — one outward pulse for strong matches */}
      {celebrate && score >= 8 && (
        <motion.div
          initial={{ opacity: 0.55, scale: 1 }}
          animate={{ opacity: 0, scale: 1.55 }}
          transition={{ duration: 1.4, ease: 'easeOut', delay: 0.75 }}
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `2px solid var(--c-success)`,
            pointerEvents: 'none',
          }}
        />
      )}
      {/* SVG ring — rotated so arc starts at top */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)', display: 'block', overflow: 'visible' }}
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
          style={{ filter: filters.arc }}
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
          filter: filters.number,
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
