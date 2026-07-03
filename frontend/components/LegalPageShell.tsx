import Link from 'next/link'

// Shared chrome for /terms and /privacy — both public routes (proxy.ts), readable
// by a signed-out visitor deciding whether to trust CareerOS before signing up.
export function LegalPageShell({
  title,
  lastUpdated,
  children,
}: {
  title: string
  lastUpdated: string
  children: React.ReactNode
}) {
  return (
    <div className="max-w-2xl mx-auto px-6 pb-24 pt-4">
      <Link href="/" className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
        ← CareerOS
      </Link>
      <h1 className="text-2xl font-semibold text-neutral-900 mt-6 mb-1">{title}</h1>
      <p className="text-xs text-neutral-600 mb-10">Last updated {lastUpdated}</p>
      <div className="prose-legal text-[14px] text-neutral-700 leading-relaxed space-y-6">
        {children}
      </div>
    </div>
  )
}

export function LegalSection({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-[15px] font-semibold text-neutral-900 mb-2">{heading}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
