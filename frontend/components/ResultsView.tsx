'use client'

import { useState } from 'react'
import { api, Job } from '@/lib/api'
import { CopyButton } from './CopyButton'
import { ScoreBadge } from './ScoreBadge'

interface Props {
  job: Job
  onStatusChange: (updated: Job) => void
}

export function ResultsView({ job, onStatusChange }: Props) {
  const [updating, setUpdating] = useState(false)

  const handleStatus = async (status: string) => {
    setUpdating(true)
    try {
      const updated = await api.updateStatus(job.id, status)
      onStatusChange(updated)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">{job.title}</h2>
          {job.company && <p className="text-sm text-zinc-400 mt-0.5">{job.company}</p>}
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 mt-0.5 block"
            >
              {job.url}
            </a>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {job.status === 'generated' && (
            <>
              <button
                onClick={() => handleStatus('applied')}
                disabled={updating}
                className="px-3 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 transition-colors"
              >
                ✓ Applied
              </button>
              <button
                onClick={() => handleStatus('skipped')}
                disabled={updating}
                className="px-3 py-1.5 text-xs rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-300 disabled:opacity-40 transition-colors"
              >
                Skip
              </button>
            </>
          )}
          {job.status !== 'generated' && (
            <span className="text-xs text-zinc-400 capitalize">{job.status}</span>
          )}
        </div>
      </div>

      {/* Fit score */}
      {job.fit_score != null && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-medium text-zinc-300">Fit Score</span>
            <ScoreBadge score={job.fit_score} />
          </div>
          {job.fit_rationale && (
            <ul className="space-y-1.5">
              {job.fit_rationale.map((bullet, i) => (
                <li key={i} className="flex gap-2 text-sm text-zinc-400">
                  <span className="text-zinc-600 shrink-0">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Resume LaTeX */}
      {job.resume_latex && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
            <span className="text-sm font-medium text-zinc-300">Resume (LaTeX)</span>
            <CopyButton text={job.resume_latex} label="Copy .tex" />
          </div>
          <pre className="px-4 py-4 text-xs text-zinc-400 overflow-x-auto max-h-96 leading-relaxed font-mono">
            {job.resume_latex}
          </pre>
        </div>
      )}

      {/* Cover letter */}
      {job.cover_letter && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
            <span className="text-sm font-medium text-zinc-300">Cover Letter</span>
            <CopyButton text={job.cover_letter} label="Copy" />
          </div>
          <div className="px-4 py-4 text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
            {job.cover_letter}
          </div>
        </div>
      )}
    </div>
  )
}
