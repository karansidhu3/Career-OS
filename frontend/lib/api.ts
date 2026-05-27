const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Job {
  id: number
  title: string
  company: string | null
  description: string | null
  url: string | null
  created_at: string | null
  status: string
  fit_score: number | null
  fit_rationale: string[] | null
  resume_latex: string | null
  cover_letter: string | null
}

export interface GenerateRequest {
  description: string
  title?: string
  company?: string
  url?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  generate: (body: GenerateRequest) =>
    request<Job>('/admin/jobs/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  listJobs: () => request<Job[]>('/admin/jobs'),

  getJob: (id: number) => request<Job>(`/admin/jobs/${id}`),

  updateStatus: (id: number, status: string) =>
    request<Job>(`/admin/jobs/${id}/status?status=${status}`, { method: 'PATCH' }),
}
