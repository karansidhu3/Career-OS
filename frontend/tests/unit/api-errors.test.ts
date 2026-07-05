import { describe, it, expect } from 'vitest'
import { extractErrorMessage } from '@/lib/api'

// extractErrorMessage guards against FastAPI's two different error shapes:
// {"detail": "some message"} for HTTPException, and
// {"detail": [{"msg": "...", ...}, ...]} for Pydantic 422 validation failures.
// Rendering the latter directly as a React child used to crash with
// "Objects are not valid as a React child" — this is the fix for that.

describe('extractErrorMessage', () => {
  it('returns a plain string detail as-is', () => {
    const e = new Error(JSON.stringify({ detail: 'Invalid Anthropic API key.' }))
    expect(extractErrorMessage(e, 'fallback')).toBe('Invalid Anthropic API key.')
  })

  it('flattens a Pydantic validation-error array into a readable string', () => {
    const e = new Error(
      JSON.stringify({
        detail: [
          { type: 'string_too_long', loc: ['body', 'api_key'], msg: 'String should have at most 500 characters' },
        ],
      })
    )
    expect(extractErrorMessage(e, 'fallback')).toBe('String should have at most 500 characters')
  })

  it('joins multiple validation errors', () => {
    const e = new Error(
      JSON.stringify({
        detail: [
          { msg: 'first problem' },
          { msg: 'second problem' },
        ],
      })
    )
    expect(extractErrorMessage(e, 'fallback')).toBe('first problem; second problem')
  })

  it('falls back to the default message for an empty validation array', () => {
    const e = new Error(JSON.stringify({ detail: [] }))
    expect(extractErrorMessage(e, 'fallback')).toBe('fallback')
  })

  it('returns raw text when the error body is not JSON', () => {
    const e = new Error('Internal Server Error')
    expect(extractErrorMessage(e, 'fallback')).toBe('Internal Server Error')
  })

  it('falls back when the error is not an Error instance', () => {
    expect(extractErrorMessage('not an error', 'fallback')).toBe('fallback')
  })
})
