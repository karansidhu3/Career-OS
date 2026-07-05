// All requests go to /api/* which Next.js proxies server-side to the backend.
// API_KEY is held server-side in the proxy route — never in the browser bundle.
const API_BASE = '/api'

// ---- Job types ----

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
  strategic_note: string | null
  selected_projects: string[] | null
  input_tokens: number | null
  output_tokens: number | null
  cache_read_tokens: number | null
  cache_write_tokens: number | null
  compression_attempts: number | null
  cost_usd: number | null
}

export interface CandidacyInsights {
  headline: string | null
  observed: string | null
  gap: string | null
  action: string | null
  count: number
}

export interface GenerateRequest {
  description: string
  url?: string
}

// ---- Profile types ----

export interface PersonalInfo {
  id: number
  name: string
  email: string
  phone: string | null
  linkedin: string | null
  github: string | null
  location: string | null
  target_roles: string[]
  target_locations: string[]
  cover_letter_voice: string
}

export interface Education {
  id: number
  school: string
  degree: string
  field: string | null
  minor: string | null
  start_date: string | null
  end_date: string | null
}

export interface Experience {
  id: number
  company: string
  role: string
  start_date: string | null
  end_date: string | null
  location: string | null
  description: string
  sort_order: number
}

export interface Project {
  id: number
  name: string
  start_date: string | null
  end_date: string | null
  github_url: string | null
  description: string
  sort_order: number
}

export interface SkillCategory {
  id: number
  category: string
  items: string[]
  sort_order: number
}

export interface FullProfile {
  personal: PersonalInfo | null
  education: Education[]
  experience: Experience[]
  projects: Project[]
  skills: SkillCategory[]
}

// ---- AI credentials (BYO API key) ----

export interface CredentialStatus {
  provider: string
  has_key: boolean
  key_hint: string | null
  label: string | null
  last_verified_at: string | null
}

// ---- Account data export (Phase 6) ----

export interface AccountExport {
  id: number
  status: string
  created_at: string | null
  completed_at: string | null
  expires_at: string | null
  error_message: string | null
}

// ---- Account deletion (Phase 6) ----

export interface AccountDeletionStatus {
  scheduled_deletion_at: string | null
}

// ---- Resume import (Phase 4) ----

export interface ImportedPersonal {
  name: string | null
  email: string | null
  phone: string | null
  linkedin: string | null
  github: string | null
  location: string | null
}

export interface ImportedEducation {
  school: string
  degree: string
  field: string | null
  minor: string | null
  start_date: string | null
  end_date: string | null
}

export interface ImportedExperience {
  company: string
  role: string
  start_date: string | null
  end_date: string | null
  location: string | null
  description: string
}

export interface ImportedProject {
  name: string
  start_date: string | null
  end_date: string | null
  github_url: string | null
  description: string
}

export interface ImportedSkillCategory {
  category: string
  items: string[]
}

export interface ProfileImportDraft {
  personal: ImportedPersonal
  education: ImportedEducation[]
  experience: ImportedExperience[]
  projects: ImportedProject[]
  skills: ImportedSkillCategory[]
}

// ---- Shared ----

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  // 204 No Content — DELETE endpoints return empty body, res.json() would throw
  if (res.status === 204) return undefined as T
  return res.json()
}

// Turns a thrown error into a displayable string, regardless of shape.
// FastAPI's error body is usually {"detail": "some message"}, but Pydantic
// validation failures (422s) instead send {"detail": [{"msg": "...", ...}, ...]}
// — rendering that array directly as a React child crashes with "Objects are
// not valid as a React child," which is what "typing garbage into a field"
// used to produce. Always resolves to a plain string.
export function extractErrorMessage(e: unknown, fallback: string): string {
  const raw = e instanceof Error ? e.message : fallback
  try {
    const parsed = JSON.parse(raw)
    const detail = parsed?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map(d => (typeof d === 'string' ? d : d?.msg)).filter(Boolean).join('; ') || fallback
    }
    return fallback
  } catch {
    return raw || fallback
  }
}

