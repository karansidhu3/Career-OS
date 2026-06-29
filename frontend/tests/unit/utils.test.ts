import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { parseStrategicNote, relativeDate } from '@/lib/utils'

// ── parseStrategicNote ────────────────────────────────────────────────────────

describe('parseStrategicNote', () => {
  it('returns null for null input', () => {
    expect(parseStrategicNote(null)).toBeNull()
  })

  it('returns null for undefined input', () => {
    expect(parseStrategicNote(undefined)).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(parseStrategicNote('')).toBeNull()
  })

  it('returns null for plain prose without section headers', () => {
    expect(parseStrategicNote('This candidate has strong Python skills.')).toBeNull()
  })

  it('parses all three sections from a complete note', () => {
    const note = [
      'GOOD FIT',
      '• Strong Python background',
      '• FastAPI experience matches JD',
      '',
      'GAPS',
      '• No Rust experience',
      '',
      'IMPROVEMENT PLAN',
      '• Build a Rust CLI project',
    ].join('\n')

    const result = parseStrategicNote(note)
    expect(result).not.toBeNull()
    expect(result!.goodFit).toHaveLength(2)
    expect(result!.gaps).toHaveLength(1)
    expect(result!.plan).toHaveLength(1)
  })

  it('strips leading bullet markers from items', () => {
    const note = 'GOOD FIT\n• Has FastAPI\n- Also React\n* And Postgres'
    const result = parseStrategicNote(note)
    expect(result!.goodFit).toContain('Has FastAPI')
    expect(result!.goodFit).toContain('Also React')
    expect(result!.goodFit).toContain('And Postgres')
  })

  it('returns empty gaps array when GAPS section is absent', () => {
    const note = 'GOOD FIT\n• Strong match\n\nIMPROVEMENT PLAN\n• Learn Rust'
    const result = parseStrategicNote(note)
    expect(result!.gaps).toHaveLength(0)
    expect(result!.goodFit).toHaveLength(1)
    expect(result!.plan).toHaveLength(1)
  })

  it('returns empty plan array when IMPROVEMENT PLAN section is absent', () => {
    const note = 'GOOD FIT\n• Great fit\n\nGAPS\n• Missing Kubernetes'
    const result = parseStrategicNote(note)
    expect(result!.plan).toHaveLength(0)
    expect(result!.goodFit).toHaveLength(1)
    expect(result!.gaps).toHaveLength(1)
  })

  it('handles a note with only one non-empty section', () => {
    // Only GAPS has content; GOOD FIT and IMPROVEMENT PLAN sections are absent
    const note = 'GAPS\n• Missing Kubernetes experience'
    const result = parseStrategicNote(note)
    // Without the GOOD FIT header the regex won't match goodFit at all
    expect(result!.gaps).toHaveLength(1)
    expect(result!.gaps[0]).toBe('Missing Kubernetes experience')
  })

  it('filters out blank lines within sections', () => {
    const note = 'GOOD FIT\n• Bullet one\n\n• Bullet two\n\nGAPS\n• Gap one'
    const result = parseStrategicNote(note)
    // blank lines between bullets should not appear as empty strings
    expect(result!.goodFit.every(s => s.length > 0)).toBe(true)
  })

  it('handles note with only GOOD FIT section', () => {
    const note = 'GOOD FIT\n• Strong Python skills'
    const result = parseStrategicNote(note)
    expect(result!.goodFit).toHaveLength(1)
    expect(result!.gaps).toHaveLength(0)
    expect(result!.plan).toHaveLength(0)
  })

  it('preserves the text content of bullets exactly', () => {
    const note = 'GOOD FIT\n• 5+ years FastAPI, PostgreSQL, async Python'
    const result = parseStrategicNote(note)
    expect(result!.goodFit[0]).toBe('5+ years FastAPI, PostgreSQL, async Python')
  })
})

// ── relativeDate ──────────────────────────────────────────────────────────────

describe('relativeDate', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  const setNow = (isoString: string) => vi.setSystemTime(new Date(isoString))

  it('returns "Just now" for 0 seconds ago', () => {
    setNow('2026-01-01T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('Just now')
  })

  it('returns "Just now" for 30 seconds ago', () => {
    setNow('2026-01-01T12:00:30Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('Just now')
  })

  it('returns "Just now" for exactly 1 minute ago', () => {
    setNow('2026-01-01T12:01:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('Just now')
  })

  it('returns "Xm ago" for 2 minutes ago', () => {
    setNow('2026-01-01T12:02:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('2m ago')
  })

  it('returns "59m ago" for 59 minutes ago', () => {
    setNow('2026-01-01T12:59:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('59m ago')
  })

  it('returns "1h ago" for exactly 1 hour ago', () => {
    setNow('2026-01-01T13:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('1h ago')
  })

  it('returns "3h ago" for 3 hours ago', () => {
    setNow('2026-01-01T15:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('3h ago')
  })

  it('returns "Yesterday" for 1 day ago', () => {
    setNow('2026-01-02T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('Yesterday')
  })

  it('returns "Xd ago" for 3 days ago', () => {
    setNow('2026-01-04T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('3d ago')
  })

  it('returns "Xd ago" for 6 days ago', () => {
    setNow('2026-01-07T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('6d ago')
  })

  it('returns "1w ago" for 7 days ago', () => {
    setNow('2026-01-08T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('1w ago')
  })

  it('returns "4w ago" for 29 days ago', () => {
    setNow('2026-01-30T12:00:00Z')
    expect(relativeDate('2026-01-01T12:00:00Z')).toBe('4w ago')
  })

  it('returns a formatted date for 30+ days ago', () => {
    setNow('2026-02-05T12:00:00Z')
    const result = relativeDate('2026-01-01T12:00:00Z')
    // Should be a formatted date like "Jan 1"
    expect(result).toMatch(/Jan/)
    expect(result).toMatch(/1/)
  })
})
