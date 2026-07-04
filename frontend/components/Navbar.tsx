'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { spring } from '@/lib/motion'
import { BrandMark } from './BrandMark'
import { UserMenu } from './UserMenu'

// Applications — stacked layers. Reads as "a pile of submitted things,"
// which fits a history/archive better than a single flat glyph would.
function ApplicationsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2 2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  )
}

// Resume — a closed book, spine-view. Distinct silhouette from the layers
// icon now used for Applications, and reads as "your compiled content"
// rather than a single flat document (which risked looking like generated
// output — the actual product of this app — rather than its source material).
function ResumeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

export function Navbar() {
  const [hasActive, setHasActive] = useState(false)

  useEffect(() => {
    api.listJobs()
      .then(jobs => setHasActive(jobs.some(j => j.status === 'interview' || j.status === 'offer')))
      .catch(() => {})
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring.standard}
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-48px)] max-w-4xl"
    >
      <div
        style={{
          backdropFilter: 'blur(28px) saturate(1.35)',
          WebkitBackdropFilter: 'blur(28px) saturate(1.35)',
          background: 'var(--c-navbar)',
          boxShadow: 'var(--c-navbar-shadow)',
        }}
        className="rounded-2xl px-4 py-2.5 flex items-center justify-between"
      >
        {/* Wordmark — home link */}
        <Link
          href="/"
          className="flex items-center gap-[7px] group"
          title="Home"
        >
          <span
            className="text-neutral-800 transition-opacity duration-150"
            style={{ opacity: 0.88 }}
          >
            <BrandMark size={12} physicalStroke={1.8} />
          </span>
          <span className="text-[13px] font-medium text-neutral-800 tracking-[0.02em]">
            CareerOS
          </span>
          {/* Amber dot — interview/offer signal, lives next to wordmark */}
          {hasActive && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={spring.bouncy}
              className="w-1.5 h-1.5 rounded-full pointer-events-none"
              style={{ background: 'var(--c-warn)' }}
            />
          )}
        </Link>

        {/* Right icons — applications, resume, then you (avatar). */}
        <div className="flex items-center gap-1">
          {/* Applications — browse/filter/search the full history */}
          <Link
            href="/applications"
            title="Applications"
            className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <ApplicationsIcon />
          </Link>

          {/* Resume — career content that feeds every generation */}
          <Link
            href="/profile"
            title="Resume"
            className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <ResumeIcon />
          </Link>

          {/* Account — moved into UserMenu's "Settings" entry, avatar click */}
          <UserMenu />
        </div>
      </div>
    </motion.div>
  )
}
