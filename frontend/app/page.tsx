'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, Job } from '@/lib/api'
import { Sidebar } from '@/components/Sidebar'
import { GenerateForm } from '@/components/GenerateForm'
import { ResultsView } from '@/components/ResultsView'

type View = 'form' | 'results'

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [view, setView] = useState<View>('form')

  const loadJobs = useCallback(async () => {
    try {
      const data = await api.listJobs()
      setJobs(data)
    } catch {
      // backend not running — silently skip
    }
  }, [])

  useEffect(() => { loadJobs() }, [loadJobs])

  const handleGenerated = (job: Job) => {
    setJobs((prev) => [job, ...prev])
    setSelectedJob(job)
    setView('results')
  }

  const handleSelect = async (id: number) => {
    const job = jobs.find((j) => j.id === id) ?? null
    setSelectedJob(job)
    setView('results')
    // Fetch full job in case description/materials were trimmed in list
    try {
      const full = await api.getJob(id)
      setSelectedJob(full)
    } catch { /* ignore */ }
  }

  const handleStatusChange = (updated: Job) => {
    setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)))
    setSelectedJob(updated)
  }

  const handleNew = () => {
    setSelectedJob(null)
    setView('form')
  }

  return (
    <div className="flex h-full">
      <Sidebar
        jobs={jobs}
        selectedId={selectedJob?.id ?? null}
        onSelect={handleSelect}
        onNew={handleNew}
      />

      <main className="flex-1 overflow-y-auto p-8">
        {view === 'form' && (
          <div className="max-w-3xl mx-auto h-full flex flex-col gap-6">
            <div>
              <h1 className="text-xl font-semibold text-zinc-100">New Application</h1>
              <p className="text-sm text-zinc-400 mt-1">
                Paste a job description and hit Generate. Takes ~15 seconds.
              </p>
            </div>
            <div className="flex-1">
              <GenerateForm onGenerated={handleGenerated} />
            </div>
          </div>
        )}

        {view === 'results' && selectedJob && (
          <div className="max-w-3xl mx-auto">
            <button
              onClick={handleNew}
              className="text-sm text-zinc-500 hover:text-zinc-300 mb-6 transition-colors"
            >
              ← New application
            </button>
            <ResultsView job={selectedJob} onStatusChange={handleStatusChange} />
          </div>
        )}
      </main>
    </div>
  )
}
