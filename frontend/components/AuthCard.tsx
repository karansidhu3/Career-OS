'use client'

import { useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
// Deliberately importing from the /legacy subpath: the default useSignIn/useSignUp
// in this Clerk version return a Signals-based { signIn, errors, fetchStatus } shape
// with no isLoaded/setActive and mutating methods that don't behave like normal
// Promise-returning calls (confirmed via live debugging — create() resolves without
// throwing but returns no usable resource, and prepareEmailAddressVerification isn't
// even defined on it). The /legacy hooks give the classic, documented
// { isLoaded, signIn/signUp, setActive } API that custom-flow guides assume.
import { useSignIn, useSignUp } from '@clerk/nextjs/legacy'
import { BrandMark } from '@/components/BrandMark'
import { spring } from '@/lib/motion'
import { inputStyle, PrimaryButton } from '@/components/FormControls'

function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.57.1.78-.25.78-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.87-1.36-3.87-1.36-.53-1.34-1.29-1.69-1.29-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.78 1.19 1.78 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.76.12 3.05.74.8 1.19 1.83 1.19 3.09 0 4.43-2.7 5.41-5.27 5.69.41.36.78 1.07.78 2.15 0 1.56-.01 2.81-.01 3.19 0 .3.2.66.79.55A10.52 10.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z" />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47a5.53 5.53 0 0 1-2.4 3.63v3h3.87c2.27-2.09 3.58-5.17 3.58-8.82z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.87-3c-1.08.72-2.45 1.14-4.07 1.14-3.13 0-5.78-2.11-6.73-4.96H1.27v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.27 14.27a7.2 7.2 0 0 1 0-4.54v-3.1H1.27a12 12 0 0 0 0 10.74l4-3.1z" />
      <path fill="#EA4335" d="M12 4.75c1.76 0 3.34.6 4.59 1.79l3.44-3.44C17.95 1.19 15.24 0 12 0A12 12 0 0 0 1.27 6.63l4 3.1C6.22 6.86 8.87 4.75 12 4.75z" />
    </svg>
  )
}

function OAuthButton({ provider, onClick, disabled }: { provider: 'github' | 'google'; onClick: () => void; disabled: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium text-neutral-800 disabled:opacity-40 transition-colors"
      style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}
    >
      {provider === 'github' ? <GitHubIcon /> : <GoogleIcon />}
      {provider === 'github' ? 'GitHub' : 'Google'}
    </button>
  )
}

type Mode = 'sign-in' | 'sign-up'

