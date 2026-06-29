import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCountUp } from '@/lib/hooks'

describe('useCountUp', () => {
  let rafCallback: FrameRequestCallback | null = null
  let mockNow: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // Control requestAnimationFrame manually so we can advance time in tests.
    // Each call to rafCallback(timestamp) drives one animation tick.
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      rafCallback = cb
      return 1
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})
    mockNow = vi.spyOn(performance, 'now').mockReturnValue(0)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    rafCallback = null
  })

  it('starts at 0 before any animation frame fires', () => {
    const { result } = renderHook(() => useCountUp(8, 700))
    // Before RAF fires, current should be 0
    expect(result.current).toBe(0)
  })

  it('returns 0 immediately when target is 0', () => {
    const { result } = renderHook(() => useCountUp(0, 700))
    expect(result.current).toBe(0)
  })

  it('progresses toward target mid-animation', () => {
    const { result } = renderHook(() => useCountUp(10, 700))

    // Fire RAF at 50% of duration
    act(() => {
      mockNow.mockReturnValue(350)
      rafCallback?.(350)
    })

    expect(result.current).toBeGreaterThan(0)
    expect(result.current).toBeLessThan(10)
  })

  it('reaches exact target at end of duration', () => {
    const { result } = renderHook(() => useCountUp(10, 700))

    // Fire RAF at 100% of duration
    act(() => {
      mockNow.mockReturnValue(700)
      rafCallback?.(700)
    })

    expect(result.current).toBe(10)
  })

  it('reaches target when duration is exceeded', () => {
    const { result } = renderHook(() => useCountUp(7, 700))

    act(() => {
      mockNow.mockReturnValue(1000)
      rafCallback?.(1000)
    })

    expect(result.current).toBe(7)
  })

  it('resets and re-animates when target changes', () => {
    const { result, rerender } = renderHook(
      ({ target }: { target: number }) => useCountUp(target, 700),
      { initialProps: { target: 8 } }
    )

    // Complete first animation
    act(() => {
      mockNow.mockReturnValue(700)
      rafCallback?.(700)
    })
    expect(result.current).toBe(8)

    // Reset clock before rerender so the new effect captures start=0, not 700
    mockNow.mockReturnValue(0)
    rerender({ target: 5 })
    // Fire at 50% of the new animation
    act(() => {
      rafCallback?.(350)
    })
    expect(result.current).toBeGreaterThanOrEqual(0)
    expect(result.current).toBeLessThanOrEqual(5)
  })

  it('rounds to the nearest integer at each frame', () => {
    const { result } = renderHook(() => useCountUp(7, 700))

    act(() => {
      mockNow.mockReturnValue(350)
      rafCallback?.(350)
    })

    // current must be a whole number (useCountUp uses Math.round)
    expect(Number.isInteger(result.current)).toBe(true)
  })
})
