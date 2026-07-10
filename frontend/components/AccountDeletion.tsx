'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useClerk } from '@clerk/nextjs'
import { motion, AnimatePresence } from 'framer-motion'
import { api, AccountDeletionStatus } from '@/lib/api'
import { spring } from '@/lib/motion'
import { inputCls, inputStyle, CancelButton } from '@/components/FormControls'
import { SectionLabel } from '@/components/SectionLabel'

// ---- Account deletion (Phase 6) ----
// A "danger zone" pattern — deliberately placed at the bottom of /profile,
// visually separated from everyday editing. Destructive and consequential
// (even with a 7-day grace period), so it gets real friction: a typed
// confirmation, not a single click. Once the grace period has started,
// "Delete now" offers an accelerated path for anyone certain they don't
// need it — gated behind its own typed confirmation, since it's strictly
// more consequential than the request that started the grace period (no
// more 7-day undo window once it runs).

export function AccountDeletion() {
  const router = useRouter()
  const { signOut } = useClerk()
  const [status, setStatus] = useState<AccountDeletionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [confirmingNow, setConfirmingNow] = useState(false)
  const [confirmNowText, setConfirmNowText] = useState('')
  const [deletingNow, setDeletingNow] = useState(false)

  useEffect(() => {
    api.getDeletionStatus().then(setStatus).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const requestDeletion = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const updated = await api.requestDeletion()
      setStatus(updated)
      setConfirming(false)
      setConfirmText('')
    } catch {
      setError('Could not schedule deletion. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const cancelDeletion = async () => {
    setSubmitting(true)
    setError(null)
    try {
      setStatus(await api.cancelDeletion())
    } catch {
      setError('Could not cancel deletion. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const deleteNow = async () => {
    setDeletingNow(true)
    setError(null)
    try {
      await api.deleteNow()
      // Account is gone server-side — clear the local session and leave.
      // No confirmation screen to land on; there's nothing left to show it on.
      await signOut(() => router.push('/'))
    } catch {
      setError('Could not delete the account. Try again.')
      setDeletingNow(false)
    }
  }

  const scheduledDate = status?.scheduled_deletion_at
    ? new Date(status.scheduled_deletion_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : null

  return (
    <div>
      <SectionLabel className="mb-1" style={{ color: 'var(--c-danger)' }}>Danger zone</SectionLabel>
      <p className="text-sm font-semibold text-neutral-800 mb-1">Delete account</p>

      {loading ? (
        <div aria-hidden>
          <div className="h-3 w-full rounded skeleton-shimmer mb-1.5" />
          <div className="h-3 w-2/3 rounded skeleton-shimmer mb-4" />
          <div className="h-7 w-32 rounded-xl skeleton-shimmer" />
        </div>
      ) : scheduledDate ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={spring.snappy}>
          <p className="text-xs text-neutral-600 mb-3 leading-relaxed">
            Your account and all data will be permanently deleted on <strong>{scheduledDate}</strong>.
          </p>
          {error && <p className="text-xs mb-3" style={{ color: 'var(--c-danger)' }}>{error}</p>}

          <AnimatePresence mode="wait" initial={false}>
            {!confirmingNow ? (
              <motion.div
                key="actions"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.snappy}
                className="flex items-center gap-3"
              >
                <button
                  onClick={cancelDeletion}
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
                  style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
                >
                  {submitting ? 'Cancelling…' : 'Cancel deletion'}
                </button>
                <button
                  onClick={() => setConfirmingNow(true)}
                  className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
                >
                  Delete now instead
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="confirm-now"
                initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.snappy}
                className="space-y-3"
              >
                <p className="text-xs leading-relaxed" style={{ color: 'var(--c-danger)' }}>
                  This skips the rest of the grace period. Once it runs, there is no undo.
                </p>
                <label className="block text-xs text-neutral-600">
                  Type <span className="font-mono font-semibold text-neutral-700">DELETE</span> to delete immediately
                </label>
                <input
                  type="text"
                  value={confirmNowText}
                  onChange={e => setConfirmNowText(e.target.value)}
                  className={inputCls}
                  style={inputStyle}
                  autoComplete="off"
                />
                <div className="flex items-center justify-end gap-2">
                  <CancelButton onClick={() => { setConfirmingNow(false); setConfirmNowText('') }} />
                  <button
                    onClick={deleteNow}
                    disabled={confirmNowText !== 'DELETE' || deletingNow}
                    className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
                    style={{ background: 'var(--c-danger)' }}
                  >
                    {deletingNow ? 'Deleting…' : 'Delete immediately'}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ) : (
        <>
          <p className="text-xs text-neutral-600 mb-4 leading-relaxed">
            Permanently deletes your profile, every generated resume and cover letter, and your
            application history, after a 7-day grace period. You can cancel any time before then.
          </p>
          {error && <p className="text-xs mb-3" style={{ color: 'var(--c-danger)' }}>{error}</p>}

          <AnimatePresence mode="wait" initial={false}>
            {!confirming ? (
              <motion.button
                key="start"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.snappy}
                onClick={() => setConfirming(true)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold transition-all"
                style={{ color: 'var(--c-danger)', border: '1px solid var(--c-danger)' }}
              >
                Delete my account
              </motion.button>
            ) : (
              <motion.div
                key="confirm"
                initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.snappy}
                className="space-y-3"
              >
                <label className="block text-xs text-neutral-600">
                  Type <span className="font-mono font-semibold text-neutral-700">DELETE</span> to confirm
                </label>
                <input
                  type="text"
                  value={confirmText}
                  onChange={e => setConfirmText(e.target.value)}
                  className={inputCls}
                  style={inputStyle}
                  autoComplete="off"
                />
                <div className="flex items-center justify-end gap-2">
                  <CancelButton onClick={() => { setConfirming(false); setConfirmText(''); setError(null) }} />
                  <button
                    onClick={requestDeletion}
                    disabled={confirmText !== 'DELETE' || submitting}
                    className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
                    style={{ background: 'var(--c-danger)' }}
                  >
                    {submitting ? 'Scheduling…' : 'Delete my account'}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  )
}
