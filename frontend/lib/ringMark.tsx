// Shared visual for generated app icons (favicon, apple-touch-icon, PWA
// manifest icons) — the same ring as components/BrandMark.tsx, rendered as a
// filled square so it reads correctly as a standalone app icon rather than
// a mark meant to sit on an existing page background.
//
// Background gradient matches globals.css's body rule (warm radial glow over
// near-black), boosted from its real 3.5% opacity since that's tuned for a
// full-screen ambient background, not something this small and high-contrast.
// The ring's stroke ratio and glow color match app/page.tsx's hero BrandMark
// (size 56, physicalStroke 1.5 — a ~3.6% stroke-to-diameter ratio) and its
// brand-ring-glow CSS animation, using that cycle's signature amber tone as a
// fixed glow since a still image can't cycle through the animated hues.
export function ringIcon(diameter: number, stroke: number, glow = true) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background:
          'radial-gradient(ellipse at 25% 18%, rgba(255,248,230,0.08) 0%, transparent 48%), #111110',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: diameter,
          height: diameter,
          borderRadius: '50%',
          border: `${stroke}px solid #E8E8E4`,
          ...(glow
            ? { boxShadow: `0 0 ${Math.round(diameter * 0.16)}px ${Math.round(diameter * 0.03)}px rgba(251,191,36,0.55)` }
            : {}),
        }}
      />
    </div>
  )
}
