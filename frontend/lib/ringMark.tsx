// Shared visual for generated app icons (favicon, apple-touch-icon, PWA
// manifest icons) — the same ring as components/BrandMark.tsx, rendered as a
// filled square so it reads correctly as a standalone app icon rather than
// a mark meant to sit on an existing page background.
export function ringIcon(diameter: number, stroke: number) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: '#111110',
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
        }}
      />
    </div>
  )
}
