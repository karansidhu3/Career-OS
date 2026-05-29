'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { api, CandidacyInsights, Job } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'
import { AutoTextarea } from '@/components/AutoTextarea'
import { BrandMark } from '@/components/BrandMark'
import { spring } from '@/lib/motion'
import { relativeDate } from '@/lib/utils'

// ─── Types ──────────────────────────────────────────────────────────────────

type AppState =
  | { mode: 'idle' }
  | { mode: 'generating'; jobId: number }
  | { mode: 'result'; job: Job }
  | { mode: 'error'; jobId?: number; message: string }

// ─── Helpers ────────────────────────────────────────────────────────────────

function getGenMessage(elapsed: number): string {
  if (elapsed < 5)  return 'Reading the job description…'
  if (elapsed < 12) return 'Scoring fit…'
  if (elapsed < 22) return 'Writing your resume…'
  return 'Polishing the cover letter…'
}

// ─── Sub-components ──────────────────────────────────────────────────────────


function CoverLetterSection({ job }: { job: Job }) {
  const paragraphs = (job.cover_letter ?? '')
    .split(/\n\n+/)
    .map(p => p.trim())
    .filter(Boolean)

  return (
    <div>
      {paragraphs.map((para, i) => (
        <p key={i} className="text-[15px] text-neutral-700 leading-[1.8] mb-5 last:mb-0">
          {para}
        </p>
      ))}
    </div>
  )
}

