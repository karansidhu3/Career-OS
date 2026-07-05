'use client'

// ---- Shared result-view sections ----
// Previously defined independently in both app/page.tsx (the home result state)
// and app/jobs/[id]/page.tsx (the archive deep-link) — byte-identical in most
// cases, drifting silently in others. Both pages now import from here.

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, Job } from '@/lib/api'
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
      <span className="text-[10px] uppercase tracking-[0.12em] text-neutral-600 shrink-0">Emphasized</span>
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
          className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
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
              <pre className="text-xs font-mono text-neutral-600 leading-relaxed whitespace-pre-wrap break-all">
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
          <p className="text-xs text-neutral-600">PDF preview unavailable — download to view</p>
        </div>
      ) : !loaded && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
          <div className="flex flex-col items-center gap-3">
            <div className="w-6 h-6 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
            <p className="text-xs text-neutral-600">Compiling PDF…</p>
          </div>
        </div>
      )}
      {blobUrl && (
        <iframe
          // #toolbar=0&navpanes=0 suppresses Chrome's own native PDF viewer chrome —
          // without it, the browser renders its own toolbar (zoom, page count, its
          // own download button) directly on top of ResumeDownloadOverlay below.
          src={`${blobUrl}#toolbar=0&navpanes=0`}
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

// Icon-only download action — the single download affordance for both the
// resume and cover letter PDFs. Square, rounded, no label: the artifact sits
// right above it, so the action doesn't need to explain itself in words.
export function DownloadIconButton({
  onClick,
  downloading,
  downloaded = false,
  title = 'Download PDF',
}: {
  onClick: () => void
  downloading: boolean
  downloaded?: boolean
  title?: string
}) {
  return (
    <motion.button
      onClick={onClick}
      disabled={downloading}
      whileTap={{ scale: 0.93 }}
      title={title}
      aria-label={title}
      className="w-10 h-10 rounded-xl flex items-center justify-center text-white transition-all disabled:opacity-40"
      style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
    >
      {downloading ? (
        <div className="w-3.5 h-3.5 rounded-full animate-spin" style={{ border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white' }} />
      ) : downloaded ? (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      )}
    </motion.button>
  )
}

// Inline PDF preview for the cover letter — same visual treatment as
// ResumePreview so the two documents read as one format. Always self-fetches
// (unlike ResumePreview, the cover letter can be edited and recompiled in
// place — the caller remounts this via a changing `key` after a save to
// force a fresh fetch, rather than this component reacting to a version prop).
export function CoverLetterPreview({ jobId }: { jobId: number }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    api.fetchCoverLetterPdfPreview(jobId)
      .then(url => {
        if (cancelled) { URL.revokeObjectURL(url); return }
        objectUrl = url
        setBlobUrl(url)
      })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [jobId])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: loaded ? 1 : 0.35, y: 0 }}
      transition={{ ...spring.gentle, delay: 0.1 }}
      className="relative mb-4 rounded-sm overflow-hidden"
      style={{
        height: 880,
        boxShadow: '0 4px 32px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
        border: '1px solid var(--c-border)',
        background: '#fff',
      }}
    >
      {failed ? (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
          <p className="text-xs text-neutral-600">PDF preview unavailable — download to view</p>
        </div>
      ) : !loaded && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--c-surface)' }}>
          <div className="flex flex-col items-center gap-3">
            <div className="w-6 h-6 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
            <p className="text-xs text-neutral-600">Compiling PDF…</p>
          </div>
        </div>
      )}
      {blobUrl && (
        <iframe
          src={`${blobUrl}#toolbar=0&navpanes=0`}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          title="Cover letter"
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

// Full cover letter block — PDF preview (matching Resume's format) + a
// download icon button + a collapsible text editor underneath (same
// expand/collapse language as LatexSection's "LaTeX source" toggle). Shared
// between the home result state and the archive page, so both now support
// editing — previously only the home state did.
export function CoverLetterSection({ job, onSave }: { job: Job; onSave?: (updated: Job) => void }) {
  const [text, setText] = useState(job.cover_letter ?? '')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [previewVersion, setPreviewVersion] = useState(0)
  const [downloading, setDownloading] = useState(false)
  const [downloaded, setDownloaded] = useState(false)

  if (!job.cover_letter) return null

  const isDirty = text !== (job.cover_letter ?? '')

  const save = async () => {
    if (!text.trim()) return
    setSaving(true)
    try {
      const updated = await api.updateCoverLetter(job.id, text)
      onSave?.(updated)
      setSaved(true)
      setPreviewVersion(v => v + 1)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await api.downloadCoverLetterPdf(job.id, job.company)
      setDownloaded(true)
      setTimeout(() => setDownloaded(false), 2000)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <CoverLetterPreview key={previewVersion} jobId={job.id} />
      <div className="mb-6 flex items-center gap-3">
        <DownloadIconButton onClick={handleDownload} downloading={downloading} downloaded={downloaded} title="Download cover letter" />
        <button
          onClick={() => setEditing(v => !v)}
          className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
        >
          {editing ? 'Hide edit text ↑' : 'Edit text ↓'}
        </button>
      </div>
      <AnimatePresence>
        {editing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={spring.snappy}
            className="overflow-hidden"
          >
            <textarea
              value={text}
              onChange={e => { setText(e.target.value); setSaved(false) }}
              rows={12}
              className="w-full text-[15px] text-neutral-700 leading-[1.8] resize-none focus:outline-none rounded-xl p-4 mb-6"
              style={{
                background: 'var(--c-glass-bg)',
                border: '1px solid var(--c-glass-border)',
              }}
            />
            <div className="-mt-3 mb-6 flex items-center gap-4 flex-wrap">
              <CopyButton text={text} label="Copy" />
              {isDirty && (
                <button
                  onClick={save}
                  disabled={saving}
                  className="text-xs text-neutral-600 hover:text-neutral-700 disabled:opacity-40 transition-colors"
                >
                  {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save edits'}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
