'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { api, Job } from '@/lib/api'

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  generated: { bg: 'rgba(139,92,246,0.08)', text: '#7c3aed' },
  applied:   { bg: 'rgba(16,185,129,0.08)',  text: '#059669' },
  skipped:   { bg: 'rgba(0,0,0,0.04)',       text: '#9ca3af' },
  interview: { bg: 'rgba(59,130,246,0.08)',  text: '#2563eb' },
  offer:     { bg: 'rgba(245,158,11,0.08)',  text: '#d97706' },
}

export default function ApplicationsPage() {
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])

  const load = useCallback(async () => {
    try { setJobs(await api.listJobs()) } catch { /* offline */ }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="px-6 pb-24 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.23, 1, 0.32, 1] }}
        className="pt-10 mb-8"
      >
        <h1 className="text-3xl font-semibold text-neutral-900">Applications</h1>
        <p className="text-neutral-400 mt-1">{jobs.length} total</p>
      </motion.div>

      {jobs.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-24 text-neutral-300 text-sm"
        >
          No applications yet. Go to Home and paste a job description.
        </motion.div>
      ) : (
        <div className="grid gap-3">
          {jobs.map((job, i) => {
            const c = STATUS_COLORS[job.status] ?? STATUS_COLORS.generated
            const score = job.fit_score
            const scoreColor = score == null ? '#9ca3af' : score >= 8 ? '#059669' : score >= 6 ? '#d97706' : '#dc2626'

            return (
              <motion.button
                key={job.id}
                onClick={() => router.push(`/jobs/${job.id}`)}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04, duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
                whileHover={{ y: -2 }}
                className="text-left w-full px-6 py-5 rounded-2xl flex items-center gap-4 transition-shadow duration-200"
                style={{
                  background: 'rgba(255,255,255,0.85)',
                  border: '1px solid rgba(255,255,255,0.9)',
                  boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
                }}
              >
                {/* Company avatar */}
                <div
                  style={{ background: 'linear-gradient(135deg, #e0e7ff, #ede9fe)' }}
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                >
                  <span className="text-indigo-600 font-semibold text-sm">
                    {(job.company ?? job.title)[0]?.toUpperCase() ?? '?'}
                  </span>
                </div>

                {/* Title + company */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-neutral-800 truncate">{job.title}</p>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">{job.company ?? '—'}</p>
                </div>

                {/* Score */}
                {score != null && (
                  <span className="text-sm font-semibold shrink-0" style={{ color: scoreColor }}>
                    {score}/10
                  </span>
                )}

                {/* Status */}
                <span
                  className="text-xs font-medium px-2.5 py-1 rounded-full shrink-0 capitalize"
                  style={{ background: c.bg, color: c.text }}
                >
                  {job.status}
                </span>

                {/* Date */}
                <span className="text-xs text-neutral-300 shrink-0">
                  {job.created_at ? new Date(job.created_at).toLocaleDateString() : ''}
                </span>
              </motion.button>
            )
          })}
        </div>
      )}
    </div>
  )
}
