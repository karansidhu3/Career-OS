import { SignUp } from '@clerk/nextjs'

// See app/sign-in — appearance now lives once at the ClerkProvider level.
export default function SignUpPage() {
  return (
    <div className="flex justify-center pt-12">
      <SignUp />
    </div>
  )
}
