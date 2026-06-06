'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'
import { spring } from '@/lib/motion'
import { parseStrategicNote } from '@/lib/utils'

function AnalysisSection({ title, bullets }: { title: string; bullets: string[] }) {
  if (!bullets.length) return null
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.12em] text-neutral-500 mb-2">{title}</p>
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

function FitCard({ job }: { job: Job }) {
  const analysis = parseStrategicNote(job.strategic_note)
  const hasContent = analysis || job.strategic_note || (job.fit_rationale && job.fit_rationale.length > 0)
  if (!hasContent) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring.standard}
      className="py-2"
    >
      {analysis ? (
        /* Structured analysis — new format */
        <div className="space-y-6">
          <AnalysisSection title="Good fit" bullets={analysis.goodFit} />
          <AnalysisSection title="Gaps" bullets={analysis.gaps} />
          <AnalysisSection title="Improvement plan" bullets={analysis.plan} />
        </div>
      ) : (
        /* Fallback: old-format prose */
        <>
          {job.strategic_note && (
            <p className="text-[17px] text-neutral-700 leading-[1.8] max-w-2xl mb-4">
              {job.strategic_note}
            </p>
          )}
        </>
      )}
    </motion.div>
  )
}

function ResumeSection({ job }: { job: Job }) {
  const [expanded, setExpanded] = useState(false)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [previewLoaded, setPreviewLoaded] = useState(false)
  const [previewFailed, setPreviewFailed] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // Hooks must come before any conditional return
  useEffect(() => {
    if (!job.resume_latex) return
    let objectUrl: string | null = null
    api.fetchResumePdfPreview(job.id)
      .then(url => { objectUrl = url; setBlobUrl(url) })
      .catch(() => setPreviewFailed(true))
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [job.id, job.resume_latex])

  if (!job.resume_latex) return null

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await api.downloadResumePdf(job.id, job.company)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      {/* Preview — the actual document */}
      <div
        className="relative mb-5 rounded-sm overflow-hidden"
        style={{
          height: 880,
          boxShadow: '0 4px 32px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
          border: '1px solid var(--c-border)',
          background: '#fff',
        }}
      >
        {previewFailed ? (
          <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
            <p className="text-xs text-neutral-400">PDF preview unavailable — download to view</p>
          </div>
        ) : !previewLoaded && (
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
            onLoad={() => setPreviewLoaded(true)}
            title="Resume"
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              display: 'block',
              opacity: previewLoaded ? 1 : 0,
              transition: 'opacity 0.4s ease',
            }}
          />
        )}
      </div>

      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] uppercase tracking-[0.12em] text-neutral-500">Resume</span>
        <div className="flex items-center gap-2">
          <motion.button
            onClick={handleDownload}
            disabled={downloading}
            whileTap={{ scale: 0.97 }}
            className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-60"
            style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
          >
            {downloading ? 'Compiling…' : 'Download PDF'}
          </motion.button>
          <CopyButton text={job.resume_latex} label="Copy .tex" />
        </div>
      </div>

      <div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
        >
          {expanded ? 'Hide source ↑' : 'LaTeX source ↓'}
        </button>
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-3 max-h-[500px] overflow-y-auto rounded-xl p-4" style={{ background: 'var(--c-surface)' }}>
                <pre className="text-xs font-mono text-neutral-500 leading-relaxed whitespace-pre-wrap break-all">
                  {job.resume_latex}
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function CoverLetterSection({ job }: { job: Job }) {
  const [downloading, setDownloading] = useState(false)
  const paragraphs = (job.cover_letter ?? '').split(/\n\n+/).map(p => p.trim()).filter(Boolean)
  if (!paragraphs.length) return null

  const handleDownload = async () => {
    setDownloading(true)
    try { await api.downloadCoverLetterPdf(job.id, job.company) }
    finally { setDownloading(false) }
  }

  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.12em] text-neutral-500 mb-4">Cover letter</p>
      <div style={{ maxWidth: '520px' }}>
        {paragraphs.map((para, i) => (
          <p key={i} className="text-[15px] text-neutral-700 leading-[1.8] mb-5 last:mb-0">
            {para}
          </p>
        ))}
      </div>
      <div className="mt-5 flex items-center gap-4 flex-wrap">
        <motion.button
          onClick={handleDownload}
          disabled={downloading}
          whileTap={{ scale: 0.97 }}
          className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all inline-flex items-center gap-2 disabled:opacity-60"
          style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
        >
          {downloading ? 'Compiling…' : 'Download Cover Letter'}
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </motion.button>
        <CopyButton text={job.cover_letter!} label="Copy" />
      </div>
    </div>
  )
}

