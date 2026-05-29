/**
 * BrandMark — CareerOS geometric ring mark.
 * A single thin-stroke circle. Renders consistently at any size.
 * strokeWidth defaults to 1.75px physical, calculated from viewBox.
 */
export function BrandMark({
  size = 14,
  physicalStroke = 1.75,
  className,
  style,
}: {
  size?: number
  physicalStroke?: number
  className?: string
  style?: React.CSSProperties
}) {
  const r = size * 0.375        // radius = 37.5% of size
  const c = size / 2            // center
  const sw = physicalStroke     // stroke width in px (same viewBox scale)

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={sw}
      className={className}
      style={style}
    >
      <circle cx={c} cy={c} r={r} />
    </svg>
  )
}
