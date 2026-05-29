'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { relativeDate } from '@/lib/utils'
import { SectionLabel } from '@/components/SectionLabel'

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

type JobRow = {
  job: Job
  pinned: boolean
}

function groupJobs(jobs: Job[]): { pinned: JobRow[]; recent: JobRow[]; older: JobRow[] } {
  const now = Date.now()
  const sevenDays = 7 * 24 * 60 * 60 * 1000

  const pinned: JobRow[] = []
  const recent: JobRow[] = []
  const older: JobRow[] = []

  for (const job of jobs) {
    if (job.status === 'interview' || job.status === 'offer') {
      pinned.push({ job, pinned: true })
      continue
    }
    const age = job.created_at ? now - new Date(job.created_at).getTime() : Infinity
    if (age < sevenDays) {
      recent.push({ job, pinned: false })
    } else {
      older.push({ job, pinned: false })
    }
  }

  return { pinned, recent, older }
}

function HistoryRow({ job, onClick }: { job: Job; onClick: () => void }) {
  const isSpecial = job.status === 'interview' || job.status === 'offer'
  const scoreColor =
    job.fit_score == null ? '#d1d5db'
    : job.fit_score >= 8 ? '#059669'
    : job.fit_score >= 6 ? '#d97706'
    : '#dc2626'

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 transition-colors hover:bg-black/[0.045] group"
    >
      {/* Special marker */}
      <div className="shrink-0 w-1.5 h-1.5 rounded-full" style={{
        background: isSpecial ? '#f59e0b' : 'transparent',
      }} />

      {/* Title + company */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-neutral-700 truncate font-medium group-hover:text-neutral-900 transition-colors">
          {job.title || 'Untitled'}
        </p>
        {job.company && (
          <p className="text-xs text-neutral-400 truncate mt-0.5">{job.company}</p>
        )}
      </div>

      {/* Score + date */}
      <div className="shrink-0 text-right">
        {job.fit_score != null && (
          <p className="text-xs font-semibold" style={{ color: scoreColor }}>
            {job.fit_score}/10
          </p>
        )}
        <p className="text-xs text-neutral-300 mt-0.5">
          {job.created_at ? relativeDate(job.created_at) : ''}
        </p>
      </div>
    </button>
  )
}

type HistoryDrawerProps = {
  open: boolean
  onClose: () => void
}

export function HistoryDrawer({ open, onClose }: HistoryDrawerProps) {
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [showOlder, setShowOlder] = useState(false)

  const load = useCallback(async () => {
    try {
      setJobs(await api.listJobs())
    } catch { /* offline */ }
  }, [])

  useEffect(() => {
    if (open) {
      load()
      setShowOlder(false)
    }
  }, [open, load])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const navigate = (id: number) => {
    onClose()
    router.push(`/jobs/${id}`)
  }

  const { pinned, recent, older } = groupJobs(jobs)
  const hasAny = pinned.length + recent.length + older.length > 0

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 z-[60]"
            style={{ background: 'rgba(0,0,0,0.08)' }}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
            className="fixed top-0 right-0 h-full z-[61] flex flex-col"
            style={{
              width: 320,
              background: 'var(--c-surface-raised)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              borderLeft: '1px solid var(--c-border)',
              boxShadow: '-8px 0 40px rgba(0,0,0,0.12)',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 pt-5 pb-4" style={{ borderBottom: '1px solid var(--c-border)' }}>
              <span className="text-sm font-semibold text-neutral-800">History</span>
              <button
                onClick={onClose}
                className="text-neutral-400 hover:text-neutral-700 transition-colors p-1 rounded-lg hover:bg-black/[0.04]"
              >
                <CloseIcon />
              </button>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto px-2 py-3">
              {!hasAny && (
                <p className="text-xs text-neutral-300 text-center py-12">
                  No applications yet.
                </p>
              )}

              {/* Pinned — interview & offer */}
              {pinned.length > 0 && (
                <div className="mb-3">
                  <SectionLabel className="px-4 mb-1" style={{ color: 'var(--c-warn)' }}>
                    Interview / Offer
                  </SectionLabel>
                  {pinned.map(({ job }) => (
                    <HistoryRow key={job.id} job={job} onClick={() => navigate(job.id)} />
                  ))}
                </div>
              )}

              {/* Recent */}
              {recent.length > 0 && (
                <div className="mb-3">
                  {(pinned.length > 0 || older.length > 0) && (
                    <SectionLabel className="px-4 mb-1">Recent</SectionLabel>
                  )}
                  {recent.map(({ job }) => (
                    <HistoryRow key={job.id} job={job} onClick={() => navigate(job.id)} />
                  ))}
                </div>
              )}

              {/* Older — collapsed by default */}
              {older.length > 0 && (
                <div>
                  <button
                    onClick={() => setShowOlder(v => !v)}
                    className="text-xs text-neutral-300 hover:text-neutral-500 px-4 py-1.5 transition-colors"
                  >
                    {showOlder ? '↑ Hide older' : `↓ ${older.length} older`}
                  </button>
                  <AnimatePresence>
                    {showOlder && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        {older.map(({ job }) => (
                          <HistoryRow key={job.id} job={job} onClick={() => navigate(job.id)} />
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </div>

            {/* Footer */}
            {hasAny && (
              <div className="px-5 py-4" style={{ borderTop: '1px solid var(--c-border)' }}>
                <button
                  onClick={() => { onClose(); router.push('/applications') }}
                  className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  View all →
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
