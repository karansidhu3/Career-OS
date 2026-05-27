'use client'

import { useState } from 'react'

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200"
      style={{
        background: copied ? 'rgba(16,185,129,0.08)' : 'rgba(0,0,0,0.04)',
        border: `1px solid ${copied ? 'rgba(16,185,129,0.2)' : 'rgba(0,0,0,0.06)'}`,
        color: copied ? '#059669' : '#6b7280',
      }}
    >
      {copied ? '✓ Copied' : label}
    </button>
  )
}
