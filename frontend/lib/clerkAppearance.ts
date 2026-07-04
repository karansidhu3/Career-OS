import { dark } from '@clerk/themes'

// Shared Clerk appearance config — without this, <SignIn>/<SignUp>/<UserButton>
// render with Clerk's stock light theme (generic blue, white cards) instead of
// the app's ink accent and dark surfaces. Applied once at the ClerkProvider
// level so it covers every Clerk component, including UserButton's dropdown
// and "Manage account" modal.
//
// baseTheme: dark is load-bearing, not decorative. Clerk's internal components
// (nav tabs, modal close button, section titles, device-session rows, etc.)
// don't all derive their text color from the top-level `variables` — several
// hardcode a light-mode-only default that only `dark` (Clerk's own maintained
// dark palette) actually overrides everywhere. Hand-patching each broken
// element via `elements` chased new instances of the same bug every time a
// different Clerk screen was opened (Security tab, session list, etc.) — using
// their real dark theme as the base fixes the whole component tree at once.
// Our own `variables`/`elements` below layer the app's ink accent and glass
// card treatment on top of that base.
export const clerkAppearance = {
  baseTheme: dark,
  variables: {
    colorPrimary: 'var(--c-accent)',
    // A real dark color, not literal 'transparent' — Clerk computes some
    // element text colors (headerTitle, profileSectionTitleText, etc.) via
    // automatic contrast against this value, and a literal 'transparent'
    // apparently reads as "light" to that calculation, producing black-on-
    // black text. The actual visible glass background comes from the `card`
    // element's own backgroundColor override below, so this only needs to be
    // representative for contrast math, not the real rendered color.
    colorBackground: '#141412',
    colorInputBackground: 'rgba(255,255,255,0.06)',
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
