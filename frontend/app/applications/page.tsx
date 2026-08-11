'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { api, Job } from '@/lib/api'
import { BrandMark } from '@/components/BrandMark'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'
import { normalizeFitScore, relativeDate, parseStrategicNote } from '@/lib/utils'


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
  skipped:   'var(--color-neutral-500)',
  interview: 'var(--c-warn)',
  offer:     'var(--c-warn)',
}

function scoreColor(score: number | null): string {
  if (score == null) return 'var(--color-neutral-500)'
  if (score >= 8) return 'var(--c-success)'
  if (score >= 6) return 'var(--c-warn)'
  return 'var(--c-danger)'
}

const FILTERS = ['all', 'generated', 'applied', 'interview', 'offer', 'skipped'] as const
type Filter = typeof FILTERS[number]

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000

function groupJobs(jobs: Job[]) {
  const now = Date.now()
  const sevenDays = 7 * 24 * 60 * 60 * 1000

  const active: Job[] = []
  const recent: Job[] = []
  const older: Job[] = []
  const stale: Job[] = []

  for (const job of jobs) {
    if (job.status === 'interview' || job.status === 'offer') {
      active.push(job)
      continue
    }
    const age = job.created_at ? now - new Date(job.created_at).getTime() : Infinity
    if (age < sevenDays) {
      recent.push(job)
    } else if (job.status === 'applied' && age > THIRTY_DAYS) {
      stale.push(job)
    } else {
      older.push(job)
    }
  }

  return { active, recent, older, stale }
}

// ─── Row ─────────────────────────────────────────────────────────

function AppRow({ job, i }: { job: Job; i: number }) {
  const router = useRouter()
  const isSpecial = job.status === 'interview' || job.status === 'offer'
  const statusColor = STATUS_TEXT[job.status] ?? 'var(--color-neutral-500)'
  const fitScore = job.fit_score == null ? null : normalizeFitScore(job.fit_score)

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
      className="w-full text-left flex items-center gap-3 -mx-3 px-3 py-3.5 rounded-xl group transition-colors hover:bg-[var(--c-icon-hover)]"
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
            <span className="font-normal text-neutral-600"> · {job.company}</span>
          )}
        </p>
        {signal && (
          <p className="text-xs text-neutral-600 truncate mt-0.5 group-hover:text-neutral-700 transition-colors">
            {signal}
          </p>
        )}
      </div>

      {/* Score */}
      {fitScore != null && (
        <span
          className="text-xs font-mono font-semibold tabular-nums shrink-0"
          style={{ color: scoreColor(fitScore) }}
        >
          {fitScore}/10
        </span>
      )}

      {/* Status */}
      <span className="text-xs font-medium shrink-0" style={{ color: statusColor }}>
        {STATUS_LABEL[job.status] ?? job.status}
      </span>

      {/* Date */}
      <span className="text-xs text-neutral-600 font-mono tabular-nums shrink-0">
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

// ─── Loading skeleton — mirrors the real layout so nothing reflows on arrival ──

