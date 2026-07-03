import { LegalPageShell, LegalSection } from '@/components/LegalPageShell'

export const metadata = { title: 'Terms of Service — CareerOS' }

export default function TermsPage() {
  return (
    <LegalPageShell title="Terms of Service" lastUpdated="July 2026">
      <p className="text-xs italic text-neutral-600 border-l-2 pl-3" style={{ borderColor: 'var(--c-warn)' }}>
        This is a starting draft, not a substitute for legal advice. It has not been reviewed by a
        lawyer. Do not rely on it as final before opening CareerOS to the public.
      </p>

      <LegalSection heading="1. What CareerOS is">
        <p>
          CareerOS turns a pasted job description into a tailored resume and cover letter using
          Claude, Anthropic&rsquo;s AI model. You bring your own Anthropic API key — every
          generation is billed to your own Anthropic account, not to CareerOS. We never see or pay
          for your generation costs.
        </p>
      </LegalSection>

      <LegalSection heading="2. Your account">
        <p>
          You need an account (via Clerk) to use CareerOS beyond the waitlist. You&rsquo;re
          responsible for keeping your sign-in credentials secure and for all activity under your
          account. You must be at least 18 years old to use CareerOS.
        </p>
      </LegalSection>

      <LegalSection heading="3. Your API key and generation costs">
        <p>
          You provide your own Anthropic API key, which we store encrypted and use only to
          generate materials on your behalf. You are solely responsible for any costs Anthropic
          charges you for that usage. We apply a daily generation limit and basic abuse monitoring
          to help protect your key from being drained if something goes wrong on our end, but we
          are not liable for your Anthropic billing.
        </p>
      </LegalSection>

      <LegalSection heading="4. AI-generated content">
        <p>
          Resumes, cover letters, and any analysis CareerOS generates are produced by an AI model
          and may contain errors, omissions, or inaccuracies. You are responsible for reviewing
          everything CareerOS produces before using it — for accuracy, honesty, and fitness for
          your actual background — before submitting it anywhere. CareerOS does not guarantee
          interviews, job offers, or any particular outcome from using generated materials.
        </p>
      </LegalSection>

      <LegalSection heading="5. Your content">
        <p>
          You own the profile information, job descriptions, and generated resumes/cover letters
          associated with your account. We don&rsquo;t claim ownership over anything you create or
          upload. You&rsquo;re responsible for making sure the information in your profile is
          accurate and that you have the right to use any content you paste into CareerOS.
        </p>
      </LegalSection>

      <LegalSection heading="6. Acceptable use">
        <p>You agree not to:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Use CareerOS to generate materials containing false credentials or fabricated experience</li>
          <li>Attempt to abuse, overload, or circumvent CareerOS&rsquo;s rate limits or generation caps</li>
          <li>Share your account or API key with anyone else</li>
          <li>Use CareerOS for any unlawful purpose</li>
        </ul>
      </LegalSection>

      <LegalSection heading="7. Data export and deletion">
        <p>
          You can export a copy of your data or delete your account at any time from your profile
          settings. Account deletion is final after a 7-day grace period, during which you can
          cancel the deletion. See our{' '}
          <a href="/privacy" className="underline underline-offset-2">Privacy Policy</a> for what
          we store and how deletion actually works.
        </p>
      </LegalSection>

      <LegalSection heading="8. No warranty; limitation of liability">
        <p>
          CareerOS is provided &ldquo;as is,&rdquo; without warranties of any kind. We do not
          guarantee uninterrupted or error-free service. To the fullest extent permitted by law,
          CareerOS and its operator are not liable for any indirect, incidental, or consequential
          damages arising from your use of the service, including any Anthropic API charges,
          missed job opportunities, or inaccuracies in generated content.
        </p>
      </LegalSection>

      <LegalSection heading="9. Changes to these terms">
        <p>
          We may update these terms as CareerOS changes. If we make material changes, we&rsquo;ll
          make a reasonable effort to notify active users. Continued use after a change means you
          accept the updated terms.
        </p>
      </LegalSection>

      <LegalSection heading="10. Contact">
        <p>Questions about these terms — reach out via the sign-in email associated with CareerOS.</p>
      </LegalSection>
    </LegalPageShell>
  )
}
