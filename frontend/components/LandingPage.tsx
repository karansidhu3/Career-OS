'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { BrandMark } from '@/components/BrandMark'
import { spring } from '@/lib/motion'
import { inputStyle, PrimaryButton } from '@/components/FormControls'

// Pre-auth landing page — the surface a signed-out visitor sees at "/" instead
// of the real app (app/page.tsx branches on Clerk's isSignedIn to choose
// between this and the core loop). Email capture here hands off straight into
// real sign-up (email verification code) rather than a waitlist queue — no
// manual invite step, no separate waitlist table in the loop.
export function LandingPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    router.push(`/sign-up?email=${encodeURIComponent(email.trim())}`)
  }

  return (
    <div className="h-dvh overflow-hidden flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="w-full max-w-xl"
      >
        <div className="flex justify-center mb-10">
          <span className="brand-ring-glow-cool text-neutral-900">
            <BrandMark size={36} physicalStroke={1.5} />
          </span>
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 mb-5 text-center">CareerOS</h1>
        <p className="text-lg font-medium text-neutral-800 text-center mb-3">
          Paste a job description. Get a finished application.
        </p>
        <p className="text-[13px] text-neutral-600 text-center mb-12">
          Tailored resume and cover letter, in seconds.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <input
            type="email"
            required
            autoFocus
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="form-input w-full px-3 py-2 rounded-xl text-sm font-light text-neutral-700 placeholder-neutral-300 focus:outline-none"
            style={inputStyle}
          />
          <PrimaryButton type="submit" fullWidth disabled={!email.trim()}>
            Get started
          </PrimaryButton>
        </form>

        <p className="text-xs text-neutral-600 text-center mt-10">
          Already have an account?{' '}
          <a
            href="/sign-in"
            className="sign-in-glow text-neutral-900 underline underline-offset-2 transition-colors"
          >
            Sign in
          </a>
        </p>

        <p className="text-xs text-neutral-600 text-center mt-4">
          <a href="/terms" className="text-neutral-600 hover:text-neutral-800 underline underline-offset-2">Terms</a>
          {' · '}
          <a href="/privacy" className="text-neutral-600 hover:text-neutral-800 underline underline-offset-2">Privacy</a>
        </p>
      </motion.div>
    </div>
  )
}
