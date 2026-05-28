'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { api, Job } from '@/lib/api'

const ease = 'easeOut'
const ESTIMATED_SECONDS = 18

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  generated: { bg: 'rgba(139,92,246,0.08)', text: '#7c3aed' },
  applied:   { bg: 'rgba(16,185,129,0.08)', text: '#059669' },
  skipped:   { bg: 'rgba(0,0,0,0.04)',      text: '#9ca3af' },
  interview: { bg: 'rgba(59,130,246,0.08)', text: '#2563eb' },
  offer:     { bg: 'rgba(245,158,11,0.08)', text: '#d97706' },
}

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.generated
  return (
    <span style={{ background: c.bg, color: c.text }} className="text-xs font-medium px-2 py-0.5 rounded-full capitalize">
      {status}
    </span>
  )
}

function CompanyAvatar({ name }: { name: string | null }) {
  return (
    <div style={{ background: 'linear-gradient(135deg, #e0e7ff, #ede9fe)' }} className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0">
      <span className="text-indigo-600 font-semibold text-sm">{(name ?? '?')[0]?.toUpperCase()}</span>
    </div>
  )
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 8 ? '#10b981' : score >= 6 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-1">
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      <span style={{ color }} className="text-xs font-semibold">{score}/10</span>
    </div>
  )
}

export default function Home() {
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Restore JD from sessionStorage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem('careeros-jd')
    if (saved) setJd(saved)
  }, [])

  const handleJdChange = (value: string) => {
    setJd(value)
    sessionStorage.setItem('careeros-jd', value)
  }

  // Elapsed timer while generating
  useEffect(() => {
    if (loading) {
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [loading])

  const loadJobs = useCallback(async () => {
    try { setJobs(await api.listJobs()) } catch { /* backend offline */ }
  }, [])

  useEffect(() => { loadJobs() }, [loadJobs])

  const thisWeek = jobs.filter((j) => {
    if (!j.created_at) return false
    return Date.now() - new Date(j.created_at).getTime() < 7 * 24 * 60 * 60 * 1000
  }).length

  const handleGenerate = async () => {
    if (!jd.trim()) return
    setLoading(true)
    setError(null)
    try {
      const job = await api.generate({ description: jd.trim() })
      sessionStorage.removeItem('careeros-jd')
      router.push(`/jobs/${job.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed. Is the backend running?')
      setLoading(false)
    }
  }

  const progress = Math.min((elapsed / ESTIMATED_SECONDS) * 100, 96)
  const recentJobs = jobs.slice(0, 6)

  return (
    <div className="px-6 pb-24 max-w-4xl mx-auto">

      {/* Hero */}
      <section className="pt-16 pb-12 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease }}
          className="text-5xl font-semibold tracking-tight text-neutral-900"
        >
          {getGreeting()}, Karan.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.08, ease }}
          className="mt-3 text-lg text-neutral-400"
        >
          {thisWeek > 0
            ? `You've generated ${thisWeek} application${thisWeek !== 1 ? 's' : ''} this week.`
            : 'Paste a job description below to generate tailored materials.'}
        </motion.p>
      </section>

      {/* Paste card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.14, ease }}
      >
        <div
          style={{
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            boxShadow: '0 8px 40px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
            border: '1px solid rgba(255,255,255,0.9)',
          }}
          className="rounded-3xl p-8"
        >
          <h2 className="text-lg font-semibold text-neutral-800 mb-5">Paste Job Description</h2>

          <textarea
            value={jd}
            onChange={e => handleJdChange(e.target.value)}
            placeholder="Paste the full job description here — Claude will extract the role, score the fit, and generate a tailored resume + cover letter in ~18 seconds."
            rows={8}
            disabled={loading}
            className="w-full resize-none rounded-2xl text-sm text-neutral-700 placeholder-neutral-300 p-4 focus:outline-none focus:ring-2 focus:ring-indigo-100 leading-relaxed disabled:opacity-50"
            style={{ background: 'rgba(0,0,0,0.025)', border: '1px solid rgba(0,0,0,0.06)' }}
          />

          {error && (
            <p className="mt-3 text-sm text-red-500 bg-red-50 px-4 py-2.5 rounded-xl">{error}</p>
          )}

          <div className="mt-5 space-y-3">
            <button
              onClick={handleGenerate}
              disabled={loading || !jd.trim()}
              className="w-full py-3 rounded-2xl text-sm font-semibold text-white transition-all duration-200 disabled:opacity-40 flex items-center justify-center gap-2"
              style={{
                background: loading ? '#a5b4fc' : 'linear-gradient(135deg, #818cf8, #7c3aed)',
                boxShadow: loading ? 'none' : '0 4px 16px rgba(129,140,248,0.35)',
              }}
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Generating… {elapsed}s
                </>
              ) : (
                'Generate Materials →'
              )}
            </button>

            {/* Progress bar */}
            {loading && (
              <div className="w-full rounded-full overflow-hidden" style={{ height: 3, background: 'rgba(0,0,0,0.06)' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'linear-gradient(90deg, #818cf8, #7c3aed)' }}
                  initial={{ width: '0%' }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 1, ease: 'linear' }}
                />
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Recent applications */}
      {recentJobs.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.2, ease }}
          className="mt-12"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">
              Recent Applications
            </h2>
            <button
              onClick={() => router.push('/applications')}
              className="text-xs text-indigo-400 hover:text-indigo-600 transition-colors"
            >
              View all →
            </button>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1">
            {recentJobs.map((job, i) => (
              <motion.button
                key={job.id}
                onClick={() => router.push(`/jobs/${job.id}`)}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.24 + i * 0.05, duration: 0.4, ease }}
                whileHover={{ y: -3 }}
                className="shrink-0 w-56 text-left p-5 rounded-2xl cursor-pointer"
                style={{
                  background: 'rgba(255,255,255,0.9)',
                  border: '1px solid rgba(255,255,255,0.9)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.05)',
                }}
              >
                <CompanyAvatar name={job.company} />
                <p className="mt-3 text-sm font-semibold text-neutral-800 truncate">{job.title}</p>
                <p className="text-xs text-neutral-400 truncate mt-0.5">{job.company ?? '—'}</p>
                <div className="flex items-center justify-between mt-3">
                  <StatusBadge status={job.status} />
                  {job.fit_score != null && <ScoreRing score={job.fit_score} />}
                </div>
              </motion.button>
            ))}
          </div>
        </motion.section>
      )}
    </div>
  )
}
