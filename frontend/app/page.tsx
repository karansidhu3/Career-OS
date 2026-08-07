'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useUser } from '@clerk/nextjs'
import { motion, AnimatePresence } from 'framer-motion'
import { api, CandidacyInsights, Job } from '@/lib/api'
import { ApiKeySettings } from '@/components/ApiKeySettings'
import { LandingPage } from '@/components/LandingPage'
import { ProfileSetupGate } from '@/components/ProfileSetupGate'
import { TemplatePickerGate } from '@/components/TemplatePickerGate'
import { AutoTextarea } from '@/components/AutoTextarea'
import { BrandMark } from '@/components/BrandMark'
import { SectionLabel } from '@/components/SectionLabel'
import { EmptyProfileNudge } from '@/components/EmptyProfileNudge'
import { ScoreRing } from '@/components/ScoreRing'
import { AnalysisSection, SelectedProjectsBar, LatexSection, Divider, ResumePreview, DownloadIconButton, CoverLetterSection } from '@/components/ResultSections'
import { spring } from '@/lib/motion'
import { parseStrategicNote } from '@/lib/utils'

// ─── Types ──────────────────────────────────────────────────────────────────

type AppState =
  | { mode: 'checking' }
  | { mode: 'needs-key' }
  | { mode: 'needs-profile' }
  | { mode: 'needs-template'; personal: NonNullable<import('@/lib/api').FullProfile['personal']> }
  | { mode: 'idle' }
  | { mode: 'generating'; jobId: number }
  | { mode: 'result'; job: Job }
  | { mode: 'error'; jobId?: number; message: string }

// Dev-only escape hatch: lets a local checkout skip the "add a billed
// Anthropic key" gate to look at the idle screen without spending real
// money. Hard-gated on NODE_ENV so a leaked env var can never activate this
// on a real deployment — Generate will still fail without a real key, since
// this only affects which screen renders, not what the backend accepts.
const DEV_SKIP_KEY_GATE =
  process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_DEV_SKIP_KEY_GATE === 'true'

// ─── Helpers ────────────────────────────────────────────────────────────────

function getGenMessage(elapsed: number): string {
  if (elapsed < 14) return 'Generating your application…'
  if (elapsed < 32) return 'Matching your background to this role…'
  return 'Finishing your resume…'
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StatusActions({ job, onUpdate }: { job: Job; onUpdate: (j: Job) => void }) {
  const [updating, setUpdating] = useState<string | null>(null)

  const mark = async (status: string) => {
    setUpdating(status)
    try {
      const updated = await api.updateStatus(job.id, status)
      onUpdate(updated)
    } finally {
      setUpdating(null)
    }
  }

  if (job.status === 'interview' || job.status === 'offer') {
    return (
      <span className="text-xs font-medium" style={{ color: 'var(--c-warn)' }}>
        {job.status === 'offer' ? 'Offer received' : 'Interview stage'}
      </span>
    )
  }

  if (job.status === 'applied') {
    return (
      <button
        onClick={() => mark('interview')}
        disabled={!!updating}
        className="text-xs text-neutral-600 hover:text-neutral-700 disabled:opacity-40 transition-colors"
      >
        {updating === 'interview' ? 'Saving…' : 'Got interview'}
      </button>
    )
  }

  // generated / default
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => mark('applied')}
        disabled={!!updating}
        className="text-xs font-medium hover:opacity-70 disabled:opacity-40 transition-opacity"
        style={{ color: 'var(--c-success)' }}
      >
        {updating === 'applied' ? 'Saving…' : 'Mark applied'}
      </button>
      <button
        onClick={() => mark('interview')}
        disabled={!!updating}
        className="text-xs text-neutral-600 hover:text-neutral-700 disabled:opacity-40 transition-colors"
      >
        {updating === 'interview' ? 'Saving…' : 'Got interview'}
      </button>
    </div>
  )
}

// ─── Selected projects bar — verify what the AI chose ────────────────────────

// ─── Generating skeleton — ghost of what's being built ──────────────────────

