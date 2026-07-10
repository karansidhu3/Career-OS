'use client'

import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, PersonalInfo, extractErrorMessage } from '@/lib/api'
import { PrimaryButton } from '@/components/FormControls'
import { SectionLabel } from '@/components/SectionLabel'
import { TEMPLATE_CATALOG, NamedTemplate, PdfState, useTemplatePdfPreviews, TemplatePdfThumb, TemplatePreviewModal } from '@/components/TemplatePreview'

type TemplateChoice = NamedTemplate | 'custom'

const NAMED_IDS = TEMPLATE_CATALOG.map(t => t.id)

// Cards sit in a 3-col grid inside max-w-2xl — roughly 190 px wide.
const PDF_SCALE = 0.235               // 816 * 0.235 ≈ 192 px

export function TemplatePickerGate({
  personal,
  onComplete,
}: {
  personal: Omit<PersonalInfo, 'id'>
  onComplete: () => void
}) {
  const [selected, setSelected] = useState<TemplateChoice>('jake')
  const [saving, setSaving] = useState(false)

  const namedStates = useTemplatePdfPreviews(NAMED_IDS)

  const [customPreamble, setCustomPreamble] = useState('')
  const [customState, setCustomState] = useState<PdfState>({ url: null, loading: false, error: null })
  const [compiling, setCompiling] = useState(false)
  const [expanded, setExpanded] = useState<{ url: string; title: string } | null>(null)

  const blobUrls = useRef<string[]>([])

  const compileCustom = async () => {
    if (!customPreamble.trim()) return
    setCompiling(true)
    setCustomState({ url: null, loading: true, error: null })
    try {
      const url = await api.compileCustomTemplatePdf(customPreamble)
      blobUrls.current.push(url)
      setCustomState({ url, loading: false, error: null })
      setSelected('custom')
    } catch (e) {
      setCustomState({ url: null, loading: false, error: extractErrorMessage(e, 'Compilation failed') })
    } finally {
      setCompiling(false)
    }
  }

  const save = async () => {
    setSaving(true)
    try {
      await api.updatePersonal({
        ...personal,
        resume_template: selected,
        custom_preamble: selected === 'custom' ? customPreamble : null,
      })
      onComplete()
    } finally {
      setSaving(false)
    }
  }

  const canSave = selected !== 'custom' || customState.url !== null

  return (
    <div className="pt-16 max-w-2xl mx-auto px-4">
      <div className="text-center mb-3">
        <SectionLabel>Step 3 of 3</SectionLabel>
      </div>
      <h1
        className="text-2xl font-semibold mb-2 text-center"
        style={{ color: 'var(--color-neutral-900)' }}
      >
        Choose your resume format
      </h1>
      <p
        className="text-sm text-center mb-2 leading-relaxed"
        style={{ color: 'var(--color-neutral-600)' }}
      >
        Every format uses the same content underneath — this only changes how it&apos;s typeset.
        All six compile to a clean one-page PDF that passes ATS screening.
      </p>
      <p
        className="text-xs text-center mb-10"
        style={{ color: 'var(--color-neutral-700)' }}
      >
        You can change this any time in Settings.
      </p>

      {/* Named template cards */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        {TEMPLATE_CATALOG.map(t => {
          const active = selected === t.id
          return (
            <motion.div
              key={t.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(t.id)}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(t.id) } }}
              whileTap={{ scale: 0.98 }}
              className="flex flex-col rounded-xl overflow-hidden text-left cursor-pointer"
              style={{
                border: `1.5px solid ${active ? 'var(--c-accent)' : 'var(--c-border)'}`,
                background: active ? 'var(--c-glass-bg)' : 'transparent',
                transition: 'border-color 0.15s, background 0.15s',
              }}
            >
              <TemplatePdfThumb
                state={namedStates[t.id]}
                scale={PDF_SCALE}
                onExpand={namedStates[t.id].url ? () => setExpanded({ url: namedStates[t.id].url!, title: t.name }) : undefined}
              />
              <div
                className="px-3 py-3"
                style={{ borderTop: '1px solid var(--c-border)' }}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <p
                    className="text-sm font-semibold"
                    style={{ color: 'var(--color-neutral-900)' }}
                  >
                    {t.name}
                  </p>
                  {t.recommended && (
                    <span
                      className="text-[9px] font-medium uppercase tracking-[0.06em] px-1.5 py-0.5 rounded"
                      style={{ background: 'var(--c-accent-dim)', color: 'var(--color-neutral-800)' }}
                    >
                      Recommended
                    </span>
                  )}
                </div>
                <p
                  className="text-[11px] leading-snug"
                  style={{ color: 'var(--color-neutral-600)' }}
                >
                  {t.description}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Custom template card */}
      <div
        className="rounded-xl overflow-hidden mb-10"
        style={{
          border: `1.5px solid ${selected === 'custom' ? 'var(--c-accent)' : 'var(--c-border)'}`,
          background: selected === 'custom' ? 'var(--c-glass-bg)' : 'transparent',
          transition: 'border-color 0.15s, background 0.15s',
        }}
      >
        <button
          className="w-full flex items-center justify-between px-4 py-3 text-left"
          onClick={() => {
            if (selected !== 'custom') setSelected('custom')
          }}
        >
          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--color-neutral-900)' }}>
              Custom format
            </p>
            <p className="text-[11px]" style={{ color: 'var(--color-neutral-600)' }}>
              Paste your own LaTeX preamble — compiles and verifies before saving
            </p>
          </div>
          {selected !== 'custom' && (
            <span className="text-xs" style={{ color: 'var(--color-neutral-700)' }}>
              Use this
            </span>
          )}
        </button>

        <AnimatePresence initial={false}>
          {selected === 'custom' && (
            <motion.div
              key="custom-body"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.18 }}
              style={{ overflow: 'hidden' }}
            >
              <div
                className="px-4 pb-4"
                style={{ borderTop: '1px solid var(--c-border)' }}
              >
                <p
                  className="text-xs mt-3 mb-2 leading-relaxed"
                  style={{ color: 'var(--color-neutral-600)' }}
                >
                  Paste your full LaTeX preamble — everything from{' '}
                  <code className="font-mono">\documentclass</code> through the opening{' '}
                  <code className="font-mono">\begin&#123;document&#125;</code>. The generator
                  appends body sections and <code className="font-mono">\end&#123;document&#125;</code>.
                </p>
                <textarea
                  value={customPreamble}
                  onChange={e => setCustomPreamble(e.target.value)}
                  placeholder={'\\documentclass[letterpaper,11pt]{article}\n\\usepackage{...}\n% ... your preamble ...\n\\begin{document}'}
                  rows={10}
                  spellCheck={false}
                  className="w-full font-mono text-xs rounded-lg p-3 resize-y"
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--c-border)',
                    color: 'var(--color-neutral-900)',
                    outline: 'none',
                  }}
                />

                <div className="flex items-center gap-3 mt-3 flex-wrap">
                  <button
                    onClick={compileCustom}
                    disabled={compiling || !customPreamble.trim()}
                    className="px-4 py-2 text-sm rounded-lg font-medium transition-opacity disabled:opacity-40"
                    style={{
                      background: 'var(--c-accent)',
                      color: '#111110',
                    }}
                  >
                    {compiling ? 'Compiling…' : 'Compile & preview'}
                  </button>
                  {customState.error && (
                    <p className="text-xs" style={{ color: 'var(--c-danger)' }}>
                      {customState.error}
                    </p>
                  )}
                  {customState.url && !customState.error && (
                    <p className="text-xs" style={{ color: 'var(--c-success)' }}>
                      Compiled — select this format to save
                    </p>
                  )}
                </div>

                {customState.url && (
                  <div
                    className="mt-4 rounded-lg overflow-hidden"
                    style={{ border: '1px solid var(--c-border)' }}
                  >
                    <TemplatePdfThumb
                      state={customState}
                      scale={PDF_SCALE}
                      showTop={0.9}
                      onExpand={customState.url ? () => setExpanded({ url: customState.url!, title: 'Custom' }) : undefined}
                    />
                  </div>
                )}

                {selected === 'custom' && customState.url === null && (
                  <button
                    className="mt-3 text-xs underline"
                    style={{ color: 'var(--color-neutral-600)' }}
                    onClick={() => setSelected('jake')}
                  >
                    Back to standard formats
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex justify-center">
        <PrimaryButton onClick={save} disabled={saving || !canSave}>
          {saving
            ? 'Saving…'
            : !canSave
            ? 'Compile your template first'
            : 'Use this format'}
        </PrimaryButton>
      </div>

      <TemplatePreviewModal
        url={expanded?.url ?? null}
        title={expanded?.title ?? ''}
        onClose={() => setExpanded(null)}
      />
    </div>
  )
}
