'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, AccountExport } from '@/lib/api'
import { spring } from '@/lib/motion'

// ---- Account data export (Phase 6) ----
// One-shot async export: request → poll until ready → download. Lives on /profile
// next to ApiKeySettings — a rare, deliberate action, not part of the core loop.

export function AccountDataExport() {
  const [exportState, setExportState] = useState<AccountExport | null>(null)
  const [requesting, setRequesting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = (id: number) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getExportStatus(id)
        setExportState(status)
        if (status.status === 'ready' || status.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        // keep polling on transient network error
      }
    }, 2500)
  }

  const requestExport = async () => {
    setRequesting(true)
    setError(null)
    try {
      const created = await api.requestExport()
      setExportState(created)
      startPolling(created.id)
    } catch (e) {
      let detail = e instanceof Error ? e.message : 'Could not start export.'
      try {
        detail = JSON.parse(detail).detail ?? detail
      } catch { /* not JSON — show raw message */ }
      setError(detail)
    } finally {
      setRequesting(false)
    }
  }

  const download = async () => {
    if (!exportState) return
    try {
      await api.downloadExport(exportState.id)
    } catch {
      setError('Download failed. Try requesting a new export.')
    }
  }

  return (
    <div>
      <p className="text-sm font-semibold text-neutral-800 mb-1">Export your data</p>
      <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
        A zip of your profile, every generated resume and cover letter, and your application history.
      </p>

      {error && <p className="text-xs mb-3" style={{ color: 'var(--c-danger)' }}>{error}</p>}

      <AnimatePresence mode="wait" initial={false}>
        {!exportState || exportState.status === 'failed' ? (
          <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.snappy}>
            {exportState?.status === 'failed' && (
              <p className="text-xs mb-2" style={{ color: 'var(--c-danger)' }}>
                The last export failed. You can try again.
              </p>
            )}
            <button
              onClick={requestExport}
              disabled={requesting}
              className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
              style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
            >
              {requesting ? 'Starting…' : 'Request export'}
            </button>
          </motion.div>
        ) : exportState.status === 'processing' ? (
          <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.snappy}>
            <p className="text-xs text-neutral-400">
              Building your export — you&apos;ll get an email when it&apos;s ready. This page also updates automatically.
            </p>
          </motion.div>
        ) : (
          <motion.div key="ready" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.snappy} className="flex items-center gap-3">
            <button
              onClick={download}
              className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white transition-all"
              style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
            >
              Download export
            </button>
            <span className="text-xs text-neutral-400">Ready</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
