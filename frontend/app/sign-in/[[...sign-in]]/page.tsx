import { SignIn } from '@clerk/nextjs'
import { clerkAppearance } from '@/lib/clerkAppearance'

export default function SignInPage() {
  return (
    <div className="flex justify-center pt-12">
      <SignIn appearance={clerkAppearance} />
    </div>
  )
}