function ApplicationsSkeleton() {
  return (
    <div className="pointer-events-none" aria-hidden>
      <div className="flex gap-1 mb-8 mt-5">
        <div className="h-7 w-14 rounded-xl skeleton-shimmer" />
        <div className="h-7 w-20 rounded-xl skeleton-shimmer" />
        <div className="h-7 w-16 rounded-xl skeleton-shimmer" />
      </div>
      <div className="h-3 w-16 rounded skeleton-shimmer mb-4" />
      {[68, 52, 61, 45].map((w, i) => (
        <div key={i} className="flex items-center justify-between py-3.5" style={i < 3 ? { borderBottom: '1px solid var(--c-border)' } : undefined}>
          <div className="flex-1 min-w-0">
            <div className="h-3.5 rounded skeleton-shimmer mb-2" style={{ width: `${w}%` }} />
            <div className="h-3 w-1/3 rounded skeleton-shimmer" />
          </div>
          <div className="shrink-0 flex items-center gap-4 ml-4">
            <div className="h-3 w-8 rounded skeleton-shimmer" />
            <div className="h-3 w-12 rounded skeleton-shimmer" />
            <div className="h-3 w-10 rounded skeleton-shimmer" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loaded, setLoaded] = useState(false)
  const [filter, setFilter] = useState<Filter>('all')
  const [showStale, setShowStale] = useState(false)
  const [query, setQuery] = useState('')

  const load = useCallback(async () => {
    try { setJobs(await api.listJobs()) }
    catch { /* offline */ }
    finally { setLoaded(true) }
  }, [])

  useEffect(() => { load() }, [load])

  const q = query.trim().toLowerCase()
  const statusFiltered = filter === 'all' ? jobs : jobs.filter(j => j.status === filter)
  const filtered = q
    ? statusFiltered.filter(j => j.title?.toLowerCase().includes(q) || j.company?.toLowerCase().includes(q))
    : statusFiltered
  const isNarrowed = filter !== 'all' || q.length > 0
  const { active, recent, older, stale } = groupJobs(jobs)

  return (
    <div className="px-6 pb-24 max-w-3xl mx-auto">
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
          className="mb-4"
        >
          <span className="brand-ring-glow-cool text-neutral-900">
            <BrandMark size={28} physicalStroke={1.5} />
          </span>
        </motion.div>
        <h1 className="text-3xl font-semibold text-neutral-900">Applications</h1>
        {loaded ? (
          <p className="text-neutral-600 mt-1 text-sm">{jobs.length} total</p>
        ) : (
          <div className="h-4 w-16 rounded skeleton-shimmer mt-2" aria-hidden />
        )}

        {/* Filter tabs + search — only once there's something to filter/search */}
        {loaded && jobs.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 mt-5">
            <div className="flex gap-1 p-1 rounded-2xl w-fit" style={{ background: 'var(--c-surface)' }}>
              {FILTERS.map(f => {
                const count = f === 'all' ? jobs.length : jobs.filter(j => j.status === f).length
                if (count === 0 && f !== 'all') return null
                return (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 capitalize ${
                      filter === f ? 'text-neutral-900' : 'text-neutral-600'
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

            <div className="relative w-full sm:w-56">
              <svg
                width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500 pointer-events-none"
              >
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search applications…"
                className="h-8 w-full pl-8 pr-7 rounded-xl text-xs text-neutral-700 placeholder-neutral-400 focus:outline-none"
                style={{ background: 'var(--c-surface)' }}
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-700 transition-colors"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        )}
      </motion.div>

      {!loaded ? (
        <ApplicationsSkeleton />
      ) : filtered.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-24 text-neutral-600 text-sm"
        >
          {jobs.length === 0
            ? 'No applications yet. Go to Home and paste a job description.'
            : q
            ? `No results for "${query.trim()}".`
            : `No ${filter} applications.`}
        </motion.div>
      ) : isNarrowed ? (
        // Flat filtered/searched list
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

          {stale.length > 0 && (
            <div
              style={{
                borderTop: '1px solid var(--c-border)',
                paddingTop: '0.75rem',
                marginTop: older.length > 0 ? '0.5rem' : active.length + recent.length > 0 ? '1.5rem' : undefined,
              }}
            >
              {showStale ? (
                <div style={{ opacity: 0.45 }}>
                  <div className="flex items-center justify-between mb-3">
                    <SectionLabel>Older applied</SectionLabel>
                    <button
                      onClick={() => setShowStale(false)}
                      className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                    >
                      hide
                    </button>
                  </div>
                  <Rows jobs={stale} startIndex={active.length + recent.length + older.length} />
                </div>
              ) : (
                <button
                  onClick={() => setShowStale(true)}
                  className="w-full text-left py-2 text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                >
                  {stale.length} older applied {stale.length === 1 ? 'application' : 'applications'} — likely no response
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
