import { SignIn } from '@clerk/nextjs'

// Appearance is now set once at the ClerkProvider level (app/layout.tsx) so it
// covers every Clerk component — SignIn/SignUp here, but also UserButton's
// dropdown and "Manage account" modal, which previously fell back to Clerk's
// stock light theme since nothing themed them individually.
export default function SignInPage() {
  return (
    <div className="flex justify-center pt-12">
      <SignIn />
    </div>
  )
}
