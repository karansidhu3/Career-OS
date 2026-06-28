'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { api, CandidacyInsights, Job } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'
import { AutoTextarea } from '@/components/AutoTextarea'
import { BrandMark } from '@/components/BrandMark'
import { SectionLabel } from '@/components/SectionLabel'
import { ScoreRing } from '@/components/ScoreRing'
import { spring } from '@/lib/motion'
import { relativeDate, parseStrategicNote } from '@/lib/utils'

// ─── Types ──────────────────────────────────────────────────────────────────

type AppState =
  | { mode: 'idle' }
  | { mode: 'generating'; jobId: number }
  | { mode: 'result'; job: Job }
  | { mode: 'error'; jobId?: number; message: string }

// ─── Helpers ────────────────────────────────────────────────────────────────

function getGenMessage(elapsed: number): string {
  if (elapsed < 14) return 'Generating your application…'
  if (elapsed < 32) return 'Matching your background to this role…'
  return 'Finishing your resume…'
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function AnalysisSection({ title, bullets }: { title: string; bullets: string[] }) {
  if (!bullets.length) return null
  return (
    <div>
      <SectionLabel className="mb-2">{title}</SectionLabel>
      <ul className="space-y-1.5">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2.5 text-[15px] text-neutral-700 leading-snug">
            <span className="text-neutral-400 shrink-0 mt-0.5 select-none">·</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
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
            transition={spring.snappy}
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


function StatusActions({ job, onUpdate }: { job: Job; onUpdate: (j: Job) => void }) {
  const [updating, setUpdating] = useState<string | null>(null)

  const mark = async (status: string) => {
    setUpdating(status)
    try {
      const updated = await api.updateStatus(job.id, status)
      onUpdate(updated)
    } finally {
      setUpdating(null)
    }
  }

  if (job.status === 'interview' || job.status === 'offer') {
    return (
      <span className="text-xs font-medium" style={{ color: 'var(--c-warn)' }}>
        {job.status === 'offer' ? 'Offer received' : 'Interview stage'}
      </span>
    )
  }

  if (job.status === 'applied') {
    return (
      <button
        onClick={() => mark('interview')}
        disabled={!!updating}
        className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors"
      >
        {updating === 'interview' ? 'Saving…' : 'Got interview'}
      </button>
    )
  }

  // generated / default
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => mark('applied')}
        disabled={!!updating}
        className="text-xs font-medium disabled:opacity-40 transition-colors"
        style={{ color: 'var(--c-success)' }}
      >
        {updating === 'applied' ? 'Saving…' : 'Mark applied'}
      </button>
      <button
        onClick={() => mark('interview')}
        disabled={!!updating}
        className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors"
      >
        {updating === 'interview' ? 'Saving…' : 'Got interview'}
      </button>
    </div>
  )
}

// ─── Selected projects bar — verify what the AI chose ────────────────────────

function SelectedProjectsBar({ projects }: { projects: string[] }) {
  if (!projects.length) return null
  return (
    <div className="flex items-center gap-2 flex-wrap mb-6">
      <span className="text-[10px] uppercase tracking-[0.12em] text-neutral-400 shrink-0">Emphasized</span>
      {projects.map(p => (
        <span
          key={p}
          className="text-xs text-neutral-700 px-2 py-0.5 rounded-full"
          style={{ background: 'var(--c-tag-bg)', border: '1px solid var(--c-tag-border)' }}
        >
          {p}
        </span>
      ))}
    </div>
  )
}

// ─── Cover letter editor — editable before download ──────────────────────────

function CoverLetterEditor({ job, onSave }: { job: Job; onSave: (updated: Job) => void }) {
  const [text, setText] = useState(job.cover_letter ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [downloaded, setDownloaded] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const save = async () => {
    if (!text.trim()) return
    setSaving(true)
    try {
      const updated = await api.updateCoverLetter(job.id, text)
      onSave(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const isDirty = text !== (job.cover_letter ?? '')

  return (
    <div>
      <textarea
        value={text}
        onChange={e => { setText(e.target.value); setSaved(false) }}
        rows={12}
        className="w-full text-[15px] text-neutral-700 leading-[1.8] resize-none focus:outline-none rounded-xl p-4"
        style={{
          background: 'var(--c-glass-bg)',
          border: '1px solid var(--c-glass-border)',
        }}
      />
      <div className="mt-4 flex items-center gap-4 flex-wrap">
        <motion.button
          onClick={async () => {
            setDownloading(true)
            try {
              await api.downloadCoverLetterPdf(job.id, job.company)
              setDownloaded(true)
            } finally {
              setDownloading(false)
            }
          }}
          disabled={downloading}
          whileTap={{ scale: 0.97 }}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold text-white transition-all disabled:opacity-60"
          style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
        >
          {downloading ? 'Compiling…' : downloaded ? 'Letter saved' : 'Download Cover Letter'}
          {downloaded ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          )}
        </motion.button>
        <CopyButton text={text} label="Copy" />
        {isDirty && (
          <button
            onClick={save}
            disabled={saving}
            className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors"
          >
            {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save edits'}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Resume preview — inline PDF, the actual artifact ────────────────────────
// Accepts either external blob state (passed from parent, shared across instances)
// or manages its own internal fetch (used by archive page).

function ResumePreview({
  jobId,
  blobUrl: externalBlobUrl,
  loaded: externalLoaded,
  failed: externalFailed,
  onLoad,
  onError,
}: {
  jobId: number
  blobUrl?: string | null
  loaded?: boolean
  failed?: boolean
  onLoad?: () => void
  onError?: () => void
}) {
  const [internalBlobUrl, setInternalBlobUrl] = useState<string | null>(null)
  const [internalLoaded, setInternalLoaded] = useState(false)
  const [internalFailed, setInternalFailed] = useState(false)

  const isManaged = externalBlobUrl !== undefined

  useEffect(() => {
    if (isManaged) return
    let objectUrl: string | null = null
    let cancelled = false
    api.fetchResumePdfPreview(jobId)
      .then(url => {
        if (cancelled) { URL.revokeObjectURL(url); return }
        objectUrl = url
        setInternalBlobUrl(url)
      })
      .catch(() => { if (!cancelled) setInternalFailed(true) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [jobId, isManaged])

  const blobUrl = isManaged ? (externalBlobUrl ?? null) : internalBlobUrl
  const loaded = isManaged ? (externalLoaded ?? false) : internalLoaded
  const failed = isManaged ? (externalFailed ?? false) : internalFailed

  const handleLoad = () => { if (!isManaged) setInternalLoaded(true); onLoad?.() }
  const handleError = () => { if (!isManaged) setInternalFailed(true); onError?.() }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: loaded ? 1 : 0.35, y: 0 }}
      transition={{ ...spring.gentle, delay: 0.1 }}
      className="relative mb-6 rounded-sm overflow-hidden"
      style={{
        height: 880,
        boxShadow: '0 4px 32px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
        border: '1px solid var(--c-border)',
        background: '#fff',
      }}
    >
      {failed ? (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
          <p className="text-xs text-neutral-400">PDF preview unavailable — download to view</p>
        </div>
      ) : !loaded && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
          <div className="flex flex-col items-center gap-3">
            <div className="w-6 h-6 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
            <p className="text-xs text-neutral-400">Compiling PDF…</p>
          </div>
        </div>
      )}
      {blobUrl && (
        <iframe
          src={blobUrl}
          onLoad={handleLoad}
          onError={handleError}
          title="Resume"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            display: 'block',
            opacity: loaded ? 1 : 0,
            transition: 'opacity 0.4s ease',
          }}
        />
      )}
    </motion.div>
  )
}

// ─── Divider — draws from left on mount ──────────────────────────────────────

function Divider({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      className="my-8"
      initial={{ scaleX: 0, opacity: 0 }}
      animate={{ scaleX: 1, opacity: 1 }}
      transition={{ ...spring.snappy, delay }}
      style={{ height: '1px', background: 'var(--c-border)', transformOrigin: 'left' }}
    />
  )
}

// ─── Generating skeleton — ghost of what's being built ──────────────────────

function GeneratingSkeleton() {
  return (
    <div className="w-full mt-14 pointer-events-none" aria-hidden>
      <div className="opacity-[0.12]">
        {/* Title */}
        <div className="h-9 w-[52%] rounded-lg skeleton-shimmer mb-2.5" />
        {/* Company */}
        <div className="h-4 w-[22%] rounded skeleton-shimmer mb-2.5" />
        {/* Fit score */}
        <div className="h-3 w-[10%] rounded skeleton-shimmer mb-8" />
        {/* Divider */}
        <div className="h-px w-full skeleton-shimmer mb-8" />
        {/* Good fit */}
        <div className="mb-7">
          <div className="h-2 w-14 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[68%] rounded skeleton-shimmer" />
            <div className="h-3.5 w-[54%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Gaps */}
        <div className="mb-7">
          <div className="h-2 w-8 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[61%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Improvement plan */}
        <div className="mb-8">
          <div className="h-2 w-24 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[72%] rounded skeleton-shimmer" />
            <div className="h-3.5 w-[48%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Emphasized pills */}
        <div className="flex items-center gap-2 mb-6">
          <div className="h-2 w-16 rounded skeleton-shimmer" />
          <div className="h-5 w-24 rounded-full skeleton-shimmer" />
          <div className="h-5 w-20 rounded-full skeleton-shimmer" />
          <div className="h-5 w-28 rounded-full skeleton-shimmer" />
        </div>
        {/* PDF ghost */}
        <div className="h-[360px] rounded-sm skeleton-shimmer" />
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Home() {
  const [appState, setAppState] = useState<AppState>({ mode: 'idle' })
  const [jd, setJd] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [genElapsed, setGenElapsed] = useState(0)
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  // Download state — completion signals loop has ended; loading shows compile progress
  const [resumeDownloaded, setResumeDownloaded] = useState(false)
  const [resumeDownloading, setResumeDownloading] = useState(false)
  // Profile readiness — show setup prompt if profile is empty
  const [profileEmpty, setProfileEmpty] = useState(false)
  const [insights, setInsights] = useState<CandidacyInsights | null>(() => {
    // Populate from cache synchronously so layout is stable on first render
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('careeros-insights-v2')
      if (raw) {
        const { data, ts } = JSON.parse(raw) as { data: CandidacyInsights; ts: number }
        if (Date.now() - ts < 60 * 60 * 1000) return data
      }
    } catch {}
    return null
  })

  // PDF preview state — fetched once, shared between mobile and desktop renders
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [pdfLoaded, setPdfLoaded] = useState(false)
  const [pdfFailed, setPdfFailed] = useState(false)

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
    const CACHE_KEY = 'careeros-insights-v2'
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

  const handleDownloadResume = useCallback(async () => {
    if (appState.mode !== 'result') return
    setResumeDownloading(true)
    try {
      await api.downloadResumePdf(appState.job.id, appState.job.company)
      setResumeDownloaded(true)
    } finally {
      setResumeDownloading(false)
    }
  }, [appState])

  useEffect(() => { loadRecent() }, [loadRecent])
  useEffect(() => { loadInsights() }, [loadInsights])

  // Fetch PDF once per result job — shared between mobile and desktop ResumePreview renders
  const resultJobId = appState.mode === 'result' ? appState.job.id : null
  useEffect(() => {
    if (!resultJobId) {
      setPdfBlobUrl(null)
      setPdfLoaded(false)
      setPdfFailed(false)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    setPdfBlobUrl(null)
    setPdfLoaded(false)
    setPdfFailed(false)
    api.fetchResumePdfPreview(resultJobId)
      .then(url => {
        if (cancelled) { URL.revokeObjectURL(url); return }
        objectUrl = url
        setPdfBlobUrl(url)
      })
      .catch(() => { if (!cancelled) setPdfFailed(true) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [resultJobId])

  // ── Profile completeness — show setup note if profile is empty ──
  useEffect(() => {
    api.getProfile()
      .then(p => {
        const hasContent = (p.experience && p.experience.length > 0) ||
                           (p.projects && p.projects.length > 0)
        setProfileEmpty(!hasContent)
      })
      .catch(() => {})
  }, [])

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
      window.scrollTo({ top: 0, behavior: 'smooth' })
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
    setResumeDownloaded(false)
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
    <div className="max-w-3xl xl:max-w-6xl mx-auto px-6 pb-24">
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
            <div className="pt-12">

              {/* ── Brand mark — glow emanates from the ring stroke itself ── */}
              <motion.div
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...spring.bouncy, delay: 0.05 }}
                className="flex justify-center mb-8"
              >
                <span className="brand-ring-glow text-neutral-600" style={{ opacity: 0.55 }}>
                  <BrandMark size={56} physicalStroke={1.5} />
                </span>
              </motion.div>

              {/* ── Workspace zone ── */}
              <div
                className="jd-workspace rounded-2xl relative cursor-text"
                onClick={() => textareaRef.current?.focus()}
                style={{ background: 'var(--c-glass-bg)' }}
              >
                {/* Writing surface */}
                <div
                  className="px-8 pt-7 pb-16"
                  style={{ minHeight: '28vh' }}
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
                    className="flex items-center gap-2 text-sm text-neutral-700 hover:text-neutral-900 disabled:opacity-30 transition-colors"
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

              {/* ── Output hint — what arrives, or setup nudge if profile is empty ── */}
              <div className="mt-3 text-center">
                {profileEmpty ? (
                  <p className="text-xs text-neutral-400">
                    <Link
                      href="/profile"
                      className="underline decoration-neutral-300 hover:text-neutral-600 transition-colors"
                    >
                      Add your experience
                    </Link>
                    {' '}for a tailored resume
                  </p>
                ) : (
                  <p className="text-xs text-neutral-400 tracking-wide">
                    Resume · Cover letter · Fit analysis
                  </p>
                )}
              </div>

              {/* ── Candidacy signal — "arrived at a conclusion" reveal ── */}
              <AnimatePresence>
                {insights && insights.count > 0 && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.28, ease: [0.25, 0, 0, 1] }}
                    className="overflow-hidden"
                  >
                    {/* Inner reveal: delayed y-rise with spring — the "conclusion" motion */}
                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ ...spring.gentle, delay: 0.2 }}
                      className="mt-12"
                    >
                      {insights.count < 3 ? (
                        /* Not enough data yet */
                        <>
                          <p className="text-xl font-semibold text-neutral-700 tracking-tight leading-tight mb-2">
                            {insights.count} application{insights.count === 1 ? '' : 's'}
                          </p>
                          <p className="text-sm text-neutral-500 leading-relaxed">
                            Apply to {3 - insights.count} more for a candidacy read.
                          </p>
                        </>
                      ) : (
                        /* Structured insight — scannable in seconds */
                        <>
                          <p className="text-xl font-semibold text-neutral-700 tracking-tight leading-snug mb-5">
                            {insights.headline ?? `${insights.count} applications`}
                          </p>
                          <div className="space-y-4 max-w-lg">
                            {insights.observed && (
                              <div>
                                <SectionLabel className="mb-1">Observed</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.observed}</p>
                              </div>
                            )}
                            {insights.gap && (
                              <div>
                                <SectionLabel className="mb-1">Gap</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.gap}</p>
                              </div>
                            )}
                            {insights.action && (
                              <div>
                                <SectionLabel className="mb-1">Action</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.action}</p>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Recent applications ── */}
              {recentJobs.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.3 }}
                  className="mt-12 pt-6"
                  style={{ borderTop: '1px solid var(--c-border)' }}
                >
                  <SectionLabel className="mb-3">Recent</SectionLabel>
                  {recentJobs.map(job => (
                    <Link
                      key={job.id}
                      href={`/jobs/${job.id}`}
                      className="flex items-center justify-between py-2.5 group"
                    >
                      <span className="flex items-center gap-1.5 min-w-0 mr-6">
                        <span className="text-sm text-neutral-600 group-hover:text-neutral-800 transition-colors truncate">
                          {job.title || 'Untitled'}
                          {job.company ? ` — ${job.company}` : ''}
                        </span>
                        {(job.status === 'interview' || job.status === 'offer') && (
                          <span className="shrink-0 w-1.5 h-1.5 rounded-full" style={{ background: 'var(--c-warn)' }} />
                        )}
                      </span>
                      <span className="shrink-0 text-xs text-neutral-500 font-mono tabular-nums">
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
            {/* Brand arc + message — compressed upper area */}
            <div className="flex flex-col items-center gap-5 pt-24">
              {/* Ring becomes a spinning arc — same mark, active state */}
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
                style={{ width: 52, height: 52 }}
                className="brand-ring-glow"
              >
                <svg width={52} height={52} viewBox="0 0 52 52" fill="none">
                  <circle cx={26} cy={26} r={19.5} stroke="var(--c-accent-dim)" strokeWidth={1.5} />
                  <circle
                    cx={26} cy={26} r={19.5}
                    stroke="var(--c-accent)"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeDasharray="79.6 42.9"
                  />
                </svg>
              </motion.div>

              {/* Message */}
              <AnimatePresence mode="wait">
                <motion.p
                  key={getGenMessage(genElapsed)}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={spring.gentle}
                  className="text-[14px] text-neutral-500 text-center"
                >
                  {getGenMessage(genElapsed)}
                </motion.p>
              </AnimatePresence>
            </div>

            {/* Skeleton — ghost of what's being built */}
            <GeneratingSkeleton />
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
            {/* Watermark ring — atmospheric depth, barely there */}
            <div
              aria-hidden
              className="pointer-events-none fixed hidden xl:block"
              style={{ right: -140, top: '50%', transform: 'translateY(-50%)', opacity: 0.038, zIndex: 0, color: 'var(--c-accent)' }}
            >
              <svg width={520} height={520} viewBox="0 0 520 520" fill="none" stroke="currentColor">
                <circle cx={260} cy={260} r={238} strokeWidth={1} />
                <circle cx={260} cy={260} r={188} strokeWidth={0.5} />
              </svg>
            </div>

            {/* Back button */}
            <div className="pt-8 mb-8">
              <button
                onClick={resetToIdle}
                className={`text-sm transition-colors flex items-center gap-1.5 ${
                  resumeDownloaded
                    ? 'text-neutral-700 hover:text-neutral-900 font-medium'
                    : 'text-neutral-500 hover:text-neutral-800'
                }`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                New application
                <span className="text-xs font-normal ml-1 opacity-60">⌘N</span>
              </button>
            </div>

            {/* Title + ScoreRing row */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <h1 className="heading-lit text-[2rem] font-semibold text-neutral-900 leading-tight tracking-tight">
                  {appState.job.title}
                </h1>
                {appState.job.company && (
                  <p className="text-[15px] text-neutral-600 mt-0.5">{appState.job.company}</p>
                )}
              </div>
              {appState.job.fit_score != null && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ ...spring.bouncy, delay: 0.15 }}
                  className="shrink-0 mt-1"
                >
                  <ScoreRing score={appState.job.fit_score} size={64} celebrate />
                </motion.div>
              )}
            </div>

            {/* Two-column grid at xl+ — left: content, right: sticky PDF */}
            <div className="xl:grid xl:grid-cols-[1fr_440px] xl:gap-16 xl:items-start">

              {/* ── LEFT COLUMN ── */}
              <div>
                {/* Strategic analysis */}
                {appState.job.strategic_note && (() => {
                  const analysis = parseStrategicNote(appState.job.strategic_note)
                  return (
                    <>
                      <Divider delay={0} />
                      <motion.div
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...spring.gentle, delay: 0.05 }}
                        className="mb-2"
                      >
                        {analysis ? (
                          <div className="space-y-6">
                            <AnalysisSection title="Good fit" bullets={analysis.goodFit} />
                            <AnalysisSection title="Gaps" bullets={analysis.gaps} />
                            <AnalysisSection title="Improvement plan" bullets={analysis.plan} />
                          </div>
                        ) : (
                          <p className="text-[15px] text-neutral-700 leading-[1.8] max-w-[520px]">
                            {appState.job.strategic_note}
                          </p>
                        )}
                      </motion.div>
                    </>
                  )
                })()}

                <Divider delay={0.05} />

                {/* Projects bar + compression notice */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.08 }}
                >
                  {appState.job.selected_projects && appState.job.selected_projects.length > 0 && (
                    <SelectedProjectsBar projects={appState.job.selected_projects} />
                  )}
                  {(appState.job.compression_attempts ?? 0) > 0 && (
                    <p className="text-xs text-neutral-400 font-mono -mt-1 mb-3">
                      compressed to 1 page · {appState.job.compression_attempts} {appState.job.compression_attempts === 1 ? 'pass' : 'passes'}
                    </p>
                  )}
                </motion.div>

                {/* Resume preview — mobile/tablet only (xl shows it in right column) */}
                {appState.job.resume_latex && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...spring.gentle, delay: 0.1 }}
                    className="relative xl:hidden"
                  >
                    <ResumePreview
                      jobId={appState.job.id}
                      blobUrl={pdfBlobUrl}
                      loaded={pdfLoaded}
                      failed={pdfFailed}
                      onLoad={() => setPdfLoaded(true)}
                      onError={() => setPdfFailed(true)}
                    />
                    <div className="absolute top-3 right-3 z-10">
                      <motion.button
                        onClick={handleDownloadResume}
                        disabled={resumeDownloading}
                        whileTap={{ scale: 0.97 }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-60 transition-all"
                        style={{ background: 'rgba(24,24,27,0.72)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
                      >
                        {resumeDownloading ? 'Compiling…' : resumeDownloaded ? 'Saved ✓' : 'Download PDF'}
                      </motion.button>
                    </div>
                  </motion.div>
                )}

                {/* Download + status actions */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.12 }}
                  className="flex items-center gap-4 flex-wrap mb-2"
                >
                  {appState.job.resume_latex && (
                    <motion.button
                      onClick={handleDownloadResume}
                      disabled={resumeDownloading}
                      whileTap={{ scale: 0.97 }}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold text-white transition-all disabled:opacity-60"
                      style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
                    >
                      {resumeDownloading ? 'Compiling…' : resumeDownloaded ? 'Resume saved' : 'Download Resume'}
                      {resumeDownloaded ? (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      ) : (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                      )}
                    </motion.button>
                  )}
                  <StatusActions
                    job={appState.job}
                    onUpdate={job => setAppState({ mode: 'result', job })}
                  />
                </motion.div>

                {/* Cover letter */}
                {appState.job.cover_letter && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...spring.gentle, delay: 0.16 }}
                  >
                    <Divider delay={0.14} />
                    <CoverLetterEditor
                      job={appState.job}
                      onSave={job => setAppState({ mode: 'result', job })}
                    />
                  </motion.div>
                )}

                {/* LaTeX source */}
                {appState.job.resume_latex && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ ...spring.gentle, delay: 0.2 }}
                  >
                    <Divider delay={0.18} />
                    <LatexSection latex={appState.job.resume_latex} />
                  </motion.div>
                )}
              </div>

              {/* ── RIGHT COLUMN — sticky PDF (xl+ only) ── */}
              {appState.job.resume_latex && (
                <div className="hidden xl:block">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...spring.heavy, delay: 0.18 }}
                    className="relative sticky"
                    style={{ top: 96 }}
                  >
                    <ResumePreview
                      jobId={appState.job.id}
                      blobUrl={pdfBlobUrl}
                      loaded={pdfLoaded}
                      failed={pdfFailed}
                      onLoad={() => setPdfLoaded(true)}
                      onError={() => setPdfFailed(true)}
                    />
                    <div className="absolute top-3 right-3 z-10">
                      <motion.button
                        onClick={handleDownloadResume}
                        disabled={resumeDownloading}
                        whileTap={{ scale: 0.97 }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-60 transition-all"
                        style={{ background: 'rgba(24,24,27,0.72)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
                      >
                        {resumeDownloading ? 'Compiling…' : resumeDownloaded ? 'Saved ✓' : 'Download PDF'}
                      </motion.button>
                    </div>
                  </motion.div>
                </div>
              )}
            </div>
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
                <p className="text-[15px] text-neutral-700 font-medium max-w-xs">{appState.message}</p>
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