function JdSection({ description }: { description: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border-subtle)' }}
    >
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        <span>View original job description</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            {expanded ? <path d="M18 15l-6-6-6 6" /> : <path d="M6 9l6 6 6-6" />}
          </svg>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 max-h-[400px] overflow-y-auto">
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

function Divider() {
  return <div className="my-8" style={{ borderTop: '1px solid var(--c-border)' }} />
}

function getGenMessage(elapsed: number): string {
  if (elapsed < 14) return 'Generating your application…'
  if (elapsed < 32) return 'Matching your background to this role…'
  return 'This is taking a moment…'
}

export default function JobPage() {
  const params = useParams()
  const router = useRouter()
  const id = Number(params.id)
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [genElapsed, setGenElapsed] = useState(0)
  // Undo state — 5-second window after any status transition
  const [undoPrev, setUndoPrev] = useState<string | null>(null)
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    api.getJob(id)
      .then(setJob)
      .catch(() => router.push('/'))
      .finally(() => setLoading(false))
  }, [id, router])

  // Poll while processing
  useEffect(() => {
    if (!job || job.status !== 'processing') return
    const poll = setInterval(async () => {
      try {
        const updated = await api.getJob(id)
        setJob(updated)
      } catch { /* keep polling */ }
    }, 2500)
    return () => clearInterval(poll)
  }, [job?.status, id])

  // Elapsed timer while processing
  useEffect(() => {
    if (job?.status !== 'processing') { setGenElapsed(0); return }
    setGenElapsed(0)
    const t = setInterval(() => setGenElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [job?.status])

  const handleStatus = async (status: string) => {
    if (!job) return
    const previous = job.status
    setUpdating(true)
    try {
      setJob(await api.updateStatus(job.id, status))
      // Open 5-second undo window
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current)
      setUndoPrev(previous)
      undoTimerRef.current = setTimeout(() => setUndoPrev(null), 5000)
    } finally {
      setUpdating(false)
    }
  }

  const handleRegenerate = async () => {
    if (!job) return
    setRegenerating(true)
    try {
      const updated = await api.regenerate(job.id)
      setJob(updated) // status will be "processing", polling takes over
    } finally {
      setRegenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
      </div>
    )
  }

  if (!job) return null

  // --- Processing state ---
  if (job.status === 'processing') {
    return (
      <div className="px-6 pb-24 max-w-3xl mx-auto">
        <div className="pt-8 mb-10">
          <button
            onClick={() => router.push('/')}
            className="text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-4 flex items-center gap-1.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Applications
          </button>
        </div>
        <div
          className="flex flex-col items-center justify-center gap-6"
          style={{ minHeight: 'calc(100vh - 200px)' }}
        >
          <div className="w-10 h-10 relative">
            <div className="absolute inset-0 rounded-full" style={{ border: '2px solid var(--c-accent-dim)' }} />
            <div className="absolute inset-0 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent)', borderTopColor: 'transparent' }} />
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={getGenMessage(genElapsed)}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={spring.gentle}
              className="text-[15px] text-neutral-600 font-medium text-center"
            >
              {getGenMessage(genElapsed)}
            </motion.p>
          </AnimatePresence>
        </div>
      </div>
    )
  }

  // --- Failed state ---
  if (job.status === 'failed') {
    return (
      <div className="px-6 pb-24 max-w-3xl mx-auto">
        <div className="pt-8 mb-10">
          <button
            onClick={() => router.push('/')}
            className="text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-4 flex items-center gap-1.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Applications
          </button>
        </div>
        <div
          className="flex flex-col items-center justify-center gap-5"
          style={{ minHeight: 'calc(100vh - 200px)' }}
        >
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(239,68,68,0.08)' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-neutral-700 font-medium">Generation failed</p>
            <p className="text-sm text-neutral-500 mt-1">Claude didn't respond in time. Try again.</p>
          </div>
          <motion.button
            onClick={handleRegenerate}
            disabled={regenerating}
            whileTap={{ scale: 0.97 }}
            className="px-5 py-2.5 rounded-2xl text-sm font-semibold text-white disabled:opacity-40 transition-all"
            style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
          >
            {regenerating ? 'Retrying…' : 'Retry'}
          </motion.button>
        </div>
      </div>
    )
  }

  // --- Normal view ---
  return (
    <div className="px-6 pb-24 max-w-3xl mx-auto">

      {/* Header */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={spring.gentle}
        className="pt-8 mb-8"
      >
        <button
          onClick={() => router.back()}
          className="text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-4 flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Applications
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">{job.title}</h1>
            {job.company && <p className="text-[15px] text-neutral-600 mt-1">{job.company}</p>}
          </div>

          <div className="flex items-center gap-4 shrink-0">
            {/* Status transitions — forward and reverse */}
            {job.status === 'generated' && (
              <>
                <button onClick={() => handleStatus('applied')} disabled={updating}
                  className="text-xs font-medium disabled:opacity-40 transition-colors"
                  style={{ color: 'var(--c-success)' }}>
                  Mark applied
                </button>
                <button onClick={() => handleStatus('skipped')} disabled={updating}
                  className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors">
                  Skip
                </button>
              </>
            )}
            {job.status === 'applied' && (
              <>
                <button onClick={() => handleStatus('interview')} disabled={updating}
                  className="text-xs font-medium disabled:opacity-40 transition-colors"
                  style={{ color: 'var(--c-warn)' }}>
                  Got interview
                </button>
                <button onClick={() => handleStatus('generated')} disabled={updating}
                  className="text-xs text-neutral-400 hover:text-neutral-600 disabled:opacity-40 transition-colors">
                  ← Unmark
                </button>
              </>
            )}
            {job.status === 'interview' && (
              <>
                <button onClick={() => handleStatus('offer')} disabled={updating}
                  className="text-xs font-medium disabled:opacity-40 transition-colors"
                  style={{ color: 'var(--c-warn)' }}>
                  Got offer
                </button>
                <button onClick={() => handleStatus('applied')} disabled={updating}
                  className="text-xs text-neutral-400 hover:text-neutral-600 disabled:opacity-40 transition-colors">
                  ← Applied
                </button>
              </>
            )}
            {job.status === 'offer' && (
              <button onClick={() => handleStatus('interview')} disabled={updating}
                className="text-xs text-neutral-400 hover:text-neutral-600 disabled:opacity-40 transition-colors">
                ← Interview
              </button>
            )}
            {job.status === 'skipped' && (
              <button onClick={() => handleStatus('generated')} disabled={updating}
                className="text-xs text-neutral-400 hover:text-neutral-600 disabled:opacity-40 transition-colors">
                ← Reopen
              </button>
            )}
            {/* Undo — 5-second window after any status change */}
            <AnimatePresence>
              {undoPrev && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  onClick={() => {
                    if (undoTimerRef.current) clearTimeout(undoTimerRef.current)
                    setUndoPrev(null)
                    handleStatus(undoPrev)
                  }}
                  className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors underline decoration-neutral-300"
                >
                  Undo
                </motion.button>
              )}
            </AnimatePresence>
            {/* Regenerate — always available */}
            <button onClick={handleRegenerate} disabled={regenerating || updating}
              className="text-xs text-neutral-500 hover:text-neutral-700 disabled:opacity-40 transition-colors flex items-center gap-1.5">
              {regenerating && <span className="w-3 h-3 rounded-full animate-spin" style={{ border: '1.5px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />}
              {regenerating ? 'Starting…' : 'Regenerate'}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Analysis at top — archive view is revisit context, not first-time reveal */}
      {job.fit_score != null && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring.gentle, delay: 0.08 }}
          className="mb-2"
        >
          <FitCard job={job} />
        </motion.div>
      )}

      {/* Single-scroll content */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.12 }}
      >
        <Divider />
        <ResumeSection job={job} />

        {job.cover_letter && (
          <>
            <Divider />
            <CoverLetterSection job={job} />
          </>
        )}

        {job.description && (
          <>
            <Divider />
            <JdSection description={job.description} />
          </>
        )}
      </motion.div>
    </div>
  )
}
