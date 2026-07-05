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
    // Pasting moves the caret to the end of the inserted text. That caret is
    // clipped out of view by overflow: hidden at the old (shorter) height —
    // resizing is what un-clips it and makes its line geometrically visible
    // for the first time. If the field is still focused at that instant, the
    // browser decides right then to scroll that newly-revealed line into
    // view, which is why it snaps to the last pasted sentence rather than
    // the true bottom of the page. Blurring after resize is too late — the
    // decision was already made during the height change. Blur BEFORE
    // resize instead, so there's no caret to reveal when the box grows.
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
      if (didPaste.current) {
        didPaste.current = false
        innerRef.current?.blur()
        resize()
        if (pastedScrollY.current !== null) {
          window.scrollTo(0, pastedScrollY.current)
          pastedScrollY.current = null
        }
      } else {
        resize()
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
