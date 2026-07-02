'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, AccountSession } from '@/lib/api'

// ---- Session management (Phase 6) ----
// Lists Clerk sessions for this account; lets the user revoke any one of them,
// or sign out everywhere else in one action. Standard security hygiene serious
// users expect — not part of the core loop, lives on /profile.

function formatLastActive(iso: string | null): string {
  if (!iso) return 'Unknown'
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return 'Active now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return new Date(iso).toLocaleDateString()
}

function SessionRow({ session, onRevoke }: { session: AccountSession; onRevoke: (id: string) => void }) {
  const [revoking, setRevoking] = useState(false)
  const [confirmRevoke, setConfirmRevoke] = useState(false)

  const revoke = async () => {
    setRevoking(true)
    try {
      await api.revokeSession(session.id)
      onRevoke(session.id)
    } finally {
      setRevoking(false)
    }
  }

  const location = [session.city, session.country].filter(Boolean).join(', ')

  return (
    <div className="flex items-center justify-between py-3" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
      <div>
        <div className="flex items-center gap-2">
          <p className="text-sm text-neutral-700">{session.browser ?? 'Unknown browser'} · {session.device_type ?? 'device'}</p>
          {session.is_current && (
            <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded" style={{ background: 'var(--c-success-bg, rgba(34,197,94,0.12))', color: 'var(--c-success)' }}>
              This device
            </span>
          )}
        </div>
        <p className="text-xs text-neutral-400 mt-0.5">
          {formatLastActive(session.last_active_at)}{location ? ` · ${location}` : ''}
        </p>
      </div>
      {!session.is_current && (
        <AnimatePresence mode="wait" initial={false}>
          {!confirmRevoke ? (
            <motion.button
              key="revoke"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              onClick={() => setConfirmRevoke(true)}
              className="text-xs text-neutral-400 hover:text-red-400 transition-colors"
            >
              Revoke
            </motion.button>
          ) : (
            <motion.div
              key="confirm"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              className="flex items-center gap-3"
            >
              <button onClick={revoke} disabled={revoking} className="text-xs text-red-400 hover:text-red-600 transition-colors disabled:opacity-50">
                {revoking ? 'Revoking…' : 'Confirm'}
              </button>
              <button onClick={() => setConfirmRevoke(false)} className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors">
                Cancel
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  )
}

export function SessionManagement() {
  const [sessions, setSessions] = useState<AccountSession[] | null>(null)
  const [revokingOthers, setRevokingOthers] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
    } catch {
      setError('Could not load sessions.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleRevoke = (id: string) => {
    setSessions(prev => prev ? prev.filter(s => s.id !== id) : prev)
  }

  const revokeOthers = async () => {
    setRevokingOthers(true)
    try {
      await api.revokeOtherSessions()
      setSessions(prev => prev ? prev.filter(s => s.is_current) : prev)
    } catch {
      setError('Could not sign out other sessions.')
    } finally {
      setRevokingOthers(false)
    }
  }

  const otherCount = sessions?.filter(s => !s.is_current).length ?? 0

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-semibold text-neutral-800">Active sessions</p>
        {otherCount > 0 && (
          <button
            onClick={revokeOthers}
            disabled={revokingOthers}
            className="text-xs text-neutral-400 hover:text-red-400 transition-colors disabled:opacity-50"
          >
            {revokingOthers ? 'Signing out…' : 'Sign out everywhere else'}
          </button>
        )}
      </div>
      <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
        Devices currently signed in to your account.
      </p>

      {error && <p className="text-xs mb-3" style={{ color: 'var(--c-danger)' }}>{error}</p>}

      {sessions === null ? (
        <p className="text-xs text-neutral-400">Loading…</p>
      ) : sessions.length === 0 ? (
        <p className="text-xs text-neutral-400">No active sessions found.</p>
      ) : (
        <div>
          {sessions.map(s => (
            <SessionRow key={s.id} session={s} onRevoke={handleRevoke} />
          ))}
        </div>
      )}
    </div>
  )
}
