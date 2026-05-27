'use client'

import { useState } from 'react'
import { api, GenerateRequest, Job } from '@/lib/api'

interface Props {
  onGenerated: (job: Job) => void
}

export function GenerateForm({ onGenerated }: Props) {
  const [description, setDescription] = useState('')
  const [title, setTitle] = useState('')
  const [company, setCompany] = useState('')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) return
    setLoading(true)
    setError(null)
    try {
      const req: GenerateRequest = { description: description.trim() }
      if (title.trim()) req.title = title.trim()
      if (company.trim()) req.company = company.trim()
      if (url.trim()) req.url = url.trim()
      const job = await api.generate(req)
      onGenerated(job)
      setDescription('')
      setTitle('')
      setCompany('')
      setUrl('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 h-full">
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Role title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
        />
        <input
          type="text"
          placeholder="Company (optional)"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
        />
        <input
          type="url"
          placeholder="Job URL (optional)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
        />
      </div>

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Paste the full job description here…"
        className="flex-1 min-h-64 px-4 py-3 text-sm rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500 resize-none font-mono leading-relaxed"
        disabled={loading}
      />

      {error && (
        <p className="text-sm text-red-400 bg-red-400/10 px-3 py-2 rounded-lg">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading || !description.trim()}
        className="self-end px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Generating…
          </span>
        ) : (
          'Generate →'
        )}
      </button>
    </form>
  )
}
