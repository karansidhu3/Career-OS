/**
 * Spring constants for Framer Motion.
 * All animation in the product uses spring physics — not ease curves.
 *
 * standard — cards, panels, section reveals
 * gentle   — page-level transitions, large reveals
 * snappy   — micro-interactions, toggles, popovers
 * bouncy   — celebration moments only (interview/offer)
 */
export const spring = {
  standard: { type: 'spring' as const, stiffness: 320, damping: 30 },
  gentle:   { type: 'spring' as const, stiffness: 180, damping: 26 },
  snappy:   { type: 'spring' as const, stiffness: 520, damping: 32 },
  bouncy:   { type: 'spring' as const, stiffness: 420, damping: 14 },
  // heavy — large surface arrivals (sticky PDF pane, full-page transitions)
  heavy:    { type: 'spring' as const, stiffness: 140, damping: 22 },
  // micro — button tap response, badge pop, fine interaction feedback
  micro:    { type: 'spring' as const, stiffness: 680, damping: 36 },
}
