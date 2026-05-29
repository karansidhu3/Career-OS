/**
 * Shared utility functions.
 */

// ─── Strategic note parsing ──────────────────────────────────────────────────

export interface AnalysisSections {
  goodFit: string[]
  gaps: string[]
  plan: string[]
}

/**
 * Parse a structured strategic_note into three sections.
 * Returns null when the note is plain prose (old format) or missing.
 *
 * Expected format:
 *   GOOD FIT\n• bullet\n\nGAPS\n• bullet\n\nIMPROVEMENT PLAN\n• bullet
 */
export function parseStrategicNote(note: string | null | undefined): AnalysisSections | null {
  if (!note) return null
  if (!note.includes('GOOD FIT') && !note.includes('GAPS')) return null

  const parseBullets = (text: string): string[] =>
    text
      .split('\n')
      .map(l => l.replace(/^[•\-\*]\s*/, '').trim())
      .filter(Boolean)

  const goodFitMatch = note.match(/GOOD FIT\n([\s\S]*?)(?=\n\nGAPS|\n\nIMPROVEMENT|$)/)
  const gapsMatch    = note.match(/GAPS\n([\s\S]*?)(?=\n\nIMPROVEMENT PLAN|$)/)
  const planMatch    = note.match(/IMPROVEMENT PLAN\n([\s\S]*?)$/)

  const result: AnalysisSections = {
    goodFit: goodFitMatch ? parseBullets(goodFitMatch[1]) : [],
    gaps:    gapsMatch    ? parseBullets(gapsMatch[1])    : [],
    plan:    planMatch    ? parseBullets(planMatch[1])    : [],
  }

  if (!result.goodFit.length && !result.gaps.length && !result.plan.length) return null
  return result
}

// ─── Dates ───────────────────────────────────────────────────────────────────

/**
 * Returns a human-readable relative date string.
 * e.g. "Just now", "3h ago", "Yesterday", "2w ago", "Jan 5"
 */
export function relativeDate(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return mins <= 1 ? 'Just now' : `${mins}m ago`
  const hrs = Math.floor(diff / 3600000)
  if (hrs < 24) return hrs === 1 ? '1h ago' : `${hrs}h ago`
  const days = Math.floor(diff / 86400000)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
