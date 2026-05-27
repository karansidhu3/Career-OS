'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  generated: { label: 'Generated',  color: '#7c3aed' },
  applied:   { label: 'Applied',    color: '#059669' },
  skipped:   { label: 'Skipped',    color: '#9ca3af' },
  interview: { label: 'Interview',  color: '#2563eb' },
  offer:     { label: 'Offer',      color: '#d97706' },
}

function FitCard({ job }: { job: Job }) {
  const score = job.fit_score ?? 0
  const label = score >= 8 ? 'Strong Match' : score >= 6 ? 'Good Match' : 'Weak Match'
  const color = score >= 8 ? { bg: 'rgba(16,185,129,0.07)', accent: '#059669', ring: 'rgba(16,185,129,0.2)' }
              : score >= 6 ? { bg: 'rgba(245,158,11,0.07)', accent: '#d97706', ring: 'rgba(245,158,11,0.2)' }
              : { bg: 'rgba(239,68,68,0.07)', accent: '#dc2626', ring: 'rgba(239,68,68,0.2)' }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
      className="rounded-3xl p-6 mb-6"
      style={{
        background: color.bg,
        border: `1px solid ${color.ring}`,
      }}
    >
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-lg font-semibold" style={{ color: color.accent }}>{label}</span>
            <span
              className="text-sm font-bold px-2.5 py-0.5 rounded-full"
              style={{ background: color.ring, color: color.accent }}
            >
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
        {/* Score arc visual */}
        <div className="shrink-0 relative w-16 h-16 flex items-center justify-center">
          <svg width="64" height="64" viewBox="0 0 64 64" className="absolute inset-0 -rotate-90">
            <circle cx="32" cy="32" r="26" fill="none" stroke={color.ring} strokeWidth="6" />
            <circle
              cx="32" cy="32" r="26" fill="none"
              stroke={color.accent} strokeWidth="6"
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

function ChangesCard({ job }: { job: Job }) {
  if (!job.fit_rationale?.length) return null
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.4 }}
      className="rounded-2xl p-5 mb-6"
      style={{
        background: 'rgba(255,255,255,0.7)',
        border: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-3">
        Why materials were tailored this way
      </p>
      <ul className="space-y-2">
        {job.fit_rationale.map((b, i) => (
          <li key={i} className="flex gap-2 text-sm text-neutral-600">
            <span className="text-indigo-400 shrink-0">→</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}

export default function JobPage() {
  const params = useParams()
  const router = useRouter()
  const id = Number(params.id)
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    api.getJob(id)
      .then(setJob)
      .catch(() => router.push('/'))
      .finally(() => setLoading(false))
  }, [id, router])

  const handleStatus = async (status: string) => {
    if (!job) return
    setUpdating(true)
    try {
      setJob(await api.updateStatus(job.id, status))
    } finally {
      setUpdating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (!job) return null

  const statusInfo = STATUS_MAP[job.status] ?? STATUS_MAP.generated

  return (
    <div className="px-6 pb-24 max-w-5xl mx-auto">
      {/* Back + header */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="pt-8 mb-6 flex items-start justify-between gap-4"
      >
        <div>
          <button
            onClick={() => router.push('/')}
            className="text-sm text-neutral-400 hover:text-neutral-700 transition-colors mb-2 flex items-center gap-1"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-semibold text-neutral-900">{job.title}</h1>
          {job.company && <p className="text-neutral-400 mt-0.5">{job.company}</p>}
          {job.url && (
            <a href={job.url} target="_blank" rel="noopener noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-600 mt-1 block">
              {job.url}
            </a>
          )}
        </div>

        {/* Status + actions */}
        <div className="flex items-center gap-2 shrink-0 pt-6">
          <span className="text-sm font-medium" style={{ color: statusInfo.color }}>
            {statusInfo.label}
          </span>
          {job.status === 'generated' && (
            <>
              <button
                onClick={() => handleStatus('applied')}
                disabled={updating}
                className="px-4 py-2 rounded-xl text-sm font-medium text-white disabled:opacity-40 transition-all"
                style={{ background: 'linear-gradient(135deg, #34d399, #059669)', boxShadow: '0 4px 12px rgba(16,185,129,0.25)' }}
              >
                Mark Applied
              </button>
              <button
                onClick={() => handleStatus('skipped')}
                disabled={updating}
                className="px-4 py-2 rounded-xl text-sm font-medium text-neutral-500 disabled:opacity-40 transition-all"
                style={{ background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.06)' }}
              >
                Skip
              </button>
            </>
          )}
        </div>
      </motion.div>

      {/* Fit card */}
      {job.fit_score != null && <FitCard job={job} />}

      {/* Changes card */}
      <ChangesCard job={job} />

      {/* Split view */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="grid grid-cols-2 gap-5"
        style={{ minHeight: 500 }}
      >
        {/* Resume */}
        <div
          className="rounded-3xl overflow-hidden flex flex-col"
          style={{
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
            border: '1px solid rgba(255,255,255,0.9)',
          }}
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-black/[0.04]">
            <span className="text-sm font-semibold text-neutral-700">Resume (LaTeX)</span>
            {job.resume_latex && <CopyButton text={job.resume_latex} label="Copy .tex" />}
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <pre className="text-xs font-mono text-neutral-500 leading-relaxed whitespace-pre-wrap break-all">
              {job.resume_latex ?? 'No resume generated.'}
            </pre>
          </div>
        </div>

        {/* Cover letter */}
        <div
          className="rounded-3xl overflow-hidden flex flex-col"
          style={{
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
            border: '1px solid rgba(255,255,255,0.9)',
          }}
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-black/[0.04]">
            <span className="text-sm font-semibold text-neutral-700">Cover Letter</span>
            {job.cover_letter && <CopyButton text={job.cover_letter} label="Copy" />}
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <p className="text-sm text-neutral-600 leading-relaxed whitespace-pre-wrap">
              {job.cover_letter ?? 'No cover letter generated.'}
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
