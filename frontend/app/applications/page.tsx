'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'
import { relativeDate } from '@/lib/utils'

// Status text — CSS tokens where semantic color exists
const STATUS_TEXT: Record<string, string> = {
  generated: '#7c3aed',
  applied:   'var(--c-success)',
  skipped:   '#9ca3af',
  interview: 'var(--c-warn)',
  offer:     'var(--c-warn)',
}

const FILTERS = ['all', 'generated', 'applied', 'interview', 'offer', 'skipped'] as const
type Filter = typeof FILTERS[number]

function fitColor(score: number | null | undefined): string {
  if (score == null) return '#9ca3af'
  if (score >= 8) return 'var(--c-success)'
  if (score >= 6) return 'var(--c-warn)'
  return 'var(--c-danger)'
}

function groupJobs(jobs: Job[]) {
  const now = Date.now()
  const sevenDays = 7 * 24 * 60 * 60 * 1000

  const active: Job[] = []
  const recent: Job[] = []
  const older: Job[] = []

  for (const job of jobs) {
    if (job.status === 'interview' || job.status === 'offer') {
      active.push(job)
      continue
    }
    const age = job.created_at ? now - new Date(job.created_at).getTime() : Infinity
    if (age < sevenDays) recent.push(job)
    else older.push(job)
  }

  return { active, recent, older }
}

// ─── Row ─────────────────────────────────────────────────────────

function AppRow({ job, i }: { job: Job; i: number }) {
  const router = useRouter()
  const isSpecial = job.status === 'interview' || job.status === 'offer'
  const statusColor = STATUS_TEXT[job.status] ?? '#9ca3af'

  return (
    <motion.button
      onClick={() => router.push(`/jobs/${job.id}`)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...spring.standard, delay: i * 0.025 }}
      className="w-full text-left flex items-center gap-3 py-3.5 group transition-colors"
    >
      {/* Active status marker */}
      <div
        className="shrink-0 w-1.5 h-1.5 rounded-full"
        style={{ background: isSpecial ? 'var(--c-warn)' : 'transparent' }}
      />

      {/* Title + company */}
      <div className="flex-1 min-w-0">
        <p className="text-[13.5px] font-medium text-neutral-700 group-hover:text-neutral-900 truncate transition-colors leading-snug">
          {job.title}
        </p>
        {job.company && (
          <p className="text-xs text-neutral-400 truncate mt-0.5">{job.company}</p>
        )}
      </div>

      {/* Fit score */}
      {job.fit_score != null && (
        <span
          className="text-xs font-semibold shrink-0 tabular-nums"
          style={{ color: fitColor(job.fit_score) }}
        >
          {job.fit_score}/10
        </span>
      )}

      {/* Status */}
      <span className="text-xs font-medium shrink-0 capitalize" style={{ color: statusColor }}>
        {job.status}
      </span>

      {/* Date */}
      <span className="text-xs text-neutral-300 shrink-0">
        {job.created_at ? relativeDate(job.created_at) : ''}
      </span>
    </motion.button>
  )
}

function Rows({ jobs, startIndex = 0 }: { jobs: Job[]; startIndex?: number }) {
  return (
    <div>
      {jobs.map((job, i) => (
        <div
          key={job.id}
          style={i < jobs.length - 1 ? { borderBottom: '1px solid var(--c-border)' } : undefined}
        >
          <AppRow job={job} i={i + startIndex} />
        </div>
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [filter, setFilter] = useState<Filter>('all')

  const load = useCallback(async () => {
    try { setJobs(await api.listJobs()) } catch { /* offline */ }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = filter === 'all' ? jobs : jobs.filter(j => j.status === filter)
  const { active, recent, older } = groupJobs(jobs)

  return (
    <div className="px-6 pb-24 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="pt-10 mb-6"
      >
        <h1 className="text-3xl font-semibold text-neutral-900">Applications</h1>
        <p className="text-neutral-400 mt-1 text-sm">{jobs.length} total</p>

        {/* Filter tabs — only show tabs with items */}
        {jobs.length > 0 && (
          <div className="flex gap-1 mt-5 p-1 rounded-2xl w-fit" style={{ background: 'rgba(0,0,0,0.04)' }}>
            {FILTERS.map(f => {
              const count = f === 'all' ? jobs.length : jobs.filter(j => j.status === f).length
              if (count === 0 && f !== 'all') return null
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className="px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 capitalize"
                  style={filter === f
                    ? { background: '#fff', color: '#1c1c1e', boxShadow: '0 1px 6px rgba(0,0,0,0.08)' }
                    : { color: '#9ca3af' }
                  }
                >
                  {f} <span className="opacity-50">{count}</span>
                </button>
              )
            })}
          </div>
        )}
      </motion.div>

      {filtered.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-24 text-neutral-300 text-sm"
        >
          {jobs.length === 0
            ? 'No applications yet. Go to Home and paste a job description.'
            : `No ${filter} applications.`}
        </motion.div>
      ) : filter !== 'all' ? (
        // Flat filtered list
        <Rows jobs={filtered} />
      ) : (
        // Grouped timeline
        <>
          {active.length > 0 && (
            <div className="mb-8">
              <SectionLabel className="mb-3" style={{ color: 'var(--c-warn)' }}>Active</SectionLabel>
              <Rows jobs={active} startIndex={0} />
            </div>
          )}

          {recent.length > 0 && (
            <div className="mb-8">
              {(active.length > 0 || older.length > 0) && (
                <SectionLabel className="mb-3">This week</SectionLabel>
              )}
              <Rows jobs={recent} startIndex={active.length} />
            </div>
          )}

          {older.length > 0 && (
            <div>
              <SectionLabel className="mb-3">Earlier</SectionLabel>
              <Rows jobs={older} startIndex={active.length + recent.length} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
