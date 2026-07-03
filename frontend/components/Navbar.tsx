'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { UserButton } from '@clerk/nextjs'
import { api } from '@/lib/api'
import { spring } from '@/lib/motion'
import { BrandMark } from './BrandMark'
import { CommandPalette } from './CommandPalette'

function ProfileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function ApplicationsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
    </svg>
  )
}

function AccountIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function Navbar() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [hasActive, setHasActive] = useState(false)

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

          {/* Right icons */}
          <div className="flex items-center gap-1">
            {/* Applications search — opens command palette */}
            <button
              onClick={() => setPaletteOpen(true)}
              title="Search applications (⌘K)"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <ApplicationsIcon />
            </button>

            {/* Background — career content that feeds every generation */}
            <Link
              href="/profile"
              title="Background"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <ProfileIcon />
            </Link>

            {/* Account — billing key, data export, deletion. Deliberately
                separate from Background: administrative, not content. */}
            <Link
              href="/account"
              title="Account"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-600 hover:text-neutral-700 transition-all duration-150"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <AccountIcon />
            </Link>

            <div className="w-8 h-8 flex items-center justify-center">
              <UserButton />
            </div>
          </div>
        </div>
      </motion.div>

      <CommandPalette
        open={paletteOpen}
        onOpen={() => setPaletteOpen(true)}
        onClose={() => setPaletteOpen(false)}
      />
    </>
  )
}
