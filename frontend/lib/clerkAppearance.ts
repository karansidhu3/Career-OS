// Shared Clerk appearance config — without this, <SignIn>/<SignUp> render with
// Clerk's stock theme (generic blue, default radii) instead of the app's ink
// accent and warm-neutral surfaces. CSS custom property references (var(--c-*))
// resolve against the same :root as the rest of the app, so this also picks up
// the existing light/dark redefinitions in globals.css for free.
export const clerkAppearance = {
  variables: {
    colorPrimary: 'var(--c-accent)',
    colorBackground: 'transparent',
    colorInputBackground: 'rgba(0,0,0,0.03)',
    colorInputText: '#1C1C1E',
    colorText: '#1C1C1E',
    colorTextSecondary: '#71717A',
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
