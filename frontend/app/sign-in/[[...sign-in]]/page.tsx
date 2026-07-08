'use client'

import { Suspense } from 'react'
import { usePathname } from 'next/navigation'
import { AuthenticateWithRedirectCallback } from '@clerk/nextjs'
import { AuthCard } from '@/components/AuthCard'

// Custom sign-in flow (OAuth + email code) instead of Clerk's prebuilt <SignIn/>.
// This route is a catch-all so the OAuth callback (/sign-in/sso-callback) also
// lands here — branch on pathname to complete the redirect handshake instead
// of rendering the form again.
export default function SignInPage() {
  const pathname = usePathname()
  if (pathname?.endsWith('/sso-callback')) {
    return <AuthenticateWithRedirectCallback />
  }
  return (
    <Suspense>
      <AuthCard mode="sign-in" />
    </Suspense>
  )
}
