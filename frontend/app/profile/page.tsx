'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, FullProfile, Project, Experience, SkillCategory } from '@/lib/api'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'

// ---- Shared UI ----

function SectionHeader({
  title,
  onAdd,
  adding,
}: {
  title: string
  onAdd?: () => void
  adding?: boolean
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <SectionLabel>{title}</SectionLabel>
      {onAdd && (
        <button
          onClick={onAdd}
          disabled={adding}
          className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors disabled:opacity-40"
        >
          {adding ? 'Adding…' : '+ Add'}
        </button>
      )}
    </div>
  )
}

function SaveButton({ saving, onClick }: { saving: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={saving}
      className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white disabled:opacity-50 transition-all"
      style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
    >
      {saving ? 'Saving…' : 'Save'}
    </button>
  )
}

function CancelButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-1.5 rounded-xl text-xs font-medium text-neutral-400 hover:text-neutral-600 transition-colors"
    >
      Cancel
    </button>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inputCls = "w-full px-3 py-2 rounded-xl text-sm text-neutral-700 placeholder-neutral-300 focus:outline-none"
const inputStyle = { background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.07)' }

function Input({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={inputCls}
      style={inputStyle}
    />
  )
}

function TextArea({ value, onChange, placeholder, rows = 4 }: { value: string; onChange: (v: string) => void; placeholder?: string; rows?: number }) {
  return (
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className={`${inputCls} resize-none leading-relaxed`}
      style={inputStyle}
    />
  )
}

function TechTags({ tags }: { tags: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map(t => (
        <span key={t} className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--c-accent-dim)', color: 'var(--c-accent)' }}>
          {t}
        </span>
      ))}
    </div>
  )
}

function Bullets({ bullets }: { bullets: string[] }) {
  return (
    <ul className="space-y-1 mt-2">
      {bullets.map((b, i) => (
        <li key={i} className="flex gap-2 text-sm text-neutral-600">
          <span className="text-neutral-300 shrink-0 mt-0.5">•</span>
          <span>{b}</span>
        </li>
      ))}
    </ul>
  )
}

function SavedFlash() {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={spring.snappy}
      className="text-xs font-medium"
      style={{ color: 'var(--c-success)' }}
    >
      Saved ✓
    </motion.span>
  )
}

// Shared border style for bare item rows
const itemBorder: React.CSSProperties = { borderBottom: '1px solid var(--c-border)' }

function ReorderButtons({
  onUp,
  onDown,
  canUp,
  canDown,
}: {
  onUp: () => void
  onDown: () => void
  canUp: boolean
  canDown: boolean
}) {
  const btnCls = "text-neutral-300 hover:text-neutral-600 transition-colors disabled:opacity-20 disabled:cursor-default p-0.5 rounded"
  return (
    <div className="flex flex-col gap-0.5">
      <button onClick={onUp} disabled={!canUp} className={btnCls} title="Move up">▲</button>
      <button onClick={onDown} disabled={!canDown} className={btnCls} title="Move down">▼</button>
    </div>
  )
}

// ---- Projects section ----

