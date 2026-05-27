'use client'

import { Job } from '@/lib/api'
import { ScoreBadge } from './ScoreBadge'

const STATUS_STYLES: Record<string, string> = {
  generated: 'bg-zinc-700 text-zinc-300',
  applied: 'bg-indigo-500/20 text-indigo-400',
  skipped: 'bg-zinc-800 text-zinc-500',
}

interface Props {
  jobs: Job[]
  selectedId: number | null
  onSelect: (id: number) => void
  onNew: () => void
}

export function Sidebar({ jobs, selectedId, onSelect, onNew }: Props) {
  return (
    <aside className="w-72 shrink-0 flex flex-col border-r border-zinc-800 bg-zinc-950 overflow-hidden">
      <div className="px-4 py-4 border-b border-zinc-800 flex items-center justify-between">
        <span className="text-sm font-semibold text-zinc-100 tracking-wide">CareerOS</span>
        <button
          onClick={onNew}
          className="text-xs px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          + New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {jobs.length === 0 && (
          <p className="px-4 py-6 text-sm text-zinc-500">No applications yet. Paste a JD to get started.</p>
        )}
        {jobs.map((job) => (
          <button
            key={job.id}
            onClick={() => onSelect(job.id)}
            className={`w-full text-left px-4 py-3 border-b border-zinc-800/50 hover:bg-zinc-900 transition-colors ${
              selectedId === job.id ? 'bg-zinc-900' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-zinc-100 truncate">{job.title}</p>
                {job.company && (
                  <p className="text-xs text-zinc-400 truncate mt-0.5">{job.company}</p>
                )}
              </div>
              {job.fit_score != null && <ScoreBadge score={job.fit_score} />}
            </div>
            <div className="flex items-center justify-between mt-1.5">
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${STATUS_STYLES[job.status] ?? STATUS_STYLES.generated}`}
              >
                {job.status}
              </span>
              {job.created_at && (
                <span className="text-xs text-zinc-600">
                  {new Date(job.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>
    </aside>
  )
}
