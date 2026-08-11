import { describe, expect, it } from 'vitest'
import { generationFailureMessage } from '@/lib/generationErrors'

describe('generationFailureMessage', () => {
  it('does not mislabel a configuration error as a timeout', () => {
    expect(generationFailureMessage({ failure_code: 'generation_configuration' }))
      .toBe('Generation hit a configuration error. The app needs an update before retrying.')
  })

  it('uses a timeout message only for an actual timeout', () => {
    expect(generationFailureMessage({ failure_code: 'anthropic_timeout' }))
      .toBe('Claude took too long to respond. Try again.')
  })

  it('falls back safely for old failed jobs without metadata', () => {
    expect(generationFailureMessage(null)).toBe('Generation failed unexpectedly. Try again.')
  })
})
