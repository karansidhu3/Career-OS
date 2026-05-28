'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'

function FitCard({ job }: { job: Job }) {
  const score = job.fit_score ?? 0
  const label = score >= 8 ? 'Strong Match' : score >= 6 ? 'Good Match' : 'Weak Match'
  const color =
    score >= 8
      ? { bg: 'rgba(16,185,129,0.07)', accent: '#059669', ring: 'rgba(16,185,129,0.2)' }
      : score >= 6
      ? { bg: 'rgba(245,158,11,0.07)', accent: '#d97706', ring: 'rgba(245,158,11,0.2)' }
      : { bg: 'rgba(239,68,68,0.07)', accent: '#dc2626', ring: 'rgba(239,68,68,0.2)' }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
      className="rounded-2xl p-6"
      style={{ background: color.bg, border: `1px solid ${color.ring}` }}
    >
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-lg font-semibold" style={{ color: color.accent }}>{label}</span>
            <span className="text-sm font-bold px-2.5 py-0.5 rounded-full" style={{ background: color.ring, color: color.accent }}>
              {score}/10
            </span>
          </div>
          {job.fit_rationale && (
            <ul className="space-y-1.5">
              {job.fit_rationale.map((b, i) => (
                <li key={i} className="flex gap-2 text-sm text-neutral-600">
                  <span style={{ color: color.accent }} className="shrink-0 mt-0.5">•</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="shrink-0 relative w-16 h-16 flex items-center justify-center">
          <svg width="64" height="64" viewBox="0 0 64 64" className="absolute inset-0 -rotate-90">
            <circle cx="32" cy="32" r="26" fill="none" stroke={color.ring} strokeWidth="6" />
            <circle cx="32" cy="32" r="26" fill="none" stroke={color.accent} strokeWidth="6"
              strokeDasharray={`${2 * Math.PI * 26 * score / 10} ${2 * Math.PI * 26}`}
              strokeLinecap="round"
            />
          </svg>
          <span className="text-base font-bold" style={{ color: color.accent }}>{score}</span>
        </div>
      </div>
    </motion.div>
  )
}

function ResumeSection({ job }: { job: Job }) {
  const [expanded, setExpanded] = useState(false)
  if (!job.resume_latex) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-neutral-400 tracking-[0.04em]">Resume</p>
        <div className="flex items-center gap-2">
          <a
            href={api.resumePdfUrl(job.id)}
            download
            className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all"
            style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
          >
            Download PDF
          </a>
          <CopyButton text={job.resume_latex} label="Copy .tex" />
        </div>
      </div>

      <div
        className="rounded-2xl overflow-hidden"
        style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border-subtle)' }}
      >
        <button
          onClick={() => setExpanded(v => !v)}
          className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-medium text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          <span>Preview LaTeX source</span>
          <span>{expanded ? '▲' : '▼'}</span>
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
              <div className="px-5 pb-5 max-h-[500px] overflow-y-auto">
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
  const paragraphs = (job.cover_letter ?? '').split(/\n\n+/).map(p => p.trim()).filter(Boolean)
  if (!paragraphs.length) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-neutral-400 tracking-[0.04em]">Cover letter</p>
        <div className="flex items-center gap-2">
          <a
            href={api.coverLetterPdfUrl(job.id)}
            download
            className="px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200"
            style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)', color: '#6b7280' }}
          >
            Download PDF
          </a>
          <CopyButton text={job.cover_letter!} label="Copy" />
        </div>
      </div>
      <div className="max-w-2xl">
        {paragraphs.map((para, i) => (
          <p key={i} className="text-[15px] text-neutral-700 leading-[1.8] mb-5 last:mb-0">
            {para}
          </p>
        ))}
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
        className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-medium text-neutral-400 hover:text-neutral-600 transition-colors"
      >
        <span>View original job description</span>
        <span>{expanded ? '▲' : '▼'}</span>
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
  if (elapsed < 5) return 'Reading…'
  if (elapsed < 12) return 'Scoring fit…'
  if (elapsed < 22) return 'Writing your resume…'
  return 'Polishing the cover letter…'
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
    setUpdating(true)
    try { setJob(await api.updateStatus(job.id, status)) }
    finally { setUpdating(false) }
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
            onClick={() => router.back()}
            className="text-sm text-neutral-400 hover:text-neutral-700 transition-colors mb-3 flex items-center gap-1"
          >
            ← Back
          </button>
        </div>
        <div
          className="flex flex-col items-center justify-center gap-6"
          style={{ minHeight: 'calc(100vh - 200px)' }}
        >
          <div className="relative flex items-center justify-center">
            <div
              className="absolute rounded-full"
              style={{
                width: 120,
                height: 120,
                background: 'radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%)',
                filter: 'blur(20px)',
              }}
            />
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full" style={{ border: '2.5px solid var(--c-accent-dim)' }} />
              <div className="absolute inset-0 rounded-full animate-spin" style={{ border: '2.5px solid var(--c-accent)', borderTopColor: 'transparent' }} />
            </div>
          </div>
          <div className="text-center">
            <AnimatePresence mode="wait">
              <motion.p
                key={getGenMessage(genElapsed)}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="text-[15px] text-neutral-600 font-medium"
              >
                {getGenMessage(genElapsed)}
              </motion.p>
            </AnimatePresence>
            <p className="text-xs text-neutral-300 mt-2 tabular-nums">{genElapsed}s</p>
          </div>
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
            onClick={() => router.back()}
            className="text-sm text-neutral-400 hover:text-neutral-700 transition-colors mb-3 flex items-center gap-1"
          >
            ← Back
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
            <span className="text-red-400 text-2xl">✕</span>
          </div>
          <div className="text-center">
            <p className="text-neutral-700 font-medium">Generation failed</p>
            <p className="text-sm text-neutral-400 mt-1">Claude didn't respond in time. Try again.</p>
          </div>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="px-5 py-2.5 rounded-2xl text-sm font-semibold text-white disabled:opacity-40 transition-all"
            style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
          >
            {regenerating ? 'Retrying…' : 'Retry'}
          </button>
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
        transition={{ duration: 0.4 }}
        className="pt-8 mb-8"
      >
        <button
          onClick={() => router.back()}
          className="text-sm text-neutral-400 hover:text-neutral-700 transition-colors mb-4 flex items-center gap-1"
        >
          ← Back
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">{job.title}</h1>
            {job.company && <p className="text-[15px] text-neutral-400 mt-1">{job.company}</p>}
          </div>

          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
            {/* Regenerate */}
            <button
              onClick={handleRegenerate}
              disabled={regenerating || updating}
              className="px-3 py-1.5 rounded-xl text-xs font-medium disabled:opacity-40 transition-all flex items-center gap-1.5"
              style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)', color: '#6b7280' }}
            >
              {regenerating && (
                <span className="w-3 h-3 border-2 border-neutral-300 border-t-neutral-500 rounded-full animate-spin" />
              )}
              {regenerating ? 'Starting…' : 'Regenerate'}
            </button>

            {/* Status action buttons */}
            {job.status === 'generated' && (
              <>
                <button
                  onClick={() => handleStatus('applied')}
                  disabled={updating}
                  className="px-3 py-1.5 rounded-xl text-xs font-medium text-white disabled:opacity-40 transition-all"
                  style={{ background: 'linear-gradient(135deg, #34d399, #059669)', boxShadow: '0 4px 12px rgba(16,185,129,0.25)' }}
                >
                  Mark Applied
                </button>
                <button
                  onClick={() => handleStatus('skipped')}
                  disabled={updating}
                  className="px-3 py-1.5 rounded-xl text-xs font-medium text-neutral-500 disabled:opacity-40 transition-all"
                  style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)' }}
                >
                  Skip
                </button>
              </>
            )}
            {job.status === 'applied' && (
              <button
                onClick={() => handleStatus('interview')}
                disabled={updating}
                className="px-3 py-1.5 rounded-xl text-xs font-medium text-white disabled:opacity-40 transition-all"
                style={{ background: 'linear-gradient(135deg, #60a5fa, #2563eb)', boxShadow: '0 4px 12px rgba(37,99,235,0.25)' }}
              >
                Got Interview
              </button>
            )}
            {job.status === 'interview' && (
              <button
                onClick={() => handleStatus('offer')}
                disabled={updating}
                className="px-3 py-1.5 rounded-xl text-xs font-medium text-white disabled:opacity-40 transition-all"
                style={{ background: 'linear-gradient(135deg, #fbbf24, #d97706)', boxShadow: '0 4px 12px rgba(217,119,6,0.25)' }}
              >
                Got Offer 🎉
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* Fit card */}
      {job.fit_score != null && <FitCard job={job} />}

      {/* Single-scroll content */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.4 }}
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
