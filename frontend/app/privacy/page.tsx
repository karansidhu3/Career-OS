import { LegalPageShell, LegalSection } from '@/components/LegalPageShell'

export const metadata = { title: 'Privacy Policy — CareerOS' }

export default function PrivacyPage() {
  return (
    <LegalPageShell title="Privacy Policy" lastUpdated="July 2026">
      <p className="text-xs italic text-neutral-400 border-l-2 pl-3" style={{ borderColor: 'var(--c-warn)' }}>
        This is a starting draft, not a substitute for legal advice. It has not been reviewed by a
        lawyer. Do not rely on it as final before opening CareerOS to the public.
      </p>

      <LegalSection heading="What we collect">
        <p>To provide the core generation loop, CareerOS stores:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Your account email and identity, managed by Clerk (our authentication provider)</li>
          <li>Your profile: work experience, education, projects, and skills, as you enter them</li>
          <li>Job descriptions you paste, and the resumes/cover letters generated from them</li>
          <li>Your Anthropic API key, stored encrypted — never in plain text, never logged</li>
          <li>
            Basic request metadata (timestamps, request counts) used only for the abuse-prevention
            guardrails described below
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="What we don't do">
        <ul className="list-disc pl-5 space-y-1">
          <li>We don&rsquo;t sell your data or share it with advertisers</li>
          <li>We don&rsquo;t use your resume content or job descriptions to train any AI model</li>
          <li>We don&rsquo;t send marketing emails or engagement notifications of any kind</li>
          <li>
            We never see or pay for your AI generation usage — every generation call uses your own
            Anthropic API key, billed directly to your Anthropic account
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="Third parties that process your data">
        <p>Running CareerOS requires a small number of infrastructure providers:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Clerk</strong> — authentication and session management</li>
          <li><strong>Anthropic</strong> — generates your resumes/cover letters, using your own API key</li>
          <li><strong>Neon</strong> — hosts our Postgres database (your profile, job history)</li>
          <li><strong>Cloudflare R2</strong> — stores compiled resume/cover letter PDFs</li>
          <li><strong>Upstash</strong> — powers the background job queue that runs generations</li>
          <li><strong>Fly.io and Vercel</strong> — host the application itself</li>
          <li>
            <strong>Resend</strong> — sends exactly two kinds of transactional email: your data
            export being ready, and account deletion confirmation. Nothing else — no digests, no
            marketing, no notifications
          </li>
          <li>
            <strong>Sentry</strong> — receives error reports when something breaks, with
            authentication headers and cookies stripped before anything is sent
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="How your API key is protected">
        <p>
          Your Anthropic API key is encrypted at rest using envelope encryption before it ever
          touches our database. It&rsquo;s decrypted only in memory, only for the duration of a
          generation request, and is never written to logs or error reports.
        </p>
      </LegalSection>

      <LegalSection heading="Data isolation">
        <p>
          Every user&rsquo;s data is isolated at the database level using row-level security —
          your rows are enforced as invisible to every other user&rsquo;s queries, not just hidden
          by application logic.
        </p>
      </LegalSection>

      <LegalSection heading="Data export and deletion">
        <p>
          You can request a full export of your data (profile, job history, generated documents)
          at any time from your account settings — you&rsquo;ll get an email when it&rsquo;s ready
          to download. Requesting account deletion starts a 7-day grace period, during which you
          can cancel; after that, your account and all associated data are permanently deleted.
        </p>
      </LegalSection>

      <LegalSection heading="Abuse prevention">
        <p>
          We apply a daily cap on generations per account and monitor for unusual generation
          bursts — both aimed at protecting you if your API key is ever compromised, and protecting
          the service from abuse. This is plain request counting; no AI is involved in this
          monitoring, and it never inspects the content of what you generate.
        </p>
      </LegalSection>

      <LegalSection heading="Changes to this policy">
        <p>
          We may update this policy as CareerOS changes. If we make material changes to how we
          handle your data, we&rsquo;ll make a reasonable effort to notify active users.
        </p>
      </LegalSection>

      <LegalSection heading="Contact">
        <p>Questions about this policy — reach out via the sign-in email associated with CareerOS.</p>
      </LegalSection>
    </LegalPageShell>
  )
}
