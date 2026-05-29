/**
 * Shared utility functions.
 */

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