function LatexSection({ latex }: { latex: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div>
      <div className="flex items-center justify-between">
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
        >
          {expanded ? 'Hide LaTeX source ↑' : 'LaTeX source ↓'}
        </button>
        <CopyButton text={latex} label="Copy .tex" />
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 max-h-[400px] overflow-y-auto rounded-xl p-4" style={{ background: 'var(--c-surface)' }}>
              <pre className="text-xs font-mono text-neutral-500 leading-relaxed whitespace-pre-wrap break-all">
                {latex}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function JdSection({ description }: { description: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div>
      <button
        onClick={() => setExpanded(v => !v)}
        className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
      >
        {expanded ? 'Hide job description ↑' : 'Original job description ↓'}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 max-h-[400px] overflow-y-auto rounded-xl p-4" style={{ background: 'var(--c-surface)' }}>
              <pre className="text-xs text-neutral-500 leading-relaxed whitespace-pre-wrap">
                {description}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function InterviewFlag({ job, onUpdate }: { job: Job; onUpdate: (j: Job) => void }) {
  const [flagging, setFlagging] = useState(false)
  const isSpecial = job.status === 'interview' || job.status === 'offer'

  if (isSpecial) {
    return (
      <span className="text-xs font-medium" style={{ color: '#f59e0b' }}>
        ✦ {job.status === 'offer' ? 'Offer received' : 'Interview stage'}
      </span>
    )
  }

  return (
    <button
      onClick={async () => {
        setFlagging(true)
        try {
          const updated = await api.updateStatus(job.id, 'interview')
          onUpdate(updated)
        } finally {
          setFlagging(false)
        }
      }}
      disabled={flagging}
      className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors"
    >
      {flagging ? 'Saving…' : '✦ Flag as interview'}
    </button>
  )
}

// ─── Divider ─────────────────────────────────────────────────────────────────

function Divider() {
  return <div className="my-8" style={{ borderTop: '1px solid var(--c-border)' }} />
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Home() {
  const [appState, setAppState] = useState<AppState>({ mode: 'idle' })
  const [jd, setJd] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [genElapsed, setGenElapsed] = useState(0)
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  const [insights, setInsights] = useState<CandidacyInsights | null>(() => {
    // Populate from cache synchronously so layout is stable on first render
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('careeros-insights-v1')
      if (raw) {
        const { data, ts } = JSON.parse(raw) as { data: CandidacyInsights; ts: number }
        if (Date.now() - ts < 60 * 60 * 1000) return data
      }
    } catch {}
    return null
  })

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // ── Restore JD from sessionStorage on mount ──
  useEffect(() => {
    const saved = sessionStorage.getItem('careeros-jd')
    if (saved) setJd(saved)
    textareaRef.current?.focus()
  }, [])

  const handleJdChange = (value: string) => {
    setJd(value)
    sessionStorage.setItem('careeros-jd', value)
  }

  // ── Load recent jobs for the idle list ──
  const loadRecent = useCallback(async () => {
    try {
      const jobs = await api.listJobs()
      setRecentJobs(jobs.slice(0, 4))
    } catch { /* offline */ }
  }, [])

  // ── Load candidacy insights — with localStorage cache ──
  const loadInsights = useCallback(async (force = false) => {
    const CACHE_KEY = 'careeros-insights-v1'
    const CACHE_TTL = 60 * 60 * 1000 // 1 hour

    if (!force) {
      try {
        const raw = localStorage.getItem(CACHE_KEY)
        if (raw) {
          const { data, ts } = JSON.parse(raw) as { data: CandidacyInsights; ts: number }
          if (Date.now() - ts < CACHE_TTL) {
            setInsights(data)
            return
          }
        }
      } catch { /* corrupt cache — fall through to fetch */ }
    }

    try {
      const data = await api.getInsights()
      setInsights(data)
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }))
      } catch { /* storage full — not critical */ }
    } catch { /* offline or no data */ }
  }, [])

  useEffect(() => { loadRecent() }, [loadRecent])
  useEffect(() => { loadInsights() }, [loadInsights])

  // ── Elapsed timer while generating ──
  useEffect(() => {
    if (appState.mode !== 'generating') {
      setGenElapsed(0)
      return
    }
    setGenElapsed(0)
    const t = setInterval(() => setGenElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [appState.mode])

  // ── Poll while generating ──
  const pollingJobId = appState.mode === 'generating' ? appState.jobId : null
  useEffect(() => {
    if (!pollingJobId) return
    const poll = setInterval(async () => {
      try {
        const job = await api.getJob(pollingJobId)
        if (job.status === 'generated') {
          setAppState({ mode: 'result', job })
          loadRecent()
          loadInsights(true) // force-refresh after new generation
        } else if (job.status === 'failed') {
          setAppState({
            mode: 'error',
            jobId: pollingJobId,
            message: 'Generation failed. Claude didn\'t respond in time.',
          })
        }
      } catch { /* keep polling on network error */ }
    }, 2500)
    return () => clearInterval(poll)
  }, [pollingJobId, loadRecent])

  // ── Generate ──
  const handleGenerate = async () => {
    if (!jd.trim() || submitting) return
    setSubmitting(true)
    try {
      const job = await api.generate({ description: jd.trim() })
      sessionStorage.removeItem('careeros-jd')
      setAppState({ mode: 'generating', jobId: job.id })
    } catch (e) {
      setAppState({
        mode: 'error',
        message: e instanceof Error ? e.message : 'Failed to start generation.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  // ── Retry ──
  const handleRetry = async (jobId: number) => {
    setSubmitting(true)
    try {
      await api.regenerate(jobId)
      setAppState({ mode: 'generating', jobId })
    } catch (e) {
      setAppState({
        mode: 'error',
        jobId,
        message: e instanceof Error ? e.message : 'Retry failed.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  // ── Reset to idle ──
  const resetToIdle = () => {
    setJd('')
    sessionStorage.removeItem('careeros-jd')
    setAppState({ mode: 'idle' })
    // Re-focus textarea after state settles
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey
      // Cmd+Enter → generate (idle only)
      if (meta && e.key === 'Enter' && appState.mode === 'idle' && !submitting) {
        handleGenerate()
      }
      // Cmd+N → new application (result only)
      if (meta && e.key === 'n' && appState.mode === 'result') {
        e.preventDefault()
        resetToIdle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appState.mode, submitting, jd])

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto px-6 pb-24">
      <AnimatePresence mode="wait">

        {/* ── IDLE STATE ── */}
        {appState.mode === 'idle' && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={spring.gentle}
          >
            <div className="pt-10">

              {/* ── Brand mark — visual anchor / signature element ── */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ ...spring.gentle, delay: 0.05 }}
                className="flex justify-center mb-7"
              >
                <span className="text-neutral-600" style={{ opacity: 0.22 }}>
                  <BrandMark size={56} physicalStroke={1.5} />
                </span>
              </motion.div>

              {/* ── Workspace zone — glass focal point ── */}
              <div
                className="rounded-2xl relative cursor-text"
                onClick={() => textareaRef.current?.focus()}
                style={{
                  background: 'var(--c-glass-bg)',
                  border: '1px solid var(--c-glass-border)',
                  boxShadow: 'var(--c-glass-shadow)',
                }}
              >
                {/* Writing surface */}
                <div
                  className="px-8 pt-7 pb-16"
                  style={{ minHeight: '40vh' }}
                >
                  <AutoTextarea
                    ref={textareaRef}
                    value={jd}
                    onChange={e => handleJdChange(e.target.value)}
                    placeholder="Paste a job description…"
                    disabled={submitting}
                    className="jd-textarea w-full text-[15px] text-neutral-800 placeholder-neutral-500 focus:outline-none leading-relaxed disabled:opacity-40"
                    style={{ background: 'transparent', border: 'none', padding: '0' }}
                  />
                </div>

                {/* Generate affordance — anchored bottom-right inside the zone */}
                <div className="absolute bottom-5 right-7">
                  <motion.button
                    onClick={handleGenerate}
                    disabled={submitting || !jd.trim()}
                    whileTap={{ scale: 0.97 }}
                    className="flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 disabled:opacity-30 transition-colors"
                  >
                    {submitting ? (
                      <>
                        <span className="w-3.5 h-3.5 rounded-full animate-spin" style={{ border: '1.5px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
                        <span>Starting…</span>
                      </>
                    ) : (
                      <>
                        <span>Generate</span>
                        <kbd
                          className="text-[10px] font-sans px-1.5 py-0.5 rounded-md border"
                          style={{
                            background: 'var(--c-kbd-bg)',
                            borderColor: 'var(--c-kbd-border)',
                            color: 'var(--c-kbd-text)',
                          }}
                        >
                          ⌘↵
                        </kbd>
                      </>
                    )}
                  </motion.button>
                </div>
              </div>

              {/* ── Candidacy signal — headline first ── */}
              <AnimatePresence>
                {insights && insights.count > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.38, ease: [0.25, 0, 0, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="mt-10">
                      {(() => {
                        const headline = insights.count < 3
                          ? `${insights.count} application${insights.count === 1 ? '' : 's'}`
                          : (insights.headline ?? `${insights.count} applications`)
                        const detail = insights.count < 3
                          ? `Apply to ${3 - insights.count} more for a candidacy read.`
                          : insights.observation
                        return (
                          <>
                            <p className="text-3xl font-semibold text-neutral-800 tracking-tight leading-tight mb-3">
                              {headline}
                            </p>
                            {detail && (
                              <p className="text-sm text-neutral-600 leading-relaxed max-w-lg">
                                {detail}
                              </p>
                            )}
                          </>
                        )
                      })()}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Recent jobs ── */}
              {recentJobs.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.3 }}
                  className="mt-10 pt-5"
                  style={{ borderTop: '1px solid var(--c-border)' }}
                >
                  {recentJobs.map(job => (
                    <Link
                      key={job.id}
                      href={`/jobs/${job.id}`}
                      className="flex items-center justify-between py-2.5 group"
                    >
                      <span className="text-sm text-neutral-600 group-hover:text-neutral-800 transition-colors truncate mr-6">
                        {job.title || 'Untitled'}
                        {job.company ? ` — ${job.company}` : ''}
                        {(job.status === 'interview' || job.status === 'offer') && (
                          <span className="ml-2 text-amber-400/80 text-xs">✦</span>
                        )}
                      </span>
                      <span className="shrink-0 text-xs text-neutral-600 group-hover:text-neutral-700 transition-colors tabular-nums">
                        {job.created_at ? relativeDate(job.created_at) : ''}
                      </span>
                    </Link>
                  ))}
                </motion.div>
              )}
            </div>
          </motion.div>
        )}

        {/* ── GENERATING STATE ── */}
        {appState.mode === 'generating' && (
          <motion.div
            key="generating"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.gentle}
          >
            <div
              className="flex flex-col items-center justify-center gap-6"
              style={{ minHeight: 'calc(100vh - 180px)' }}
            >
              {/* Spinner with ambient atmosphere */}
              <div className="relative flex items-center justify-center">
                <div
                  className="absolute rounded-full"
                  style={{
                    width: 80,
                    height: 80,
                    background: 'radial-gradient(circle, var(--c-accent-dim) 0%, transparent 70%)',
                    filter: 'blur(16px)',
                    opacity: 0.7,
                  }}
                />
                <div className="relative w-12 h-12">
                  <div className="absolute inset-0 rounded-full" style={{ border: '2.5px solid var(--c-accent-dim)' }} />
                  <div className="absolute inset-0 rounded-full animate-spin" style={{ border: '2.5px solid var(--c-accent)', borderTopColor: 'transparent' }} />
                </div>
              </div>

              {/* Cycling message */}
              <div className="text-center">
                <AnimatePresence mode="wait">
                  <motion.p
                    key={getGenMessage(genElapsed)}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    transition={spring.snappy}
                    className="text-[15px] text-neutral-600 font-medium"
                  >
                    {getGenMessage(genElapsed)}
                  </motion.p>
                </AnimatePresence>
                <p className="text-xs text-neutral-500 mt-2 tabular-nums">{genElapsed}s</p>
              </div>

              {/* Abandon */}
              <button
                onClick={() => setAppState({ mode: 'idle' })}
                className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}

        {/* ── RESULT STATE ── */}
        {appState.mode === 'result' && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.standard}
          >
            {/* Header */}
            <div className="pt-8 mb-8">
              <button
                onClick={resetToIdle}
                className="text-sm text-neutral-500 hover:text-neutral-800 transition-colors flex items-center gap-1.5"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                New application
                <span className="text-xs text-neutral-500 font-normal ml-1">⌘N</span>
              </button>
            </div>

            {/* Title + company */}
            <div className="flex items-baseline gap-3 flex-wrap mb-1">
              <h1 className="text-[2rem] font-semibold text-neutral-900 leading-tight tracking-tight">
                {appState.job.title}
              </h1>
              {appState.job.fit_score != null && (
                <span className="text-xs text-neutral-500 tabular-nums">
                  {appState.job.fit_score}/10
                </span>
              )}
            </div>
            {appState.job.company && (
              <p className="text-[15px] text-neutral-600 mb-0">{appState.job.company}</p>
            )}

            {/* Strategic note — the centerpiece */}
            {appState.job.strategic_note && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...spring.gentle, delay: 0.1 }}
                className="mt-8"
              >
                <p className="text-[10px] uppercase tracking-[0.12em] text-neutral-500 mb-3">
                  what this reveals
                </p>
                <p className="text-[17px] text-neutral-700 leading-[1.8] max-w-2xl">
                  {appState.job.strategic_note}
                </p>
              </motion.div>
            )}

            <Divider />

            {/* Downloads — primary action */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ ...spring.gentle, delay: 0.15 }}
              className="flex items-center gap-4 flex-wrap"
            >
              {appState.job.resume_latex && (
                <motion.a
                  href={api.resumePdfUrl(appState.job.id)}
                  download
                  whileTap={{ scale: 0.97 }}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold text-white transition-all"
                  style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
                >
                  Download Resume
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                </motion.a>
              )}
              <InterviewFlag
                job={appState.job}
                onUpdate={job => setAppState({ mode: 'result', job })}
              />
            </motion.div>

            {/* Cover letter */}
            {appState.job.cover_letter && (
              <>
                <Divider />
                <CoverLetterSection job={appState.job} />
                <div className="mt-5 flex items-center gap-5">
                  <motion.a
                    href={api.coverLetterPdfUrl(appState.job.id)}
                    download
                    whileTap={{ scale: 0.98 }}
                    className="text-sm text-neutral-500 hover:text-neutral-800 transition-colors"
                  >
                    Download cover letter ↓
                  </motion.a>
                  <CopyButton text={appState.job.cover_letter} label="Copy" />
                </div>
              </>
            )}

            {/* LaTeX source */}
            {appState.job.resume_latex && (
              <>
                <Divider />
                <LatexSection latex={appState.job.resume_latex} />
              </>
            )}

            {/* Original JD */}
            {appState.job.description && (
              <>
                <Divider />
                <JdSection description={appState.job.description} />
              </>
            )}
          </motion.div>
        )}

        {/* ── ERROR STATE ── */}
        {appState.mode === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.gentle}
          >
            <div
              className="flex flex-col items-center justify-center gap-4"
              style={{ minHeight: 'calc(100vh - 180px)' }}
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(239,68,68,0.08)' }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>

              <div className="text-center">
                <p className="text-neutral-700 font-medium">Something went wrong</p>
                <p className="text-sm text-neutral-400 mt-1 max-w-xs">{appState.message}</p>
              </div>

              <div className="flex items-center gap-3 mt-2">
                {appState.jobId != null && (
                  <motion.button
                    onClick={() => handleRetry(appState.jobId!)}
                    disabled={submitting}
                    whileTap={{ scale: 0.97 }}
                    className="px-5 py-2.5 rounded-2xl text-sm font-semibold text-white disabled:opacity-40 transition-all"
                    style={{
                      background: 'var(--c-btn-bg)',
                      boxShadow: 'var(--c-btn-shadow)',
                    }}
                  >
                    {submitting ? 'Retrying…' : 'Try again'}
                  </motion.button>
                )}
                <button
                  onClick={() => setAppState({ mode: 'idle' })}
                  className="px-4 py-2.5 rounded-2xl text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-700"
                  style={{ background: 'rgba(0,0,0,0.04)' }}
                >
                  Start over
                </button>
              </div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
