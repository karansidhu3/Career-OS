'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { spring } from '@/lib/motion'

export type NamedTemplate = 'jake' | 'crisp' | 'modern' | 'sharp' | 'classic' | 'minimal'

export interface PdfState {
  url: string | null
  loading: boolean
  error: string | null
}

// Single source of truth for the 6 named templates — both the onboarding
// picker and the settings editor read from this so the catalog can't drift
// between the two surfaces.
export const TEMPLATE_CATALOG: { id: NamedTemplate; name: string; description: string; recommended?: boolean }[] = [
  {
    id: 'jake',
    name: 'Jake',
    description: 'Small-caps headers, divider rules, icon-linked contact. The most-used ATS format for CS roles.',
    recommended: true,
  },
  {
    id: 'crisp',
    name: 'Crisp',
    description: 'Centered name, pipe-separated contact row, bold section headers. Clean and readable.',
  },
  {
    id: 'modern',
    name: 'Modern',
    description: 'Palatino serif, bold small-caps section headers. Elegant — still fully ATS-safe.',
  },
  {
    id: 'sharp',
    name: 'Sharp',
    description: 'Sans-serif, bold section headers, minimal rule. Reads current and technical.',
  },
  {
    id: 'classic',
    name: 'Classic',
    description: 'Times serif, centered heading, heavier double-weight rule. Traditional and formal.',
  },
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'No dividing rules anywhere — hierarchy comes from weight and space alone.',
  },
]

// PDF letter page at 96 dpi ≈ 816 × 1056 px.
export const PDF_W = 816
export const PDF_H = 1056

// Each preview compiles a real PDF server-side via a Tectonic subprocess
// (~100-150MB RSS each). Fetching all of them at once — one person loading
// the template picker — used to spawn that many concurrent Tectonic
// processes and OOM the backend machine. Matches the server-side compile
// semaphore's limit of 2 (backend/app/services/pdf.py).
const PREVIEW_FETCH_CONCURRENCY = 2

/** Fetches a live compiled-PDF preview for each template id once on mount, cleaning up blob URLs on unmount. */
export function useTemplatePdfPreviews(templates: readonly NamedTemplate[]) {
  const [states, setStates] = useState<Record<string, PdfState>>(() =>
    Object.fromEntries(templates.map(t => [t, { url: null, loading: true, error: null }]))
  )
  const blobUrls = useRef<string[]>([])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      for (let i = 0; i < templates.length; i += PREVIEW_FETCH_CONCURRENCY) {
        if (cancelled) return
        const batch = templates.slice(i, i + PREVIEW_FETCH_CONCURRENCY)
        const results = await Promise.allSettled(batch.map(t => api.fetchTemplatePdfPreview(t)))
        if (cancelled) return
        results.forEach((r, j) => {
          const id = batch[j]
          if (r.status === 'fulfilled') {
            blobUrls.current.push(r.value)
            setStates(prev => ({ ...prev, [id]: { url: r.value, loading: false, error: null } }))
          } else {
            setStates(prev => ({ ...prev, [id]: { url: null, loading: false, error: 'Failed' } }))
          }
        })
      }
    }
    load()
    const urls = blobUrls.current
    return () => {
      cancelled = true
      urls.forEach(u => URL.revokeObjectURL(u))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- templates is static per mount site
  }, [])

  return states
}

function ExpandIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
    </svg>
  )
}

export function TemplatePdfThumb({
  state,
  scale,
  showTop = 0.75,
  onExpand,
}: {
  state: PdfState
  scale: number
  showTop?: number
  /** When provided, a hover-revealed expand affordance overlays the thumbnail and calls this instead of bubbling the click to the card. */
  onExpand?: () => void
}) {
  const height = Math.round(PDF_H * scale * showTop)
  if (state.loading) {
    return <div className="w-full skeleton" style={{ height }} />
  }
  if (!state.url) {
    return (
      <div
        className="w-full flex items-center justify-center text-xs"
        style={{ height, color: 'var(--color-neutral-600)' }}
      >
        {state.error ? 'Preview unavailable' : '—'}
      </div>
    )
  }
  return (
    <div className="group" style={{ overflow: 'hidden', height, position: 'relative', width: '100%' }}>
      <iframe
        src={`${state.url}#toolbar=0&navpanes=0&scrollbar=0`}
        title="Resume preview"
        tabIndex={-1}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: PDF_W,
          height: PDF_H,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
          border: 'none',
          pointerEvents: 'none',
        }}
      />
      {onExpand && (
        <button
          onClick={e => { e.stopPropagation(); onExpand() }}
          aria-label="View full size"
          className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ background: 'rgba(0,0,0,0.45)' }}
        >
          <span
            className="flex items-center justify-center rounded-full"
            style={{ width: 34, height: 34, background: 'var(--c-accent)', color: '#111110' }}
          >
            <ExpandIcon />
          </span>
        </button>
      )}
    </div>
  )
}

/** Full-size modal preview — the elevated plane: backdrop blur, own shadow, and the content behind it becomes non-interactive while open. */
export function TemplatePreviewModal({
  url,
  title,
  onClose,
}: {
  url: string | null
  title: string
  onClose: () => void
}) {
  useEffect(() => {
    if (!url) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [url, onClose])

  return (
    <AnimatePresence>
      {url && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={spring.snappy}
          className="fixed inset-0 z-[100] flex items-center justify-center p-6"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={spring.standard}
            className="relative rounded-xl overflow-hidden flex flex-col"
            style={{
              width: 'min(92vw, 720px)',
              height: 'min(90vh, 960px)',
              background: 'var(--c-surface-overlay)',
              border: '1px solid var(--c-border)',
              boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div
              className="flex items-center justify-between px-4 py-3 shrink-0"
              style={{ borderBottom: '1px solid var(--c-border)' }}
            >
              <p className="text-sm font-semibold" style={{ color: 'var(--color-neutral-900)' }}>{title}</p>
              <button
                onClick={onClose}
                aria-label="Close"
                className="text-neutral-600 hover:text-neutral-900 transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <iframe
              src={`${url}#toolbar=0`}
              title={title}
              className="flex-1 w-full"
              style={{ border: 'none' }}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
