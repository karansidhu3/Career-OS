'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { spring } from '@/lib/motion'
import { BrandMark } from './BrandMark'
import { UserMenu } from './UserMenu'

// Applications — a briefcase. Reads unambiguously as "jobs" at a glance,
// unlike a generic list glyph. Search now lives on the Applications page
// itself rather than behind a navbar icon.
function ApplicationsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  )
}

// Background — a resume/document glyph. Previously a folder, which read as a
// generic container rather than "the career content you maintain."
function BackgroundIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="16" y2="17" />
    </svg>
  )
}

function IconGroupDivider() {
  return <div className="w-px h-4 mx-1 shrink-0" style={{ background: 'var(--c-border)' }} />
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

        {/* Right icons — grouped by purpose: your job search (applications),
            then a divider, then you (background, account, avatar). */}
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

          <IconGroupDivider />

          {/* Background — career content that feeds every generation */}
          <Link
            href="/profile"
            title="Background"
            className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <BackgroundIcon />
          </Link>

          {/* Account — moved into UserMenu's "Settings" entry, avatar click */}
          <UserMenu />
        </div>
      </div>
    </motion.div>
  )
}
