'use client'

import Link from 'next/link'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { HistoryDrawer } from './HistoryDrawer'

function HistoryIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

function ProfileIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-48px)] max-w-4xl"
      >
        <div
          style={{
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            background: 'rgba(250, 250, 248, 0.88)',
            border: '1px solid rgba(0,0,0,0.07)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04)',
          }}
          className="rounded-2xl px-4 py-2.5 flex items-center justify-between"
        >
          {/* Wordmark */}
          <Link href="/" className="flex items-center gap-2 group">
            <div
              style={{ background: 'linear-gradient(135deg, #818cf8, #6366f1)' }}
              className="w-6 h-6 rounded-md flex items-center justify-center"
            >
              <span className="text-white text-[10px] font-bold">C</span>
            </div>
            <span className="text-sm font-semibold text-neutral-800 tracking-tight">CareerOS</span>
          </Link>

          {/* Icon actions */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setDrawerOpen(true)}
              title="History"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-400 hover:text-neutral-700 hover:bg-black/[0.04] transition-all duration-150"
            >
              <HistoryIcon />
            </button>
            <Link
              href="/profile"
              title="Profile"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-neutral-400 hover:text-neutral-700 hover:bg-black/[0.04] transition-all duration-150"
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