export function AuthCard({ mode }: { mode: Mode }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isLoaded: signInLoaded, signIn, setActive: setActiveSignIn } = useSignIn()
  const { isLoaded: signUpLoaded, signUp, setActive: setActiveSignUp } = useSignUp()

  const [step, setStep] = useState<'email' | 'code' | 'forgot-email' | 'forgot-code'>('email')
  const [email, setEmail] = useState(searchParams.get('email') ?? '')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState<'email' | 'code' | 'github' | 'google' | 'forgot-email' | 'forgot-code' | null>(null)
  const [error, setError] = useState<string | null>(null)
  // The exact resource instance returned by create()+prepare*Verification() in
  // submitEmail — attemptFirstFactor/attemptEmailAddressVerification in submitCode
  // must run on this SAME instance, not a fresh read from the hook. Mixing the two
  // caused "wrong code" failures even with a correct code, because the hook's
  // signIn/signUp value hadn't necessarily caught up to the one that actually holds
  // the pending verification.
  const pending = useRef<any>(null)

  const ready = mode === 'sign-in' ? signInLoaded : signUpLoaded

  const oauth = async (provider: 'github' | 'google') => {
    if (!ready) return
    setLoading(provider)
    setError(null)
    const strategy = provider === 'github' ? 'oauth_github' : 'oauth_google'
    try {
      if (mode === 'sign-in') {
        await signIn!.authenticateWithRedirect({
          strategy,
          redirectUrl: '/sign-in/sso-callback',
          redirectUrlComplete: '/',
        })
      } else {
        await signUp!.authenticateWithRedirect({
          strategy,
          redirectUrl: '/sign-up/sso-callback',
          redirectUrlComplete: '/',
        })
      }
    } catch {
      setError('Something went wrong — try again.')
      setLoading(null)
    }
  }

  const submitEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ready || !email.trim() || !password.trim()) return
    setLoading('email')
    setError(null)
    try {
      if (mode === 'sign-in') {
        // Password auth completes in one step — no code needed.
        const attempt = await signIn!.create({ identifier: email.trim(), password: password.trim() })
        if (attempt.status === 'complete') {
          await setActiveSignIn!({ session: attempt.createdSessionId })
          router.push('/')
          return
        }
        throw new Error('sign-in-incomplete')
      } else {
        // This instance requires a password on sign-up (confirmed live: verifying
        // the email code alone leaves the attempt at status "missing_requirements"
        // with missingFields: ["password"], which otherwise silently looks
        // identical to a wrong code from the UI).
        const created = await signUp!.create({ emailAddress: email.trim(), password: password.trim() })
        pending.current = await created.prepareEmailAddressVerification({ strategy: 'email_code' })
        setStep('code')
      }
    } catch (err: any) {
      console.error('Auth error:', err)
      const clerkMsg = err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message
      setError(
        mode === 'sign-in'
          ? (clerkMsg ?? 'Wrong email or password.')
          : (clerkMsg ?? "Couldn't start sign-up — check the email and try again."),
      )
    } finally {
      setLoading(null)
    }
  }

  const submitCode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ready || !code.trim()) return
    setLoading('code')
    setError(null)
    try {
      if (mode === 'sign-in') {
        const attempt = await pending.current.attemptFirstFactor({ strategy: 'email_code', code: code.trim() })
        if (attempt.status === 'complete') {
          await setActiveSignIn!({ session: attempt.createdSessionId })
          router.push('/')
          return
        }
      } else {
        const attempt = await pending.current.attemptEmailAddressVerification({ code: code.trim() })
        if (attempt.status === 'complete') {
          await setActiveSignUp!({ session: attempt.createdSessionId })
          router.push('/')
          return
        }
      }
      setError('That code didn’t work — check it and try again.')
    } catch {
      setError('That code didn’t work — check it and try again.')
    } finally {
      setLoading(null)
    }
  }

  // ── Forgot password (sign-in only) — same create()-then-attemptFirstFactor()
  // shape as the sign-in code flow above, but on the reset_password_email_code
  // strategy: the code Clerk emails proves ownership of the address, and the
  // new password is submitted in the same attempt that consumes it.
  const submitForgotEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!signInLoaded || !email.trim()) return
    setLoading('forgot-email')
    setError(null)
    try {
      pending.current = await signIn!.create({ strategy: 'reset_password_email_code', identifier: email.trim() })
      setStep('forgot-code')
    } catch (err: any) {
      const clerkMsg = err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message
      setError(clerkMsg ?? "Couldn't send a reset code — check the email and try again.")
    } finally {
      setLoading(null)
    }
  }

  const submitForgotCode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!signInLoaded || !code.trim() || !newPassword.trim()) return
    setLoading('forgot-code')
    setError(null)
    try {
      const attempt = await pending.current.attemptFirstFactor({
        strategy: 'reset_password_email_code',
        code: code.trim(),
        password: newPassword.trim(),
      })
      if (attempt.status === 'complete') {
        await setActiveSignIn!({ session: attempt.createdSessionId })
        router.push('/')
        return
      }
      setError('That code didn’t work — check it and try again.')
    } catch (err: any) {
      const clerkMsg = err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message
      setError(clerkMsg ?? 'That code didn’t work — check it and try again.')
    } finally {
      setLoading(null)
    }
  }

  const backToSignIn = () => {
    setStep('email')
    setCode('')
    setNewPassword('')
    setError(null)
  }

  return (
    <div className="h-dvh overflow-hidden flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="w-full max-w-sm"
      >
        <div className="flex justify-center mb-8">
          <span className="brand-ring-glow-cool text-neutral-900">
            <BrandMark size={32} physicalStroke={1.5} />
          </span>
        </div>

        <h1 className="text-2xl font-bold tracking-tight text-neutral-900 text-center mb-1.5">
          {mode === 'sign-in' ? 'Sign in' : 'Create your account'}
        </h1>
        <p className="text-[13px] text-neutral-600 text-center mb-8">
          {mode === 'sign-in' ? 'Welcome back to CareerOS.' : 'One paste. A finished application.'}
        </p>

        <div className="flex gap-3 mb-5">
          <OAuthButton provider="github" onClick={() => oauth('github')} disabled={loading !== null} />
          <OAuthButton provider="google" onClick={() => oauth('google')} disabled={loading !== null} />
        </div>

        <div className="flex items-center gap-3 mb-5">
          <div className="flex-1 h-px" style={{ background: 'var(--c-border)' }} />
          <span className="text-xs text-neutral-600">or</span>
          <div className="flex-1 h-px" style={{ background: 'var(--c-border)' }} />
        </div>

        {/* Clerk's bot-protection widget needs this exact element to attach to —
            invisible unless a challenge is actually triggered. Custom flows that
            omit it silently fail sign-up creation. */}
        <div id="clerk-captcha" />

        <AnimatePresence mode="wait">
          {step === 'email' ? (
            <motion.form
              key="email"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
              onSubmit={submitEmail}
              className="flex flex-col gap-3"
            >
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              <input
                type="password"
                required
                autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Password"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              {mode === 'sign-in' && (
                <button
                  type="button"
                  onClick={() => { setStep('forgot-email'); setError(null) }}
                  className="self-end -mt-1 text-xs text-neutral-600 hover:text-neutral-800 transition-colors"
                >
                  Forgot password?
                </button>
              )}
              <PrimaryButton
                type="submit"
                fullWidth
                disabled={loading !== null || !email.trim() || !password.trim()}
              >
                {loading === 'email' ? 'Continuing…' : 'Continue'}
              </PrimaryButton>
            </motion.form>
          ) : step === 'code' ? (
            <motion.form
              key="code"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
              onSubmit={submitCode}
              className="flex flex-col gap-3"
            >
              <p className="text-xs text-neutral-600 -mt-1 mb-1">
                Enter the code sent to <span className="text-neutral-800">{email}</span>
              </p>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                autoFocus
                value={code}
                onChange={e => setCode(e.target.value)}
                placeholder="123456"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light tracking-[0.3em] text-center text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              <PrimaryButton type="submit" fullWidth disabled={loading !== null || !code.trim()}>
                {loading === 'code' ? 'Verifying…' : 'Verify'}
              </PrimaryButton>
              <button
                type="button"
                onClick={() => { setStep('email'); setCode(''); setError(null) }}
                className="text-xs text-neutral-600 hover:text-neutral-800 transition-colors"
              >
                Use a different email
              </button>
            </motion.form>
          ) : step === 'forgot-email' ? (
            <motion.form
              key="forgot-email"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
              onSubmit={submitForgotEmail}
              className="flex flex-col gap-3"
            >
              <p className="text-xs text-neutral-600 -mt-1 mb-1">
                We&rsquo;ll email a code to reset your password.
              </p>
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              <PrimaryButton type="submit" fullWidth disabled={loading !== null || !email.trim()}>
                {loading === 'forgot-email' ? 'Sending…' : 'Send reset code'}
              </PrimaryButton>
              <button
                type="button"
                onClick={backToSignIn}
                className="text-xs text-neutral-600 hover:text-neutral-800 transition-colors"
              >
                Back to sign in
              </button>
            </motion.form>
          ) : (
            <motion.form
              key="forgot-code"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
              onSubmit={submitForgotCode}
              className="flex flex-col gap-3"
            >
              <p className="text-xs text-neutral-600 -mt-1 mb-1">
                Enter the code sent to <span className="text-neutral-800">{email}</span> and choose a new password.
              </p>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                autoFocus
                value={code}
                onChange={e => setCode(e.target.value)}
                placeholder="123456"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light tracking-[0.3em] text-center text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              <input
                type="password"
                required
                autoComplete="new-password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                placeholder="New password"
                className="form-input w-full px-3 py-2 rounded-xl text-sm font-light text-neutral-700 placeholder-neutral-300 focus:outline-none"
                style={inputStyle}
                disabled={loading !== null}
              />
              <PrimaryButton type="submit" fullWidth disabled={loading !== null || !code.trim() || !newPassword.trim()}>
                {loading === 'forgot-code' ? 'Resetting…' : 'Reset password'}
              </PrimaryButton>
              <button
                type="button"
                onClick={backToSignIn}
                className="text-xs text-neutral-600 hover:text-neutral-800 transition-colors"
              >
                Back to sign in
              </button>
            </motion.form>
          )}
        </AnimatePresence>

        {error && <p className="text-xs text-center mt-4" style={{ color: 'var(--c-danger)' }}>{error}</p>}

        <p className="text-xs text-neutral-600 text-center mt-8">
          {mode === 'sign-in' ? (
            <>Don&rsquo;t have an account? <a href="/sign-up" className="sign-in-glow text-neutral-900 underline underline-offset-2">Sign up</a></>
          ) : (
            <>Already have an account? <a href="/sign-in" className="sign-in-glow text-neutral-900 underline underline-offset-2">Sign in</a></>
          )}
        </p>
      </motion.div>
    </div>
  )
}