function ProjectCard({
  project,
  onSave,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  startEditing,
}: {
  project: Project
  onSave: (data: Omit<Project, 'id'>) => Promise<void>
  onDelete: () => Promise<void>
  onMoveUp: () => void
  onMoveDown: () => void
  canMoveUp: boolean
  canMoveDown: boolean
  startEditing?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [name, setName] = useState(project.name)
  const [tech, setTech] = useState(project.tech.join(', '))
  const [startDate, setStartDate] = useState(project.start_date ?? '')
  const [endDate, setEndDate] = useState(project.end_date ?? '')
  const [bullets, setBullets] = useState(project.bullets.join('\n'))

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    try {
      await onSave({
        name,
        tech: tech.split(',').map(t => t.trim()).filter(Boolean),
        start_date: startDate || null,
        end_date: endDate || null,
        bullets: bullets.split('\n').map(b => b.trim()).filter(Boolean),
        sort_order: project.sort_order,
      })
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  const del = async () => {
    if (!confirm(`Delete "${project.name}"?`)) return
    setDeleting(true)
    await onDelete()
  }

  return (
    <motion.div layout className="py-5 group" style={itemBorder}>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Project name">
                <Input value={name} onChange={setName} placeholder="MarketMind AI" />
              </Field>
              <Field label="Tech stack (comma-separated)">
                <Input value={tech} onChange={setTech} placeholder="Python, FastAPI, React" />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start date">
                <Input value={startDate} onChange={setStartDate} placeholder="Dec 2025" />
              </Field>
              <Field label="End date">
                <Input value={endDate} onChange={setEndDate} placeholder="Present (leave blank)" />
              </Field>
            </div>
            <Field label="Bullets (one per line)">
              <TextArea
                value={bullets}
                onChange={setBullets}
                rows={5}
                placeholder={"Built a multi-agent pipeline...\nReduced manual work by 70%..."}
              />
            </Field>
            <div className="flex items-center justify-between pt-1">
              <button onClick={del} disabled={deleting}
                className="text-xs text-red-400 hover:text-red-600 transition-colors disabled:opacity-40">
                {deleting ? 'Deleting…' : 'Delete project'}
              </button>
              <div className="flex gap-2">
                <CancelButton onClick={() => setEditing(false)} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2.5 mb-1.5">
                  <h3 className="text-sm font-semibold text-neutral-800">{project.name}</h3>
                  {(project.start_date || project.end_date) && (
                    <span className="text-xs text-neutral-400">
                      {project.start_date} – {project.end_date || 'Present'}
                    </span>
                  )}
                  <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                </div>
                {project.tech.length > 0 && <TechTags tags={project.tech} />}
                {project.bullets.length > 0 && <Bullets bullets={project.bullets} />}
              </div>
              {/* Hover-reveal actions */}
              <div className="shrink-0 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <ReorderButtons onUp={onMoveUp} onDown={onMoveDown} canUp={canMoveUp} canDown={canMoveDown} />
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">
                  Edit
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ---- Experience section ----

function ExperienceCard({
  exp,
  onSave,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  startEditing,
}: {
  exp: Experience
  onSave: (data: Omit<Experience, 'id'>) => Promise<void>
  onDelete: () => Promise<void>
  onMoveUp: () => void
  onMoveDown: () => void
  canMoveUp: boolean
  canMoveDown: boolean
  startEditing?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [company, setCompany] = useState(exp.company)
  const [role, setRole] = useState(exp.role)
  const [startDate, setStartDate] = useState(exp.start_date ?? '')
  const [endDate, setEndDate] = useState(exp.end_date ?? '')
  const [bullets, setBullets] = useState(exp.bullets.join('\n'))

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    try {
      await onSave({
        company, role,
        start_date: startDate || null,
        end_date: endDate || null,
        bullets: bullets.split('\n').map(b => b.trim()).filter(Boolean),
        sort_order: exp.sort_order,
      })
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  const del = async () => {
    if (!confirm(`Delete "${exp.role} at ${exp.company}"?`)) return
    setDeleting(true)
    await onDelete()
  }

  return (
    <motion.div layout className="py-5 group" style={itemBorder}>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Role"><Input value={role} onChange={setRole} placeholder="Full Stack Developer" /></Field>
              <Field label="Company"><Input value={company} onChange={setCompany} placeholder="UBC" /></Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start date"><Input value={startDate} onChange={setStartDate} placeholder="May 2025" /></Field>
              <Field label="End date"><Input value={endDate} onChange={setEndDate} placeholder="Aug 2025" /></Field>
            </div>
            <Field label="Bullets (one per line)">
              <TextArea value={bullets} onChange={setBullets} rows={4} placeholder="Built a platform that..." />
            </Field>
            <div className="flex items-center justify-between pt-1">
              <button onClick={del} disabled={deleting}
                className="text-xs text-red-400 hover:text-red-600 transition-colors disabled:opacity-40">
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
              <div className="flex gap-2">
                <CancelButton onClick={() => setEditing(false)} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <h3 className="text-sm font-semibold text-neutral-800">{exp.role}</h3>
                  <span className="text-neutral-400 text-sm">at {exp.company}</span>
                  <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                </div>
                <p className="text-xs text-neutral-400 mb-2">
                  {exp.start_date} – {exp.end_date || 'Present'}
                </p>
                <Bullets bullets={exp.bullets} />
              </div>
              <div className="shrink-0 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <ReorderButtons onUp={onMoveUp} onDown={onMoveDown} canUp={canMoveUp} canDown={canMoveDown} />
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">
                  Edit
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ---- Skills section ----

function SkillCard({
  skill,
  onSave,
  onDelete,
}: {
  skill: SkillCategory
  onSave: (d: Omit<SkillCategory, 'id'>) => Promise<void>
  onDelete: () => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [category, setCategory] = useState(skill.category)
  const [items, setItems] = useState(skill.items.join(', '))

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    try {
      await onSave({ category, items: items.split(',').map(s => s.trim()).filter(Boolean), sort_order: skill.sort_order })
      setEditing(false)
      setSavedFlash(true)
    } finally { setSaving(false) }
  }

  return (
    <motion.div layout className="py-5 group" style={itemBorder}>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Category"><Input value={category} onChange={setCategory} placeholder="Languages" /></Field>
              <div className="col-span-2">
                <Field label="Skills (comma-separated)"><Input value={items} onChange={setItems} placeholder="Python, JavaScript, TypeScript" /></Field>
              </div>
            </div>
            <div className="flex items-center justify-between pt-1">
              <button
                onClick={async () => { if (confirm('Delete this skill category?')) await onDelete() }}
                className="text-xs text-red-400 hover:text-red-600 transition-colors">
                Delete
              </button>
              <div className="flex gap-2">
                <CancelButton onClick={() => setEditing(false)} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="text-xs text-neutral-400 mb-2">{skill.category}</p>
                <TechTags tags={skill.items} />
              </div>
              <div className="shrink-0 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">
                  Edit
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ---- Main page ----

export default function ProfilePage() {
  const [profile, setProfile] = useState<FullProfile | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [newProjectId, setNewProjectId] = useState<number | null>(null)
  const [newExpId, setNewExpId] = useState<number | null>(null)
  const [addingProject, setAddingProject] = useState(false)
  const [addingExp, setAddingExp] = useState(false)
  const [addingSkill, setAddingSkill] = useState(false)

  const load = useCallback(async () => {
    try {
      setLoadError(false)
      setProfile(await api.getProfile())
    } catch {
      setLoadError(true)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-neutral-400 text-sm">Could not reach the backend.</p>
        <button
          onClick={load}
          className="px-4 py-2 rounded-xl text-sm font-medium text-white"
          style={{ background: 'var(--c-btn-bg)', boxShadow: 'var(--c-btn-shadow)' }}
        >
          Retry
        </button>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
      </div>
    )
  }

  // ---- Reorder helpers ----

  const swapProjectOrder = async (idxA: number, idxB: number) => {
    const a = profile.projects[idxA]
    const b = profile.projects[idxB]
    const { id: _ia, ...restA } = a
    const { id: _ib, ...restB } = b
    await Promise.all([
      api.updateProject(a.id, { ...restA, sort_order: b.sort_order }),
      api.updateProject(b.id, { ...restB, sort_order: a.sort_order }),
    ])
    const updated = [...profile.projects]
    updated[idxA] = { ...a, sort_order: b.sort_order }
    updated[idxB] = { ...b, sort_order: a.sort_order }
    updated.sort((x, y) => x.sort_order - y.sort_order)
    setProfile(prev => prev ? { ...prev, projects: updated } : prev)
  }

  const swapExpOrder = async (idxA: number, idxB: number) => {
    const a = profile.experience[idxA]
    const b = profile.experience[idxB]
    const { id: _ia, ...restA } = a
    const { id: _ib, ...restB } = b
    await Promise.all([
      api.updateExperience(a.id, { ...restA, sort_order: b.sort_order }),
      api.updateExperience(b.id, { ...restB, sort_order: a.sort_order }),
    ])
    const updated = [...profile.experience]
    updated[idxA] = { ...a, sort_order: b.sort_order }
    updated[idxB] = { ...b, sort_order: a.sort_order }
    updated.sort((x, y) => x.sort_order - y.sort_order)
    setProfile(prev => prev ? { ...prev, experience: updated } : prev)
  }

  // ---- Projects handlers ----

  const addProject = async () => {
    if (addingProject) return
    setAddingProject(true)
    try {
      const p = await api.createProject({
        name: 'New Project',
        tech: [],
        start_date: null,
        end_date: null,
        bullets: [],
        sort_order: (profile.projects.at(-1)?.sort_order ?? -1) + 1,
      })
      setProfile(prev => prev ? { ...prev, projects: [...prev.projects, p] } : prev)
      setNewProjectId(p.id)
    } finally {
      setAddingProject(false)
    }
  }

  const saveProject = async (id: number, data: Omit<Project, 'id'>) => {
    const updated = await api.updateProject(id, data)
    setNewProjectId(null)
    setProfile(prev => prev ? { ...prev, projects: prev.projects.map(p => p.id === id ? updated : p) } : prev)
  }

  const deleteProject = async (id: number) => {
    await api.deleteProject(id)
    setProfile(prev => prev ? { ...prev, projects: prev.projects.filter(p => p.id !== id) } : prev)
  }

  // ---- Experience handlers ----

  const addExperience = async () => {
    if (addingExp) return
    setAddingExp(true)
    try {
      const e = await api.createExperience({
        company: 'Company',
        role: 'Role',
        start_date: null,
        end_date: null,
        bullets: [],
        sort_order: (profile.experience.at(-1)?.sort_order ?? -1) + 1,
      })
      setProfile(prev => prev ? { ...prev, experience: [...prev.experience, e] } : prev)
      setNewExpId(e.id)
    } finally {
      setAddingExp(false)
    }
  }

  const saveExperience = async (id: number, data: Omit<Experience, 'id'>) => {
    const updated = await api.updateExperience(id, data)
    setNewExpId(null)
    setProfile(prev => prev ? { ...prev, experience: prev.experience.map(e => e.id === id ? updated : e) } : prev)
  }

  const deleteExperience = async (id: number) => {
    await api.deleteExperience(id)
    setProfile(prev => prev ? { ...prev, experience: prev.experience.filter(e => e.id !== id) } : prev)
  }

  // ---- Skills handlers ----

  const addSkill = async () => {
    if (addingSkill) return
    setAddingSkill(true)
    try {
      const s = await api.createSkillCategory({
        category: 'New Category',
        items: [],
        sort_order: (profile.skills.at(-1)?.sort_order ?? -1) + 1,
      })
      setProfile(prev => prev ? { ...prev, skills: [...prev.skills, s] } : prev)
    } finally {
      setAddingSkill(false)
    }
  }

  const saveSkill = async (id: number, data: Omit<SkillCategory, 'id'>) => {
    const updated = await api.updateSkillCategory(id, data)
    setProfile(prev => prev ? { ...prev, skills: prev.skills.map(s => s.id === id ? updated : s) } : prev)
  }

  const deleteSkill = async (id: number) => {
    await api.deleteSkillCategory(id)
    setProfile(prev => prev ? { ...prev, skills: prev.skills.filter(s => s.id !== id) } : prev)
  }

  return (
    <div className="px-6 pb-24 max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="pt-10 mb-10"
      >
        <h1 className="text-3xl font-semibold text-neutral-900">Profile</h1>
      </motion.div>

      {/* Projects — most important, first */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.06 }}
        className="mb-10"
      >
        <SectionHeader title="Projects" onAdd={addProject} adding={addingProject} />
        <div className="space-y-3">
          <AnimatePresence>
            {profile.projects.map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={spring.standard}
              >
                <ProjectCard
                  project={p}
                  startEditing={p.id === newProjectId}
                  onSave={data => saveProject(p.id, data)}
                  onDelete={() => deleteProject(p.id)}
                  onMoveUp={() => swapProjectOrder(i, i - 1)}
                  onMoveDown={() => swapProjectOrder(i, i + 1)}
                  canMoveUp={i > 0}
                  canMoveDown={i < profile.projects.length - 1}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.section>

      {/* Experience */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.1 }}
        className="mb-10"
      >
        <SectionHeader title="Experience" onAdd={addExperience} adding={addingExp} />
        <div className="space-y-3">
          <AnimatePresence>
            {profile.experience.map((e, i) => (
              <motion.div
                key={e.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={spring.standard}
              >
                <ExperienceCard
                  exp={e}
                  startEditing={e.id === newExpId}
                  onSave={data => saveExperience(e.id, data)}
                  onDelete={() => deleteExperience(e.id)}
                  onMoveUp={() => swapExpOrder(i, i - 1)}
                  onMoveDown={() => swapExpOrder(i, i + 1)}
                  canMoveUp={i > 0}
                  canMoveDown={i < profile.experience.length - 1}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.section>

      {/* Skills */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.14 }}
        className="mb-10"
      >
        <SectionHeader title="Skills" onAdd={addSkill} adding={addingSkill} />
        <div className="space-y-3">
          <AnimatePresence>
            {profile.skills.map(s => (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={spring.standard}
              >
                <SkillCard
                  skill={s}
                  onSave={data => saveSkill(s.id, data)}
                  onDelete={() => deleteSkill(s.id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.section>

      {/* Education — rarely changes */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.18 }}
        className="mb-10"
      >
        <SectionHeader title="Education" />
        <div className="space-y-3">
          {profile.education.map(e => (
            <div key={e.id} className="py-5" style={itemBorder}>
              <h3 className="text-sm font-semibold text-neutral-800">{e.school}</h3>
              <p className="text-sm text-neutral-500 mt-0.5">{e.degree}{e.minor ? `, Minor in ${e.minor}` : ''}</p>
              <p className="text-xs text-neutral-400 mt-1">{e.start_date} – {e.end_date}</p>
            </div>
          ))}
        </div>
      </motion.section>
    </div>
  )
}
