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
    // Pasting moves the caret to the end of the inserted text, and since this
    // textarea has no internal scrollbar (overflow: hidden), the browser's
    // "scroll caret into view" behavior scrolls the whole window down to the
    // now much-taller box. Snapshot scroll position before the browser acts
    // on the paste, then restore it once the resize settles but before paint,
    // so the reader stays where they were instead of being dropped at the end.
    const pastedScrollY = useRef<number | null>(null)

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
      if (pastedScrollY.current !== null) {
        window.scrollTo(0, pastedScrollY.current)
        pastedScrollY.current = null
      }
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
          onPaste?.(e)
        }}
        style={{ resize: 'none', overflow: 'hidden', ...style }}
        {...props}
      />
    )
  },
)

AutoTextarea.displayName = 'AutoTextarea'
