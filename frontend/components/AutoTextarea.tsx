'use client'

import {
  forwardRef,
  useCallback,
  useEffect,
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
  ({ onChange, value, style, ...props }, forwardedRef) => {
    const innerRef = useRef<HTMLTextAreaElement | null>(null)

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
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight}px`
    }, [])

    // Resize whenever value changes (covers external changes, e.g. sessionStorage restore)
    useEffect(() => {
      resize()
    }, [value, resize])

    return (
      <textarea
        ref={setRef}
        value={value}
        onChange={e => {
          onChange?.(e)
          resize()
        }}
        style={{ resize: 'none', overflow: 'hidden', ...style }}
        {...props}
      />
    )
  },
)

AutoTextarea.displayName = 'AutoTextarea'
