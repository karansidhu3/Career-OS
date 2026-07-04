'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, CredentialStatus } from '@/lib/api'
import { spring } from '@/lib/motion'
import { Field, inputCls, inputStyle, CancelButton, SaveButton } from '@/components/FormControls'
import { SectionLabel } from '@/components/SectionLabel'

function SavedFlash() {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={spring.snappy}
      className="text-xs font-medium"
      style={{ color: 'var(--c-success)' }}
    >
      Saved ✓
    </motion.span>
  )
}

// ---- API key section (BYO Anthropic key) ----
// Shared between /profile (rare edits) and the home page's onboarding gate
// (new signup, before a key exists — see app/page.tsx's 'needs-key' state).

export function ApiKeySettings({ onSaved }: { onSaved?: (status: CredentialStatus) => void }) {
  const [status, setStatus] = useState<CredentialStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [keyInput, setKeyInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedFlash, setSavedFlash] = useState(false)

  const load = useCallback(async () => {
    try {
      setStatus(await api.getApiKeyStatus())
    } catch {
      // Silently leave status null — the empty state below reads fine either way
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await api.setApiKey(keyInput.trim())
      setStatus(updated)
      setKeyInput('')
      setEditing(false)
      setSavedFlash(true)
      onSaved?.(updated)
    } catch (e) {
      let detail = e instanceof Error ? e.message : 'Could not verify this key.'
      try {
        detail = JSON.parse(detail).detail ?? detail
      } catch { /* not JSON — show raw message */ }
      setError(detail)
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    setConfirmDelete(false)
    const previous = status
    setStatus({ provider: 'anthropic', has_key: false, key_hint: null, label: null, last_verified_at: null })
    try {
      await api.deleteApiKey()
    } catch {
      setStatus(previous)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionLabel>Anthropic API key</SectionLabel>
        <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
      </div>
      <p className="text-xs text-neutral-600 mb-4 leading-relaxed">
        Your own key, billed to you. CareerOS never sees or pays for your generation usage.
      </p>

      <AnimatePresence mode="wait">
        {loading ? (
          <div className="flex items-center justify-between" aria-hidden>
            <div>
              <div className="h-4 w-32 rounded skeleton-shimmer mb-2" />
              <div className="h-3 w-24 rounded skeleton-shimmer" />
            </div>
          </div>
        ) : editing || !status?.has_key ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <Field label="API key">
              <input
                type="password"
                value={keyInput}
                onChange={e => setKeyInput(e.target.value)}
                placeholder="sk-ant-..."
                className={inputCls}
                style={inputStyle}
                autoComplete="off"
              />
            </Field>
            {error && <p className="text-xs" style={{ color: 'var(--c-danger)' }}>{error}</p>}
            <div className="flex items-center justify-end gap-2 pt-1">
              {editing && (
                <CancelButton onClick={() => { setEditing(false); setError(null); setKeyInput('') }} />
              )}
              <SaveButton saving={saving} onClick={save} disabled={keyInput.trim().length < 10} savingLabel="Verifying…">
                Save key
              </SaveButton>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-mono text-neutral-700">sk-ant-••••{status.key_hint}</p>
                {status.last_verified_at && (
                  <p className="text-xs text-neutral-600 mt-1">
                    Verified {new Date(status.last_verified_at).toLocaleDateString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={() => setEditing(true)} className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
                  Update
                </button>
                <AnimatePresence mode="wait" initial={false}>
                  {!confirmDelete ? (
                    <motion.button
                      key="del"
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                      onClick={() => setConfirmDelete(true)}
                      className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
                    >
                      Remove
                    </motion.button>
                  ) : (
                    <motion.div
                      key="confirm"
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                      className="flex items-center gap-3"
                    >
                      <button onClick={remove} className="text-xs text-red-400 hover:text-red-600 transition-colors">
                        Confirm
                      </button>
                      <button onClick={() => setConfirmDelete(false)} className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
                        Cancel
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
