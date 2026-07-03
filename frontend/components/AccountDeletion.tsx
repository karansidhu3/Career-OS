'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, AccountDeletionStatus } from '@/lib/api'
import { spring } from '@/lib/motion'
import { inputCls, inputStyle, CancelButton } from '@/components/FormControls'

// ---- Account deletion (Phase 6) ----
// A "danger zone" pattern — deliberately placed at the bottom of /profile,
// visually separated from everyday editing. Destructive and consequential
// (even with a 7-day grace period), so it gets real friction: a typed
// confirmation, not a single click.

export function AccountDeletion() {
  const [status, setStatus] = useState<AccountDeletionStatus | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getDeletionStatus().then(setStatus).catch(() => {})
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

  const scheduledDate = status?.scheduled_deletion_at
    ? new Date(status.scheduled_deletion_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : null

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: 'var(--c-danger)' }}>
        Danger zone
      </p>
      <p className="text-sm font-semibold text-neutral-800 mb-1">Delete account</p>

      {scheduledDate ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={spring.snappy}>
          <p className="text-xs text-neutral-500 mb-3 leading-relaxed">
            Your account and all data will be permanently deleted on <strong>{scheduledDate}</strong>.
          </p>
          {error && <p className="text-xs mb-3" style={{ color: 'var(--c-danger)' }}>{error}</p>}
          <button
            onClick={cancelDeletion}
            disabled={submitting}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
            style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
          >
            {submitting ? 'Cancelling…' : 'Cancel deletion'}
          </button>
        </motion.div>
      ) : (
        <>
          <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
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
                <label className="block text-xs text-neutral-500">
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
