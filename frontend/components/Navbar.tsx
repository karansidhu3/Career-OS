'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { HistoryDrawer } from './HistoryDrawer'

function ArchiveIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <line x1="9" y1="6" x2="20" y2="6" />
      <line x1="9" y1="12" x2="20" y2="12" />
      <line x1="9" y1="18" x2="20" y2="18" />
      <circle cx="4" cy="6" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="4" cy="12" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="4" cy="18" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  )
}

function ProfileIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [hasActive, setHasActive] = useState(false)

  // Fetch once on mount to light the dot if interview/offer jobs exist
  useEffect(() => {
    api.listJobs()
      .then(jobs => setHasActive(jobs.some(j => j.status === 'interview' || j.status === 'offer')))
      .catch(() => {})
  }, [])

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-48px)] max-w-4xl"
      >
        <div
          style={{
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            background: 'var(--c-navbar)',
            border: '1px solid var(--c-border)',
            boxShadow: 'var(--c-navbar-shadow)',
          }}
          className="rounded-2xl px-4 py-2.5 flex items-center justify-between"
        >
          {/* Mark + Wordmark */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div
              style={{
                width: 7,
                height: 7,
                borderRadius: 2,
                background: 'var(--c-accent)',
                flexShrink: 0,
                transition: 'opacity 0.15s',
              }}
            />
            <span className="text-[13.5px] font-semibold text-neutral-800 tracking-[-0.01em]">
              CareerOS
            </span>
          </Link>

          {/* Icon actions */}
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setDrawerOpen(true)}
              title="Log"
              className="relative w-8 h-8 flex items-center justify-center rounded-xl text-neutral-400 hover:text-neutral-600 transition-all duration-150"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <ArchiveIcon />
              {hasActive && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 420, damping: 14 }}
                  className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full pointer-events-none"
                  style={{ background: 'var(--c-warn)' }}
                />
              )}
            </button>
            <Link
              href="/profile"
              title="Profile"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-400 hover:text-neutral-600 transition-all duration-150"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <ProfileIcon />
            </Link>
          </div>
        </div>
      </motion.div>

      <HistoryDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  )
}
