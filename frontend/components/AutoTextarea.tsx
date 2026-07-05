'use client'

import {
  forwardRef,
  useCallback,
  useLayoutEffect,
  useRef,
  type TextareaHTMLAttributes,
  type MutableRefObject,
} from 'react'

export type AutoTextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

/**
 * A textarea that grows with its content.
 * Drops the `rows` attribute — use `style.minHeight` for the floor size.
 */
export const AutoTextarea = forwardRef<HTMLTextAreaElement, AutoTextareaProps>(
  ({ onChange, onPaste, value, style, ...props }, forwardedRef) => {
    const innerRef = useRef<HTMLTextAreaElement | null>(null)
    // Pasting long text ends with the browser scrolling the page down to the
    // pasted caret's line. Neither preventing it (blur/reorder) nor reacting
    // to a 'scroll' event caught it reliably — whatever the browser does here
    // doesn't consistently surface as a single observable event. Polling via
    // rAF sidesteps that: it doesn't wait to be notified, it just re-asserts
    // the pre-paste position on every rendered frame for a short window,
    // so it catches the drift regardless of how or when it happens.
    const pastedScrollY = useRef<number | null>(null)
    const lockFrames = useRef(0)

    const pollScroll = useCallback(() => {
      if (lockFrames.current <= 0 || pastedScrollY.current === null) return
      lockFrames.current -= 1
      if (window.scrollY !== pastedScrollY.current) {
        window.scrollTo(0, pastedScrollY.current)
      }
      if (lockFrames.current > 0) {
        requestAnimationFrame(pollScroll)
      } else {
        pastedScrollY.current = null
      }
    }, [])

    // Merge the forwarded ref with our internal ref
    const setRef = useCallback(
      (node: HTMLTextAreaElement | null) => {
        innerRef.current = node
        if (typeof forwardedRef === 'function') {
          forwardedRef(node)
        } else if (forwardedRef) {
          ;(forwardedRef as MutableRefObject<HTMLTextAreaElement | null>).current = node
        }
      },
      [forwardedRef],
    )

    const resize = useCallback(() => {
      const el = innerRef.current
      if (!el) return
      // Set to 0 first — 'auto' doesn't force a reflow before scrollHeight is read,
      // causing it to return a stale large value. 0px makes scrollHeight content-only.
      el.style.height = '0px'
      el.style.height = `${el.scrollHeight}px`
    }, [])

    // useLayoutEffect fires synchronously after DOM mutations, before paint.
    // This ensures layout is settled when we measure scrollHeight.
    useLayoutEffect(() => {
      resize()
    }, [value, resize])

    return (
      <textarea
        ref={setRef}
        value={value}
        rows={1}
        onChange={e => {
          onChange?.(e)
          resize()
        }}
        onPaste={e => {
          pastedScrollY.current = window.scrollY
          lockFrames.current = 30
          requestAnimationFrame(pollScroll)
          onPaste?.(e)
        }}
        style={{ resize: 'none', overflow: 'hidden', ...style }}
        {...props}
      />
    )
  },
)

AutoTextarea.displayName = 'AutoTextarea'
