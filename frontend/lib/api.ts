const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
  description: string
  sort_order: number
}

export interface Project {
  id: number
  name: string
  start_date: string | null
  end_date: string | null
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

// ---- Shared ----

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  // 204 No Content — DELETE endpoints return empty body, res.json() would throw
  if (res.status === 204) return undefined as T
  return res.json()
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
    request<Job>(`/admin/jobs/${id}/status?status=${status}`, { method: 'PATCH' }),
  regenerate: (id: number, signal?: AbortSignal) =>
    request<Job>(`/admin/jobs/${id}/regenerate`, { method: 'POST', signal }),
  resumePdfUrl: (id: number) => `${API_BASE}/admin/jobs/${id}/resume.pdf`,
  resumePreviewUrl: (id: number) => `${API_BASE}/admin/jobs/${id}/resume-preview.pdf`,
  coverLetterPdfUrl: (id: number) => `${API_BASE}/admin/jobs/${id}/cover-letter.pdf`,
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

  // Experience
  createExperience: (data: Omit<Experience, 'id'>) =>
    request<Experience>('/admin/profile/experience', json('POST', data)),
  updateExperience: (id: number, data: Omit<Experience, 'id'>) =>
    request<Experience>(`/admin/profile/experience/${id}`, json('PUT', data)),
  deleteExperience: (id: number) =>
    request<void>(`/admin/profile/experience/${id}`, { method: 'DELETE' }),

  // Skills
  createSkillCategory: (data: Omit<SkillCategory, 'id'>) =>
    request<SkillCategory>('/admin/profile/skills', json('POST', data)),
  updateSkillCategory: (id: number, data: Omit<SkillCategory, 'id'>) =>
    request<SkillCategory>(`/admin/profile/skills/${id}`, json('PUT', data)),
  deleteSkillCategory: (id: number) =>
    request<void>(`/admin/profile/skills/${id}`, { method: 'DELETE' }),

  // Education
  updateEducation: (id: number, data: Omit<Education, 'id'>) =>
    request<Education>(`/admin/profile/education/${id}`, json('PUT', data)),
}