// Fetch a binary endpoint (PDF) and return an object URL.
// Caller is responsible for revoking with URL.revokeObjectURL when done.
async function requestBlob(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

// Fetch a PDF and immediately trigger a browser download, then revoke the blob URL.
async function downloadBlob(path: string, filename: string): Promise<void> {
  const url = await requestBlob(path)
  try {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } finally {
    URL.revokeObjectURL(url)
  }
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

// ---- API ----

export const api = {
  // Jobs
  generate: (body: GenerateRequest, signal?: AbortSignal) =>
    request<Job>('/admin/jobs/generate', { ...json('POST', body), signal }),
  listJobs: () => request<Job[]>('/admin/jobs'),
  getJob: (id: number) => request<Job>(`/admin/jobs/${id}`),
  getInsights: () => request<CandidacyInsights>('/admin/jobs/insights'),
  updateStatus: (id: number, status: string) =>
    request<Job>(`/admin/jobs/${id}/status`, json('PATCH', { status })),
  deleteJob: (id: number) =>
    request<void>(`/admin/jobs/${id}`, { method: 'DELETE' }),
  regenerate: (id: number, signal?: AbortSignal) =>
    request<Job>(`/admin/jobs/${id}/regenerate`, { method: 'POST', signal }),
  // PDF methods — use authenticated fetch rather than bare URL so X-API-Key is sent.
  // Iframes and <a href> are plain browser requests that cannot carry custom headers.
  fetchResumePdfPreview: (id: number) => requestBlob(`/admin/jobs/${id}/resume-preview.pdf`),
  downloadResumePdf: (id: number, company: string | null) =>
    downloadBlob(`/admin/jobs/${id}/resume.pdf`, `resume-${(company ?? 'company').toLowerCase().replace(/[^a-z0-9]/g, '-')}.pdf`),
  downloadResumePdfPage1: (id: number, company: string | null) =>
    downloadBlob(`/admin/jobs/${id}/resume.pdf?first_page=true`, `resume-${(company ?? 'company').toLowerCase().replace(/[^a-z0-9]/g, '-')}-p1.pdf`),
  downloadCoverLetterPdf: (id: number, company: string | null) =>
    downloadBlob(`/admin/jobs/${id}/cover-letter.pdf`, `cover-letter-${(company ?? 'company').toLowerCase().replace(/[^a-z0-9]/g, '-')}.pdf`),
  updateCoverLetter: (id: number, cover_letter: string) =>
    request<Job>(`/admin/jobs/${id}/cover-letter`, json('PATCH', { cover_letter })),

  // Profile
  getProfile: () => request<FullProfile>('/admin/profile'),
  updatePersonal: (data: Omit<PersonalInfo, 'id'>) =>
    request<PersonalInfo>('/admin/profile/personal', json('PUT', data)),

  // Projects
  createProject: (data: Omit<Project, 'id'>) =>
    request<Project>('/admin/profile/projects', json('POST', data)),
  updateProject: (id: number, data: Omit<Project, 'id'>) =>
    request<Project>(`/admin/profile/projects/${id}`, json('PUT', data)),
  deleteProject: (id: number) =>
    request<void>(`/admin/profile/projects/${id}`, { method: 'DELETE' }),
  restoreProject: (id: number) =>
    request<Project>(`/admin/profile/projects/${id}/restore`, { method: 'POST' }),

  // Experience
  createExperience: (data: Omit<Experience, 'id'>) =>
    request<Experience>('/admin/profile/experience', json('POST', data)),
  updateExperience: (id: number, data: Omit<Experience, 'id'>) =>
    request<Experience>(`/admin/profile/experience/${id}`, json('PUT', data)),
  deleteExperience: (id: number) =>
    request<void>(`/admin/profile/experience/${id}`, { method: 'DELETE' }),
  restoreExperience: (id: number) =>
    request<Experience>(`/admin/profile/experience/${id}/restore`, { method: 'POST' }),

  // Skills
  createSkillCategory: (data: Omit<SkillCategory, 'id'>) =>
    request<SkillCategory>('/admin/profile/skills', json('POST', data)),
  updateSkillCategory: (id: number, data: Omit<SkillCategory, 'id'>) =>
    request<SkillCategory>(`/admin/profile/skills/${id}`, json('PUT', data)),
  deleteSkillCategory: (id: number) =>
    request<void>(`/admin/profile/skills/${id}`, { method: 'DELETE' }),
  restoreSkillCategory: (id: number) =>
    request<SkillCategory>(`/admin/profile/skills/${id}/restore`, { method: 'POST' }),

  // Education
  createEducation: (data: Omit<Education, 'id'>) =>
    request<Education>('/admin/profile/education', json('POST', data)),
  updateEducation: (id: number, data: Omit<Education, 'id'>) =>
    request<Education>(`/admin/profile/education/${id}`, json('PUT', data)),
  deleteEducation: (id: number) =>
    request<void>(`/admin/profile/education/${id}`, { method: 'DELETE' }),
  restoreEducation: (id: number) =>
    request<Education>(`/admin/profile/education/${id}/restore`, { method: 'POST' }),

  // AI provider credentials (BYO API key)
  getApiKeyStatus: () => request<CredentialStatus>('/admin/settings/api-key'),
  setApiKey: (api_key: string, label?: string) =>
    request<CredentialStatus>('/admin/settings/api-key', json('POST', { api_key, label })),
  deleteApiKey: () =>
    request<void>('/admin/settings/api-key', { method: 'DELETE' }),

  // Account data export (Phase 6) — async: request enqueues on the worker,
  // poll status until "ready", then download.
  requestExport: () => request<AccountExport>('/admin/account/export', { method: 'POST' }),
  getExportStatus: (id: number) => request<AccountExport>(`/admin/account/export/${id}`),
  downloadExport: (id: number) =>
    downloadBlob(`/admin/account/export/${id}/download`, `careeros-export-${id}.zip`),

  // Account deletion (Phase 6) — 7-day grace period, cancel any time before it lapses.
  getDeletionStatus: () => request<AccountDeletionStatus>('/admin/account/delete'),
  requestDeletion: () => request<AccountDeletionStatus>('/admin/account/delete', { method: 'POST' }),
  cancelDeletion: () => request<AccountDeletionStatus>('/admin/account/delete', { method: 'DELETE' }),

  // Resume import — draft only, never written to the profile until the caller
  // saves each reviewed item via the CRUD methods above.
  importResume: (input: { file: File } | { text: string }) => {
    const formData = new FormData()
    if ('file' in input) formData.append('file', input.file)
    else formData.append('text', input.text)
    return request<ProfileImportDraft>('/admin/profile/import', { method: 'POST', body: formData })
  },

  // Waitlist (Phase 8) — pre-auth, hits /api/waitlist directly (not the generic
  // /api/[...path] proxy, which requires a Clerk session that doesn't exist yet).
  joinWaitlist: (email: string) =>
    request<{ status: string }>('/waitlist', json('POST', { email })),
}
