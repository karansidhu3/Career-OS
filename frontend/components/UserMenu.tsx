'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { useClerk, useUser } from '@clerk/nextjs'
import { spring } from '@/lib/motion'

// Replaces Clerk's stock <UserButton /> dropdown + "Manage account" modal.
// That default UI kept surfacing dark-mode contrast bugs across its many
// internal sub-components, and its Security tab exposes a native "Delete
// account" button that bypasses our own grace-period deletion flow
// (components/AccountDeletion.tsx) entirely — deleting the Clerk identity
// directly without cleaning up app data first. This is a single-user tool;
// the only thing that needs to live behind the avatar is identity + sign out.
function SettingsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function SignOutIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}

export function UserMenu() {
  const { user, isLoaded } = useUser()
  const { signOut } = useClerk()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('mousedown', onClick)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onClick)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const initial = user?.firstName?.[0] ?? user?.primaryEmailAddress?.emailAddress?.[0]?.toUpperCase() ?? '?'

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        title="Account menu"
        className="w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-150"
        onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        {isLoaded && user?.imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.imageUrl}
            alt=""
            className="w-6 h-6 rounded-full object-cover"
            style={{ border: '1px solid var(--c-border)' }}
          />
        ) : (
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold text-neutral-700"
            style={{ background: 'var(--c-surface-raised)', border: '1px solid var(--c-border)' }}
          >
            {initial}
          </div>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -6 }}
            transition={spring.snappy}
            className="absolute right-0 top-[calc(100%+10px)] w-56 rounded-2xl overflow-hidden z-50"
            style={{
              background: 'var(--c-surface-overlay)',
              backdropFilter: 'blur(32px) saturate(1.40)',
              WebkitBackdropFilter: 'blur(32px) saturate(1.40)',
              border: '1px solid var(--c-border)',
              boxShadow: [
                'inset 0 1px 0 rgba(255,255,255,0.06)',
                '0 20px 56px rgba(0,0,0,0.35)',
                '0 4px 16px rgba(0,0,0,0.25)',
              ].join(', '),
            }}
          >
            <div className="px-3.5 py-3" style={{ borderBottom: '1px solid var(--c-border)' }}>
              <p className="text-sm font-medium text-neutral-800 truncate">
                {user?.fullName || 'Account'}
              </p>
              {user?.primaryEmailAddress && (
                <p className="text-xs text-neutral-600 truncate mt-0.5">
                  {user.primaryEmailAddress.emailAddress}
                </p>
              )}
            </div>

            <Link
              href="/account"
              onClick={() => setOpen(false)}
              className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-neutral-700 hover:text-neutral-900 transition-colors"
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <SettingsIcon />
              Settings
            </Link>

            <button
              onClick={() => { setOpen(false); signOut(() => router.push('/')) }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-neutral-700 hover:text-neutral-900 transition-colors"
              style={{ borderTop: '1px solid var(--c-border)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--c-icon-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <SignOutIcon />
              Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
