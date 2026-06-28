'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { relativeDate } from '@/lib/utils'
import { spring } from '@/lib/motion'

type CommandPaletteProps = {
  open: boolean
  onOpen: () => void
  onClose: () => void
}

function scoreColor(score: number | null): string {
  if (score == null) return 'var(--c-border)'
  if (score >= 8) return 'var(--c-success)'
  if (score >= 6) return 'var(--c-warn)'
  return 'var(--c-danger)'
}

export function CommandPalette({ open, onOpen, onClose }: CommandPaletteProps) {
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Global Cmd+K
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (open) onClose()
        else onOpen()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onOpen, onClose])

  // Load + focus when opened
  useEffect(() => {
    if (!open) return
    setQuery('')
    setActiveIdx(0)
    api.listJobs().then(setJobs).catch(() => {})
    const t = setTimeout(() => inputRef.current?.focus(), 60)
    return () => clearTimeout(t)
  }, [open])

  // Escape to close
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const filtered = query.trim()
    ? jobs.filter(j => {
        const q = query.toLowerCase()
        return j.title?.toLowerCase().includes(q) || j.company?.toLowerCase().includes(q)
      })
    : jobs.slice(0, 8)

  // Arrow / Enter navigation
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx(i => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx(i => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && filtered[activeIdx]) {
        onClose()
        router.push(`/jobs/${filtered[activeIdx].id}`)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, filtered, activeIdx, onClose, router])

  // Reset active index on query change
  useEffect(() => { setActiveIdx(0) }, [query])

  const navigate = useCallback((jobId: number) => {
    onClose()
    router.push(`/jobs/${jobId}`)
  }, [onClose, router])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="palette-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="fixed inset-0 z-[70]"
            style={{ background: 'rgba(0,0,0,0.18)' }}
          />

          {/* Panel */}
          <motion.div
            key="palette-panel"
            initial={{ opacity: 0, scale: 0.97, y: -10, filter: 'blur(3px)' }}
            animate={{ opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, scale: 0.97, y: -10, filter: 'blur(3px)' }}
            transition={spring.snappy}
            className="fixed z-[71] left-1/2 -translate-x-1/2 w-[calc(100%-32px)]"
            style={{ top: '18vh', maxWidth: 680 }}
          >
            <div
              className="rounded-2xl overflow-hidden"
              style={{
                background: 'var(--c-surface-overlay)',
                backdropFilter: 'blur(32px) saturate(1.40) brightness(1.01)',
                WebkitBackdropFilter: 'blur(32px) saturate(1.40) brightness(1.01)',
                boxShadow: [
                  'inset 0 1px 0 rgba(255,255,255,0.75)',
                  '0 0 0 0.5px rgba(0,0,0,0.08)',
                  '0 4px 16px rgba(0,0,0,0.07)',
                  '0 20px 56px rgba(0,0,0,0.10)',
                  '0 40px 80px rgba(0,0,0,0.05)',
                ].join(', '),
              }}
            >
              {/* Search row */}
              <div
                className="flex items-center gap-3 px-4 py-3.5"
                style={{ borderBottom: '1px solid var(--c-border)' }}
              >
                <svg
                  width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  className="text-neutral-400 shrink-0"
                >
                  <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
                </svg>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search applications…"
                  className="flex-1 text-sm text-neutral-700 placeholder-neutral-400 bg-transparent focus:outline-none"
                />
                <kbd
                  className="text-[10px] font-sans px-1.5 py-0.5 rounded-md border text-neutral-400 shrink-0"
                  style={{ background: 'var(--c-kbd-bg)', borderColor: 'var(--c-kbd-border)' }}
                >
                  esc
                </kbd>
              </div>

              {/* Results */}
              <div className="py-1.5 max-h-64 overflow-y-auto">
                {filtered.length === 0 ? (
                  <p className="text-xs text-neutral-400 text-center py-8">
                    {query ? 'No results' : 'No applications yet'}
                  </p>
                ) : (
                  filtered.map((job, i) => {
                    const isSpecial = job.status === 'interview' || job.status === 'offer'
                    return (
                      <button
                        key={job.id}
                        onClick={() => navigate(job.id)}
                        onMouseEnter={() => setActiveIdx(i)}
                        className="w-full text-left flex items-center gap-3 px-3 py-2.5 mx-1.5 rounded-xl transition-none"
                        style={{
                          width: 'calc(100% - 12px)',
                          background: i === activeIdx ? 'var(--c-icon-hover)' : 'transparent',
                        }}
                      >
                        <div
                          className="shrink-0 w-1.5 h-1.5 rounded-full"
                          style={{ background: isSpecial ? 'var(--c-warn)' : 'transparent' }}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-700 truncate">
                            {job.title || 'Untitled'}
                          </p>
                          {job.company && (
                            <p className="text-xs text-neutral-400 truncate mt-0.5">{job.company}</p>
                          )}
                        </div>
                        <div className="shrink-0 text-right">
                          {job.fit_score != null && (
                            <p
                              className="text-xs font-mono font-semibold tabular-nums"
                              style={{ color: scoreColor(job.fit_score) }}
                            >
                              {job.fit_score}/10
                            </p>
                          )}
                          <p className="text-[11px] text-neutral-400 mt-0.5">
                            {job.created_at ? relativeDate(job.created_at) : ''}
                          </p>
                        </div>
                      </button>
                    )
                  })
                )}
              </div>

              {/* Footer */}
              <div
                className="flex items-center justify-between px-4 py-2.5"
                style={{ borderTop: '1px solid var(--c-border)' }}
              >
                <span className="text-[11px] text-neutral-400">↑↓ navigate · ↵ open</span>
                <button
                  onClick={() => { onClose(); router.push('/applications') }}
                  className="text-[11px] text-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  View all →
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
