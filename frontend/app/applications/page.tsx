'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { BrandMark } from '@/components/BrandMark'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'
import { relativeDate, parseStrategicNote } from '@/lib/utils'


// Status display labels — user-facing language, not internal state names
const STATUS_LABEL: Record<string, string> = {
  generated: 'Ready',
  applied:   'Applied',
  skipped:   'Skipped',
  interview: 'Interview',
  offer:     'Offer',
  new:       'New',
}

// Status text — CSS tokens where semantic color exists
const STATUS_TEXT: Record<string, string> = {
  generated: 'var(--c-accent)',
  applied:   'var(--c-success)',
  skipped:   '#9ca3af',
  interview: 'var(--c-warn)',
  offer:     'var(--c-warn)',
}

function scoreColor(score: number | null): string {
  if (score == null) return 'var(--c-border)'
  if (score >= 8) return 'var(--c-success)'
  if (score >= 6) return 'var(--c-warn)'
  return 'var(--c-danger)'
}

const FILTERS = ['all', 'generated', 'applied', 'interview', 'offer', 'skipped'] as const
type Filter = typeof FILTERS[number]

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

  // Signal: first gap bullet from structured analysis, or first sentence of prose fallback
  const signal = (() => {
    if (!job.strategic_note) return null
    const analysis = parseStrategicNote(job.strategic_note)
    if (analysis) return analysis.gaps[0] ?? analysis.goodFit[0] ?? null
    return job.strategic_note.split(/(?<=[.!?])\s+/)[0]?.replace(/[.!?]+$/, '').trim() ?? null
  })()

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

      {/* Title + signal */}
      <div className="flex-1 min-w-0">
        <p className="text-[13.5px] font-medium text-neutral-700 group-hover:text-neutral-900 truncate transition-colors leading-snug">
          {job.title}
          {job.company && (
            <span className="font-normal text-neutral-500"> · {job.company}</span>
          )}
        </p>
        {signal && (
          <p className="text-xs text-neutral-500 truncate mt-0.5 group-hover:text-neutral-600 transition-colors">
            {signal}
          </p>
        )}
      </div>

      {/* Score */}
      {job.fit_score != null && (
        <span
          className="text-xs font-mono font-semibold tabular-nums shrink-0"
          style={{ color: scoreColor(job.fit_score) }}
        >
          {job.fit_score}/10
        </span>
      )}

      {/* Status */}
      <span className="text-xs font-medium shrink-0" style={{ color: statusColor }}>
        {STATUS_LABEL[job.status] ?? job.status}
      </span>

      {/* Date */}
      <span className="text-xs text-neutral-500 font-mono tabular-nums shrink-0">
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
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...spring.bouncy, delay: 0.04 }}
          className="mb-4 text-neutral-600"
          style={{ opacity: 0.45 }}
        >
          <BrandMark size={28} physicalStroke={1.5} />
        </motion.div>
        <h1 className="text-3xl font-semibold text-neutral-900">Applications</h1>
        <p className="text-neutral-600 mt-1 text-sm">{jobs.length} total</p>

        {/* Filter tabs — only show tabs with items */}
        {jobs.length > 0 && (
          <div className="flex gap-1 mt-5 p-1 rounded-2xl w-fit" style={{ background: 'var(--c-surface)' }}>
            {FILTERS.map(f => {
              const count = f === 'all' ? jobs.length : jobs.filter(j => j.status === f).length
              if (count === 0 && f !== 'all') return null
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 capitalize ${
                    filter === f ? 'text-neutral-900' : 'text-neutral-500'
                  }`}
                  style={filter === f
                    ? { background: 'var(--c-surface-raised)', boxShadow: '0 1px 6px rgba(0,0,0,0.08)' }
                    : undefined
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
          className="text-center py-24 text-neutral-500 text-sm"
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
            <div
              className="mb-8"
              style={active.length > 0 ? { borderTop: '1px solid var(--c-border)', paddingTop: '1.5rem' } : undefined}
            >
              {(active.length > 0 || older.length > 0) && (
                <SectionLabel className="mb-3">This week</SectionLabel>
              )}
              <Rows jobs={recent} startIndex={active.length} />
            </div>
          )}

          {older.length > 0 && (
            <div
              style={active.length + recent.length > 0 ? { borderTop: '1px solid var(--c-border)', paddingTop: '1.5rem' } : undefined}
            >
              <SectionLabel className="mb-3">Earlier</SectionLabel>
              <Rows jobs={older} startIndex={active.length + recent.length} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
