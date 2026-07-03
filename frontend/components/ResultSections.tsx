'use client'

// ---- Shared result-view sections ----
// Previously defined independently in both app/page.tsx (the home result state)
// and app/jobs/[id]/page.tsx (the archive deep-link) — byte-identical in most
// cases, drifting silently in others. Both pages now import from here.

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { CopyButton } from '@/components/CopyButton'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'

export function AnalysisSection({ title, bullets, color }: { title: string; bullets: string[]; color?: string }) {
  if (!bullets.length) return null
  return (
    <div>
      <SectionLabel className="mb-2" style={color ? { color } : undefined}>{title}</SectionLabel>
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

export function SelectedProjectsBar({ projects }: { projects: string[] }) {
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

export function LatexSection({ latex }: { latex: string }) {
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

// Draws from left on mount.
export function Divider({ delay = 0 }: { delay?: number }) {
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

// Inline PDF preview — the actual artifact. Accepts either external blob state
// (passed from a parent that already fetched it, e.g. the home result state)
// or manages its own internal fetch (standalone use, e.g. the archive page).
export function ResumePreview({
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

// Floating download-PDF affordance overlaid on the top-right corner of
// ResumePreview — same treatment on the home result state and the archive page.
export function ResumeDownloadOverlay({
  onDownload,
  downloading,
  downloaded = false,
  label = 'Download PDF',
  downloadedLabel = 'Saved ✓',
}: {
  onDownload: () => void
  downloading: boolean
  downloaded?: boolean
  label?: string
  downloadedLabel?: string
}) {
  return (
    <div className="absolute top-3 right-3 z-10">
      <motion.button
        onClick={onDownload}
        disabled={downloading}
        whileTap={{ scale: 0.97 }}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
        style={{ background: 'rgba(24,24,27,0.72)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
      >
        {downloading ? 'Compiling…' : downloaded ? downloadedLabel : label}
      </motion.button>
    </div>
  )
}
