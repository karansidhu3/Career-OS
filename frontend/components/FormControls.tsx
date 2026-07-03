'use client'

// ---- Shared form primitives ----
// Canonical input/button treatment used across settings, onboarding, and
// account management. Previously copy-pasted independently in ApiKeySettings,
// ProfileSetupGate, the profile page, LandingPage, and AccountDeletion — this
// is the single source those now import from.

export const inputCls =
  "form-input w-full px-3 py-2 rounded-xl text-sm text-neutral-700 placeholder-neutral-300 focus:outline-none"
export const inputStyle = { background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.07)' }

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
      {children}
    </div>
  )
}

export function Input({
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={inputCls}
      style={inputStyle}
    />
  )
}

// Large primary CTA — onboarding steps, main result-state actions
// (Download Resume, Try Again, Continue, Save profile).
export function PrimaryButton({
  children,
  onClick,
  disabled,
  type = 'button',
  fullWidth = false,
}: {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  type?: 'button' | 'submit'
  fullWidth?: boolean
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${fullWidth ? 'w-full' : ''} px-5 py-2.5 rounded-2xl text-sm font-semibold text-white disabled:opacity-40 transition-all`}
      style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
    >
      {children}
    </button>
  )
}

// Compact save action — inline within a settings section (API key, profile
// field edits, account deletion). Deliberately smaller than PrimaryButton —
// this is a second, intentional size tier, not a drifted version of the first.
export function SaveButton({
  saving,
  onClick,
  disabled,
  children = 'Save',
  savingLabel = 'Saving…',
}: {
  saving: boolean
  onClick: () => void
  disabled?: boolean
  children?: React.ReactNode
  savingLabel?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={saving || disabled}
      className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all"
      style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
    >
      {saving ? savingLabel : children}
    </button>
  )
}

export function CancelButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-1.5 rounded-xl text-xs font-medium text-neutral-400 hover:text-neutral-600 transition-colors"
    >
      Cancel
    </button>
  )
}
