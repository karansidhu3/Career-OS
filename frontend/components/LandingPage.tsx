'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { BrandMark } from '@/components/BrandMark'
import { spring } from '@/lib/motion'

const inputCls = "w-full px-3 py-2.5 rounded-xl text-sm text-neutral-700 placeholder-neutral-400 focus:outline-none"
const inputStyle = { background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.07)' }

// Pre-auth waitlist landing page (Phase 8) — the surface a signed-out visitor
// sees at "/" instead of the real app (app/page.tsx branches on Clerk's
// isSignedIn to choose between this and the core loop). Sells the BYO-key
// model as a trust feature rather than hiding it — that's the actual product
// differentiator worth leading with, not a footnote.
export function LandingPage() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'joined' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (status === 'submitting' || status === 'joined') return
    setStatus('submitting')
    setError(null)
    try {
      await api.joinWaitlist(email.trim())
      setStatus('joined')
    } catch {
      setError("Couldn't join the waitlist — check the email and try again.")
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="w-full max-w-md"
      >
        <div className="flex justify-center mb-8">
          <span className="brand-ring-glow text-neutral-600" style={{ opacity: 0.55 }}>
            <BrandMark size={40} physicalStroke={1.5} />
          </span>
        </div>

        <h1 className="text-2xl font-semibold text-neutral-900 mb-3 text-center">CareerOS</h1>
        <p className="text-sm text-neutral-500 text-center mb-10 leading-relaxed">
          Paste a job description. Get a tailored resume and cover letter in 20 seconds.
        </p>

        <div className="rounded-2xl p-6 mb-6" style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}>
          <p className="text-[13px] font-medium text-neutral-800 mb-1.5">You bring your own AI key.</p>
          <p className="text-[13px] text-neutral-500 leading-relaxed">
            Every generation is billed to your own Anthropic account — CareerOS never sees or pays
            for your usage, and never has visibility into your generation costs.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {status === 'joined' ? (
            <motion.div
              key="joined"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={spring.snappy}
              className="text-center py-3"
            >
              <p className="text-sm font-medium" style={{ color: 'var(--c-success)' }}>You&rsquo;re on the list.</p>
              <p className="text-xs text-neutral-400 mt-1">We&rsquo;ll email you when it&rsquo;s your turn.</p>
            </motion.div>
          ) : (
            <motion.form
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
              onSubmit={submit}
              className="flex flex-col gap-3"
            >
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
                style={inputStyle}
                disabled={status === 'submitting'}
              />
              <button
                type="submit"
                disabled={status === 'submitting' || !email.trim()}
                className="w-full px-4 py-2.5 rounded-xl text-sm font-medium text-white disabled:opacity-40 transition-opacity"
                style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
              >
                {status === 'submitting' ? 'Joining…' : 'Join the waitlist'}
              </button>
              {error && <p className="text-xs text-center" style={{ color: 'var(--c-danger)' }}>{error}</p>}
            </motion.form>
          )}
        </AnimatePresence>

        <p className="text-xs text-neutral-400 text-center mt-8">
          Already invited?{' '}
          <a href="/sign-in" className="text-neutral-600 hover:text-neutral-800 underline underline-offset-2">
            Sign in
          </a>
        </p>

        <p className="text-xs text-neutral-400 text-center mt-3">
          <a href="/terms" className="hover:text-neutral-600 underline underline-offset-2">Terms</a>
          {' · '}
          <a href="/privacy" className="hover:text-neutral-600 underline underline-offset-2">Privacy</a>
        </p>
      </motion.div>
    </div>
  )
}
