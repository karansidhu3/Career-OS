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
    // Pasting moves the caret to the end of the inserted text and leaves the
    // field focused, so the browser keeps chasing that caret to keep it in
    // view as the box grows — a one-time scroll restore isn't enough because
    // the browser can re-assert "keep the focused caret visible" on a later
    // tick, after our restore already ran. Blurring removes the thing being
    // chased: no caret is being tracked, so there's nothing to scroll toward.
    const pastedScrollY = useRef<number | null>(null)
    const didPaste = useRef(false)

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
      if (didPaste.current) {
        didPaste.current = false
        innerRef.current?.blur()
        if (pastedScrollY.current !== null) {
          window.scrollTo(0, pastedScrollY.current)
          pastedScrollY.current = null
        }
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
          didPaste.current = true
          onPaste?.(e)
        }}
        style={{ resize: 'none', overflow: 'hidden', ...style }}
        {...props}
      />
    )
  },
)

AutoTextarea.displayName = 'AutoTextarea'
