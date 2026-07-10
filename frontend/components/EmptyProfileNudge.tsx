'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { spring } from '@/lib/motion'

// One-time card shown only on the first idle-screen arrival right after a
// brand-new user finishes onboarding with no experience or projects saved.
// Dismissible, never reappears (no persistence — it's driven by a session
// transition flag in app/page.tsx, not a recurring check), never blocks
// Generate. See CLAUDE.md ADR-016.
export function EmptyProfileNudge({ onDismiss }: { onDismiss: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={spring.gentle}
      className="mt-6 rounded-xl px-4 py-3.5 flex items-start justify-between gap-4"
      style={{ background: 'var(--c-glass-bg)', border: '1px solid var(--c-border)' }}
    >
      <p className="text-xs text-neutral-600 leading-relaxed">
        Your profile is empty — CareerOS writes from what&apos;s there, so the first resume
        will be thin.{' '}
        <Link href="/profile" className="underline underline-offset-2 text-neutral-800 hover:text-neutral-900 transition-colors">
          Add a role or project
        </Link>
        {' '}whenever you&apos;re ready.
      </p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 text-neutral-600 hover:text-neutral-800 transition-colors"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </motion.div>
  )
}
