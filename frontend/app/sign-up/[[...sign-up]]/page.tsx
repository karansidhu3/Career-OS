import { SignUp } from '@clerk/nextjs'
import { clerkAppearance } from '@/lib/clerkAppearance'

export default function SignUpPage() {
  return (
    <div className="flex justify-center pt-12">
      <SignUp appearance={clerkAppearance} />
    </div>
  )
}