function GeneratingSkeleton() {
  return (
    <div className="w-full mt-14 pointer-events-none" aria-hidden>
      <div className="opacity-[0.12]">
        {/* Title */}
        <div className="h-9 w-[52%] rounded-lg skeleton-shimmer mb-2.5" />
        {/* Company */}
        <div className="h-4 w-[22%] rounded skeleton-shimmer mb-2.5" />
        {/* Fit score */}
        <div className="h-3 w-[10%] rounded skeleton-shimmer mb-8" />
        {/* Divider */}
        <div className="h-px w-full skeleton-shimmer mb-8" />
        {/* Good fit */}
        <div className="mb-7">
          <div className="h-2 w-14 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[68%] rounded skeleton-shimmer" />
            <div className="h-3.5 w-[54%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Gaps */}
        <div className="mb-7">
          <div className="h-2 w-8 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[61%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Improvement plan */}
        <div className="mb-8">
          <div className="h-2 w-24 rounded skeleton-shimmer mb-3" />
          <div className="space-y-2">
            <div className="h-3.5 w-[72%] rounded skeleton-shimmer" />
            <div className="h-3.5 w-[48%] rounded skeleton-shimmer" />
          </div>
        </div>
        {/* Emphasized pills */}
        <div className="flex items-center gap-2 mb-6">
          <div className="h-2 w-16 rounded skeleton-shimmer" />
          <div className="h-5 w-24 rounded-full skeleton-shimmer" />
          <div className="h-5 w-20 rounded-full skeleton-shimmer" />
          <div className="h-5 w-28 rounded-full skeleton-shimmer" />
        </div>
        {/* PDF ghost */}
        <div className="h-[360px] rounded-sm skeleton-shimmer" />
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Home() {
  // / is public now (Phase 8, proxy.ts) — a signed-out visitor lands here and
  // sees the waitlist page instead of the core loop. isSignedIn is checked
  // below, after every other hook (Rules of Hooks), right before the render.
  const { isLoaded, isSignedIn } = useUser()
  const [appState, setAppState] = useState<AppState>({ mode: 'checking' })
  const [jd, setJd] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [genElapsed, setGenElapsed] = useState(0)
  // Download state — completion signals loop has ended; loading shows compile progress
  const [resumeDownloaded, setResumeDownloaded] = useState(false)
  const [resumeDownloading, setResumeDownloading] = useState(false)
  // Profile readiness — show setup prompt if profile is empty
  const [profileEmpty, setProfileEmpty] = useState(false)
  // One-time nudge shown only immediately after finishing onboarding with an
  // empty profile — never re-checked on later visits, never blocks Generate.
  const [showEmptyNudge, setShowEmptyNudge] = useState(false)
  // Set only when a Generate attempt was actually blocked by the empty-profile
  // check — distinct from profileEmpty itself, so the passive hint under the
  // textarea only turns into this corrective message after a real attempt,
  // not preemptively.
  const [generateBlocked, setGenerateBlocked] = useState(false)
  const [insights, setInsights] = useState<CandidacyInsights | null>(() => {
    // Populate from cache synchronously so layout is stable on first render.
    // No age check — insights only change when a new generation happens (see
    // loadInsights below), so a cached value is never "stale" from the passage
    // of time, only from the passage of new applications.
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('careeros-insights-v2')
      if (raw) {
        const { data } = JSON.parse(raw) as { data: CandidacyInsights; ts: number }
        return data
      }
    } catch {}
    return null
  })

  // PDF preview state — fetched once, shared between mobile and desktop renders
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [pdfFailed, setPdfFailed] = useState(false)

  // Generate shortcut hint — the handler already accepts either modifier
  // (e.metaKey || e.ctrlKey), so only the displayed glyph needs to match the
  // platform. Defaults to the Ctrl form for a safe SSR render, then upgrades
  // after mount once navigator is available.
  const [shortcutHint, setShortcutHint] = useState('Ctrl ↵')
  useEffect(() => {
    if (/Mac|iPod|iPhone|iPad/.test(navigator.platform)) setShortcutHint('⌘↵')
  }, [])

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // ── Restore JD from sessionStorage on mount ──
  useEffect(() => {
    const saved = sessionStorage.getItem('careeros-jd')
    if (saved) setJd(saved)
  }, [])

  // ── Focus the textarea once the idle surface actually mounts — onboarding
  // gates (checking/needs-key/needs-profile) render first and don't have it ──
  // Focusing is handled by the idle motion.div's onAnimationComplete below —
  // AnimatePresence mode="wait" holds the idle content (and its textarea)
  // unmounted until the outgoing surface's exit animation finishes, so a
  // useEffect keyed on appState.mode fires before the ref is ever attached.

  const handleJdChange = (value: string) => {
    setJd(value)
    sessionStorage.setItem('careeros-jd', value)
  }

  // ── Load candidacy insights — refreshed once per calendar day, on the
  // first generation of that day ──
  // No time-based expiry on ordinary loads: the underlying data (your
  // application history) only changes when you generate something new, so a
  // cached headline is never "stale" just because time passed with the page
  // open or refreshed.
  //
  // The force-refresh after a completed generation is gated to once per local
  // calendar day. This is deliberately coarser than "once per session" —
  // "the dominant repeated gap across your whole history" essentially never
  // changes between your 2nd and 4th application of the same day, so a
  // second same-day refresh would mostly just be re-confirming the same
  // answer at full cost. It's also a better match for what this feature
  // actually is: a considered daily read on your search, not a live metric
  // that should visibly react within a single day.
  const loadInsights = useCallback(async (force = false) => {
    const CACHE_KEY = 'careeros-insights-v2'

    let cached: { data: CandidacyInsights; ts: number } | null = null
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (raw) cached = JSON.parse(raw)
    } catch { /* corrupt cache — treat as absent */ }

    if (!force) {
      if (cached) {
        setInsights(cached.data)
        return
      }
      // No cache yet at all — fall through and fetch once to populate it.
    } else if (cached && new Date(cached.ts).toDateString() === new Date().toDateString()) {
      // Already refreshed today — keep showing what's cached until tomorrow's
      // first generation.
      return
    }

    try {
      const data = await api.getInsights()
      setInsights(data)
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }))
      } catch { /* storage full — not critical */ }
    } catch { /* offline or no data */ }
  }, [])

  const handleDownloadResume = useCallback(async () => {
    if (appState.mode !== 'result') return
    setResumeDownloading(true)
    try {
      await api.downloadResumePdf(appState.job.id, appState.job.company)
      setResumeDownloaded(true)
    } finally {
      setResumeDownloading(false)
    }
  }, [appState])

  useEffect(() => { loadInsights() }, [loadInsights])

  // Fetch PDF once per result job — shared between mobile and desktop ResumePreview renders
  const resultJobId = appState.mode === 'result' ? appState.job.id : null
  useEffect(() => {
    if (!resultJobId) {
      setPdfBlobUrl(null)
      setPdfFailed(false)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    setPdfBlobUrl(null)
    setPdfFailed(false)
    api.fetchResumePdfPreview(resultJobId)
      .then(url => {
        if (cancelled) { URL.revokeObjectURL(url); return }
        objectUrl = url
        setPdfBlobUrl(url)
      })
      .catch(() => { if (!cancelled) setPdfFailed(true) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [resultJobId])

  // ── Onboarding gate — enforced order: API key → profile → template → idle.
  // Key comes first so users understand the BYO-key model before investing time
  // in profile setup. A skip link lets them defer the key and poke around first
  // (they'll be gated again at generate time). Runs once on mount.
  //
  // On failure, retries once after a short delay before falling open to idle.
  // A bare fail-open-on-any-error here is dangerous specifically for a brand
  // new user: their very first authenticated load races two concurrent
  // requests (getProfile + getApiKeyStatus) against JIT user provisioning on
  // the backend, and used to occasionally 500 on that race (see clerk_auth.py
  // fix) — which silently dropped a zero-profile, zero-key user straight onto
  // the full generation screen. A returning user with a real network hiccup
  // still gets through after the retry; a fresh signup gets a real gate
  // instead of one flaky request skipping every check.
  useEffect(() => {
    const check = async () => {
      const [p, keyStatus] = await Promise.all([api.getProfile(), api.getApiKeyStatus()])
      if (!keyStatus.has_key && !DEV_SKIP_KEY_GATE) {
        setAppState({ mode: 'needs-key' })
        return
      }
      if (!p.personal) {
        setAppState({ mode: 'needs-profile' })
        return
      }
      if (!p.personal.resume_template) {
        setAppState({ mode: 'needs-template', personal: p.personal })
        return
      }
      const hasContent = (p.experience && p.experience.length > 0) ||
                         (p.projects && p.projects.length > 0)
      setProfileEmpty(!hasContent)
      setAppState({ mode: 'idle' })
    }
    ;(async () => {
      try {
        await check()
      } catch {
        try {
          await new Promise(r => setTimeout(r, 500))
          await check()
        } catch {
          setAppState({ mode: 'idle' })
        }
      }
    })()
  }, [])

  // ── Elapsed timer while generating ──
  useEffect(() => {
    if (appState.mode !== 'generating') {
      setGenElapsed(0)
      return
    }
    setGenElapsed(0)
    const t = setInterval(() => setGenElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [appState.mode])

  // ── Poll while generating ──
  const pollingJobId = appState.mode === 'generating' ? appState.jobId : null
  useEffect(() => {
    if (!pollingJobId) return
    const poll = setInterval(async () => {
      try {
        const job = await api.getJob(pollingJobId)
        if (job.status === 'generated') {
          setAppState({ mode: 'result', job })
          loadInsights(true) // force-refresh after new generation
        } else if (job.status === 'failed') {
          setAppState({
            mode: 'error',
            jobId: pollingJobId,
            message: 'Generation failed. Claude didn\'t respond in time.',
          })
        }
      } catch { /* keep polling on network error */ }
    }, 2500)
    return () => clearInterval(poll)
  }, [pollingJobId, loadInsights])

  // ── Generate ──
  const handleGenerate = async () => {
    if (!jd.trim() || submitting) return
    // Fail fast, before spending a token: an empty profile has nothing for the
    // model to write from. The backend enforces this too (authoritative — see
    // jobs.py's _has_generatable_content), but checking here means the common
    // case never even hits the network. Generate itself stays clickable; this
    // only intercepts the click, it doesn't disable anything.
    if (profileEmpty) {
      setGenerateBlocked(true)
      return
    }
    setSubmitting(true)
    try {
      const job = await api.generate({ description: jd.trim() })
      sessionStorage.removeItem('careeros-jd')
      setAppState({ mode: 'generating', jobId: job.id })
      // Shallow URL sync — no visible navigation, but refresh/bookmark/share now
      // land on /jobs/[id] instead of losing the job back to a blank idle screen.
      window.history.replaceState(null, '', `/jobs/${job.id}`)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      setAppState({
        mode: 'error',
        message: e instanceof Error ? e.message : 'Failed to start generation.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  // ── Retry ──
  const handleRetry = async (jobId: number) => {
    setSubmitting(true)
    try {
      await api.regenerate(jobId)
      setAppState({ mode: 'generating', jobId })
      window.history.replaceState(null, '', `/jobs/${jobId}`)
    } catch (e) {
      setAppState({
        mode: 'error',
        jobId,
        message: e instanceof Error ? e.message : 'Retry failed.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  // ── Reset to idle ──
  const resetToIdle = () => {
    setJd('')
    setResumeDownloaded(false)
    sessionStorage.removeItem('careeros-jd')
    setAppState({ mode: 'idle' })
    window.history.replaceState(null, '', '/')
    // Re-focus textarea after state settles
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey
      // Cmd+Enter → generate (idle only)
      if (meta && e.key === 'Enter' && appState.mode === 'idle' && !submitting) {
        handleGenerate()
      }
      // Cmd+N → new application (result only)
      if (meta && e.key === 'n' && appState.mode === 'result') {
        e.preventDefault()
        resetToIdle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appState.mode, submitting, jd])

  // ─── Pre-auth branch (Phase 8) ──────────────────────────────────────────────
  // Every hook above has already run unconditionally (Rules of Hooks) — this
  // branch only changes what gets rendered.
  if (!isLoaded) return null
  if (!isSignedIn) return <LandingPage />

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto px-6 pb-24">
      <AnimatePresence mode="wait">

        {/* ── CHECKING STATE — onboarding gate resolving, before we know which surface to show ── */}
        {appState.mode === 'checking' && (
          <motion.div key="checking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 180px)' }}>
              <div className="w-8 h-8 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
            </div>
          </motion.div>
        )}

        {/* ── NEEDS-PROFILE STATE ── */}
        {appState.mode === 'needs-profile' && (
          <motion.div key="needs-profile" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <ProfileSetupGate
              onComplete={async () => {
                try {
                  const p = await api.getProfile()
                  if (p.personal && !p.personal.resume_template) {
                    setAppState({ mode: 'needs-template', personal: p.personal })
                  } else {
                    setShowEmptyNudge(
                      (p.experience?.length ?? 0) === 0 && (p.projects?.length ?? 0) === 0
                    )
                    setAppState({ mode: 'idle' })
                  }
                } catch {
                  setAppState({ mode: 'idle' })
                }
              }}
            />
          </motion.div>
        )}

        {/* ── NEEDS-TEMPLATE STATE — pick resume format ── */}
        {appState.mode === 'needs-template' && (
          <motion.div key="needs-template" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <TemplatePickerGate
              personal={appState.personal}
              onComplete={async () => {
                try {
                  const p = await api.getProfile()
                  setShowEmptyNudge(
                    (p.experience?.length ?? 0) === 0 && (p.projects?.length ?? 0) === 0
                  )
                } catch {}
                setAppState({ mode: 'idle' })
              }}
            />
          </motion.div>
        )}

        {/* ── NEEDS-KEY STATE — first onboarding step, skip available ── */}
        {appState.mode === 'needs-key' && (
          <motion.div key="needs-key" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <div className="pt-16 max-w-md mx-auto">
              <div className="text-center mb-3">
                <SectionLabel>Step 1 of 3</SectionLabel>
              </div>
              <h1 className="text-2xl font-semibold text-neutral-900 mb-2 text-center">Add your Anthropic API key</h1>
              <p className="text-sm text-neutral-600 text-center mb-10 leading-relaxed">
                CareerOS runs on your own key — every generation is billed to you, not us, and nothing about your
                usage is visible to anyone else. You can find yours at{' '}
                <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:text-neutral-800 transition-colors">
                  console.anthropic.com
                </a>.
              </p>
              <ApiKeySettings onSaved={async () => {
                try {
                  const p = await api.getProfile()
                  if (!p.personal) { setAppState({ mode: 'needs-profile' }); return }
                  if (!p.personal.resume_template) { setAppState({ mode: 'needs-template', personal: p.personal }); return }
                  setAppState({ mode: 'idle' })
                } catch { setAppState({ mode: 'idle' }) }
              }} />
              <p className="text-xs text-neutral-600 text-center mt-8">
                <button
                  onClick={async () => {
                    try {
                      const p = await api.getProfile()
                      if (!p.personal) { setAppState({ mode: 'needs-profile' }); return }
                      if (!p.personal.resume_template) { setAppState({ mode: 'needs-template', personal: p.personal }); return }
                      setAppState({ mode: 'idle' })
                    } catch { setAppState({ mode: 'idle' }) }
                  }}
                  className="underline underline-offset-2 hover:text-neutral-800 transition-colors"
                >
                  Set up later in Settings
                </button>
              </p>
            </div>
          </motion.div>
        )}

        {/* ── IDLE STATE ── */}
        {appState.mode === 'idle' && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={spring.gentle}
            onAnimationComplete={() => textareaRef.current?.focus()}
          >
            <div className="pt-12">

              {/* ── Brand mark — glow emanates from the ring stroke itself ── */}
              <motion.div
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...spring.bouncy, delay: 0.05 }}
                className="flex justify-center mb-8"
              >
                <span className="brand-ring-glow-cool text-neutral-900">
                  <BrandMark size={56} physicalStroke={1.5} />
                </span>
              </motion.div>

              {/* ── Workspace zone ── */}
              <div
                className="jd-workspace rounded-2xl relative cursor-text"
                onClick={() => textareaRef.current?.focus()}
                style={{ background: 'var(--c-glass-bg)' }}
              >
                {/* Writing surface */}
                <div
                  className="px-8 pt-7 pb-16"
                  style={{ minHeight: '28vh' }}
                >
                  <AutoTextarea
                    ref={textareaRef}
                    value={jd}
                    onChange={e => handleJdChange(e.target.value)}
                    placeholder="Paste a job description…"
                    disabled={submitting}
                    className="jd-textarea w-full text-[15px] text-neutral-800 placeholder-neutral-500 focus:outline-none leading-relaxed disabled:opacity-40"
                    style={{ background: 'transparent', border: 'none', padding: '0' }}
                  />
                </div>

                {/* Generate affordance — anchored bottom-right inside the zone */}
                <div className="absolute bottom-5 right-7">
                  <motion.button
                    onClick={handleGenerate}
                    disabled={submitting || !jd.trim()}
                    whileTap={{ scale: 0.97 }}
                    className="flex items-center gap-2 text-sm text-neutral-700 hover:text-neutral-900 disabled:opacity-40 transition-colors"
                  >
                    {submitting ? (
                      <>
                        <span className="w-3.5 h-3.5 rounded-full animate-spin" style={{ border: '1.5px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
                        <span>Starting…</span>
                      </>
                    ) : (
                      <>
                        <span>Generate</span>
                        <kbd
                          className="text-[10px] font-sans px-1.5 py-0.5 rounded-md border"
                          style={{
                            background: 'var(--c-kbd-bg)',
                            borderColor: 'var(--c-kbd-border)',
                            color: 'var(--c-kbd-text)',
                          }}
                        >
                          {shortcutHint}
                        </kbd>
                      </>
                    )}
                  </motion.button>
                </div>
              </div>

              {/* ── Output hint — what arrives, corrective message if a blocked Generate
                   was just attempted, or a passive setup nudge if profile is empty ── */}
              <div className="mt-3 text-center">
                {generateBlocked && profileEmpty ? (
                  <motion.p
                    initial={{ opacity: 0, y: -2 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={spring.snappy}
                    className="text-xs"
                    style={{ color: 'var(--c-danger)' }}
                  >
                    Add a project or role first —{' '}
                    <Link
                      href="/profile"
                      className="underline decoration-current hover:opacity-80 transition-opacity"
                    >
                      add now
                    </Link>
                    {' '}— there&apos;s nothing to write from yet.
                  </motion.p>
                ) : profileEmpty ? (
                  <p className="text-xs text-neutral-600">
                    <Link
                      href="/profile"
                      className="underline decoration-neutral-300 hover:text-neutral-600 transition-colors"
                    >
                      Add your experience
                    </Link>
                    {' '}for a tailored resume
                  </p>
                ) : (
                  <p className="text-xs text-neutral-600 tracking-wide">
                    Resume · Cover letter · Fit analysis
                  </p>
                )}
              </div>

              {/* ── One-time empty-profile nudge — only right after onboarding ── */}
              <AnimatePresence>
                {showEmptyNudge && (
                  <EmptyProfileNudge onDismiss={() => setShowEmptyNudge(false)} />
                )}
              </AnimatePresence>

              {/* ── Candidacy signal — "arrived at a conclusion" reveal ── */}
              <AnimatePresence>
                {insights && insights.count > 0 && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.28, ease: [0.25, 0, 0, 1] }}
                    className="overflow-hidden"
                  >
                    {/* Inner reveal: delayed y-rise with spring — the "conclusion" motion */}
                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ ...spring.gentle, delay: 0.2 }}
                      className="mt-12"
                    >
                      {insights.count < 3 ? (
                        /* Not enough data yet */
                        <>
                          <p className="text-xl font-semibold text-neutral-700 tracking-tight leading-tight mb-2">
                            {insights.count} application{insights.count === 1 ? '' : 's'}
                          </p>
                          <p className="text-sm text-neutral-600 leading-relaxed">
                            Apply to {3 - insights.count} more for a candidacy read.
                          </p>
                        </>
                      ) : (
                        /* Structured insight — scannable in seconds */
                        <>
                          <p className="text-xl font-semibold text-neutral-700 tracking-tight leading-snug mb-5">
                            {insights.headline ?? `${insights.count} applications`}
                          </p>
                          <div className="space-y-4 max-w-lg">
                            {insights.observed && (
                              <div>
                                <SectionLabel className="mb-1" style={{ color: 'var(--c-warn)' }}>Observed</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.observed}</p>
                              </div>
                            )}
                            {insights.gap && (
                              <div>
                                <SectionLabel className="mb-1" style={{ color: 'var(--c-danger)' }}>Gap</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.gap}</p>
                              </div>
                            )}
                            {insights.action && (
                              <div>
                                <SectionLabel className="mb-1" style={{ color: 'var(--c-success)' }}>Action</SectionLabel>
                                <p className="text-sm text-neutral-600 leading-relaxed">{insights.action}</p>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {/* ── GENERATING STATE ── */}
        {appState.mode === 'generating' && (
          <motion.div
            key="generating"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.gentle}
          >
            {/* Brand arc + message — compressed upper area */}
            <div className="flex flex-col items-center gap-5 pt-24">
              {/* Ring becomes a spinning arc — same mark, active state */}
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
                style={{ width: 52, height: 52 }}
                className="brand-ring-glow-cool"
              >
                <svg width={52} height={52} viewBox="0 0 52 52" fill="none">
                  <circle cx={26} cy={26} r={19.5} stroke="var(--c-accent-dim)" strokeWidth={1.5} />
                  <circle
                    cx={26} cy={26} r={19.5}
                    stroke="var(--c-accent)"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeDasharray="79.6 42.9"
                  />
                </svg>
              </motion.div>

              {/* Message */}
              <AnimatePresence mode="wait">
                <motion.p
                  key={getGenMessage(genElapsed)}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={spring.gentle}
                  className="text-[14px] text-neutral-600 text-center"
                >
                  {getGenMessage(genElapsed)}
                </motion.p>
              </AnimatePresence>
            </div>

            {/* Skeleton — ghost of what's being built */}
            <GeneratingSkeleton />
          </motion.div>
        )}

        {/* ── RESULT STATE ── */}
        {appState.mode === 'result' && (
          // Deliberately snappier than the other states' spring.gentle — this is the
          // deliverable arriving after ~20s of generation, the single most consequential
          // moment in the core loop. The extra weight (spring.standard, y:12) is intentional.
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.standard}
          >
            {/* Back button */}
            <div className="pt-8 mb-8">
              <button
                onClick={resetToIdle}
                className={`text-sm transition-colors flex items-center gap-1.5 ${
                  resumeDownloaded
                    ? 'text-neutral-700 hover:text-neutral-900 font-medium'
                    : 'text-neutral-600 hover:text-neutral-800'
                }`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                New application
                <span className="text-xs font-normal ml-1 opacity-60">⌘N</span>
              </button>
            </div>

            {/* Title + ScoreRing row */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h1 className="heading-lit text-[2rem] font-semibold text-neutral-900 leading-tight tracking-tight">
                  {appState.job.title}
                </h1>
                {appState.job.company && (
                  <p className="text-[15px] text-neutral-600 mt-0.5">{appState.job.company}</p>
                )}
              </div>
              {appState.job.fit_score != null && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ ...spring.bouncy, delay: 0.15 }}
                  className="shrink-0 mt-1"
                >
                  <ScoreRing score={appState.job.fit_score} size={64} celebrate />
                </motion.div>
              )}
            </div>

            {/* Status actions — same position as archive page */}
            <div className="flex items-center gap-4 mb-8 flex-wrap">
              <StatusActions
                job={appState.job}
                onUpdate={job => setAppState({ mode: 'result', job })}
              />
            </div>

            {/* Single-column content */}
            <div>
              {/* Strategic analysis */}
              {appState.job.strategic_note && (() => {
                const analysis = parseStrategicNote(appState.job.strategic_note)
                return (
                  <>
                    <Divider delay={0} />
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ ...spring.gentle, delay: 0.05 }}
                      className="mb-2"
                    >
                      {analysis ? (
                        <div className="space-y-6">
                          <AnalysisSection title="Good fit" bullets={analysis.goodFit} color="var(--c-success)" />
                          <AnalysisSection title="Gaps" bullets={analysis.gaps} color="var(--c-danger)" />
                          <AnalysisSection title="Improvement plan" bullets={analysis.plan} color="var(--c-warn)" />
                        </div>
                      ) : (
                        <p className="text-[15px] text-neutral-700 leading-[1.8] max-w-[520px]">
                          {appState.job.strategic_note}
                        </p>
                      )}
                    </motion.div>
                  </>
                )
              })()}

              <Divider delay={0.05} />

              {/* Projects bar + compression notice */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ ...spring.gentle, delay: 0.08 }}
              >
                {appState.job.selected_projects && appState.job.selected_projects.length > 0 && (
                  <SelectedProjectsBar projects={appState.job.selected_projects} />
                )}
                {(appState.job.compression_attempts ?? 0) > 0 && (
                  <p className="text-xs text-neutral-600 font-mono -mt-1 mb-3">
                    compressed to 1 page · {appState.job.compression_attempts} {appState.job.compression_attempts === 1 ? 'pass' : 'passes'}
                  </p>
                )}
              </motion.div>

              {/* Resume PDF — inline for all viewports */}
              {appState.job.resume_latex && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...spring.gentle, delay: 0.1 }}
                  className="relative"
                >
                  <ResumePreview
                    jobId={appState.job.id}
                    blobUrl={pdfBlobUrl}
                    failed={pdfFailed}
                    onError={() => setPdfFailed(true)}
                  />
                </motion.div>
              )}

              {/* Download Resume button */}
              {appState.job.resume_latex && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.12 }}
                  className="mb-8 flex items-center gap-3"
                >
                  <DownloadIconButton
                    onClick={handleDownloadResume}
                    downloading={resumeDownloading}
                    downloaded={resumeDownloaded}
                    title="Download resume"
                  />
                  {(appState.job.compression_attempts ?? 0) >= 2 && (
                    <button
                      onClick={() => api.downloadResumePdfPage1(appState.job.id, appState.job.company)}
                      className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                      title="Resume may exceed 1 page — download only the first page with links intact"
                    >
                      Page 1 only ↓
                    </button>
                  )}
                </motion.div>
              )}

              {/* Cover letter */}
              {appState.job.cover_letter && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...spring.gentle, delay: 0.16 }}
                >
                  <Divider delay={0.14} />
                  <CoverLetterSection
                    job={appState.job}
                    onSave={job => setAppState({ mode: 'result', job })}
                  />
                </motion.div>
              )}

              {/* LaTeX source */}
              {appState.job.resume_latex && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ ...spring.gentle, delay: 0.2 }}
                >
                  <Divider delay={0.18} />
                  <LatexSection latex={appState.job.resume_latex} />
                </motion.div>
              )}
            </div>
          </motion.div>
        )}

        {/* ── ERROR STATE ── */}
        {appState.mode === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={spring.gentle}
          >
            <div
              className="flex flex-col items-center justify-center gap-4"
              style={{ minHeight: 'calc(100vh - 180px)' }}
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(239,68,68,0.08)' }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>

              <div className="text-center">
                <p className="text-[15px] text-neutral-700 font-medium max-w-xs">{appState.message}</p>
              </div>

              <div className="flex items-center gap-3 mt-2">
                {appState.jobId != null && (
                  <motion.button
                    onClick={() => handleRetry(appState.jobId!)}
                    disabled={submitting}
                    whileTap={{ scale: 0.97 }}
                    className="px-5 py-2.5 rounded-2xl text-sm font-semibold text-white disabled:opacity-40 transition-all"
                    style={{
                      background: 'var(--c-btn-bg)',
                      boxShadow: 'var(--c-btn-shadow)',
                    }}
                  >
                    {submitting ? 'Retrying…' : 'Try again'}
                  </motion.button>
                )}
                <button
                  onClick={resetToIdle}
                  className="px-4 py-2.5 rounded-2xl text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-700"
                  style={{ background: 'rgba(0,0,0,0.04)' }}
                >
                  Start over
                </button>
              </div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
