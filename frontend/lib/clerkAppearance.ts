// Shared Clerk appearance config — without this, <SignIn>/<SignUp>/<UserButton>
// render with Clerk's stock light theme (generic blue, white cards) instead of
// the app's ink accent and dark surfaces. Applied once at the ClerkProvider
// level so it covers every Clerk component, including UserButton's dropdown
// and "Manage account" modal.
export const clerkAppearance = {
  variables: {
    colorPrimary: 'var(--c-accent)',
    colorBackground: 'transparent',
    colorInputBackground: 'rgba(255,255,255,0.06)',
    colorInputText: '#EDEDE8',
    colorText: '#EDEDE8',
    colorTextSecondary: 'rgba(255,255,255,0.5)',
    colorNeutral: '#EDEDE8',
    colorDanger: 'var(--c-danger)',
    colorSuccess: 'var(--c-success)',
    colorWarning: 'var(--c-warn)',
    borderRadius: '0.75rem',
  },
  elements: {
    card: {
      boxShadow: 'var(--c-glass-shadow)',
      border: '1px solid var(--c-border)',
      backgroundColor: 'var(--c-glass-bg)',
      backdropFilter: 'blur(20px)',
    },
    formButtonPrimary: {
      backgroundImage: 'var(--c-btn-bg)',
      boxShadow: 'var(--c-btn-shadow)',
      fontSize: '0.875rem',
      fontWeight: 600,
      textTransform: 'none',
      '&:hover': { opacity: 0.92 },
      '&:focus': { boxShadow: 'var(--c-btn-shadow)' },
      '&:active': { opacity: 0.85 },
    },
    footerActionLink: {
      color: 'var(--c-accent)',
      textDecorationColor: 'var(--c-accent)',
    },
    formFieldInput: {
      borderRadius: '0.75rem',
    },
  },
} as const
