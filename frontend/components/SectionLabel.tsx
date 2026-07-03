/**
 * SectionLabel — consistent section heading treatment across all surfaces.
 * 11px, medium weight, uppercase, tracked. The product's quietest voice.
 *
 * Use `className` to override color or add spacing (e.g. className="text-amber-400 px-4 mb-1").
 * Use `style` for one-off overrides (e.g. style={{ color: 'var(--c-warn)' }}).
 */
export function SectionLabel({
  children,
  className,
  style,
}: {
  children: React.ReactNode
  className?: string
  style?: React.CSSProperties
}) {
  return (
    <p
      className={`text-[11px] font-medium uppercase tracking-[0.07em] text-neutral-600 ${className ?? ''}`}
      style={style}
    >
      {children}
    </p>
  )
}
