'use client'

import { Suspense } from 'react'
import { usePathname } from 'next/navigation'
import { AuthenticateWithRedirectCallback } from '@clerk/nextjs'
import { AuthCard } from '@/components/AuthCard'

// See app/sign-in — same catch-all + sso-callback branching pattern.
export default function SignUpPage() {
  const pathname = usePathname()
  if (pathname?.endsWith('/sso-callback')) {
    return <AuthenticateWithRedirectCallback />
  }
  return (
    <Suspense>
      <AuthCard mode="sign-up" />
    </Suspense>
  )
}
