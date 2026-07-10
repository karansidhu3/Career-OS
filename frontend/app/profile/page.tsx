'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { api, FullProfile, Project, Experience, SkillCategory, Education, PersonalInfo } from '@/lib/api'
import { BrandMark } from '@/components/BrandMark'
import { SectionLabel } from '@/components/SectionLabel'
import { spring } from '@/lib/motion'
import { Field, Input, SaveButton, CancelButton, inputCls, inputStyle } from '@/components/FormControls'
import { TEMPLATE_CATALOG, useTemplatePdfPreviews, TemplatePdfThumb, TemplatePreviewModal } from '@/components/TemplatePreview'

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
          className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors disabled:opacity-40"
        >
          {adding ? 'Adding…' : '+ Add'}
        </button>
      )}
    </div>
  )
}

function TextArea({ value, onChange, placeholder, rows = 4, maxLength }: { value: string; onChange: (v: string) => void; placeholder?: string; rows?: number; maxLength?: number }) {
  return (
    <div className="relative">
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength}
        className={`${inputCls} resize-none leading-relaxed`}
        style={inputStyle}
      />
      {maxLength && value.length > maxLength * 0.85 && (
        <span className={`absolute bottom-2 right-3 text-xs tabular-nums ${value.length >= maxLength ? 'text-red-400' : 'text-neutral-300'}`}>
          {value.length}/{maxLength}
        </span>
      )}
    </div>
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

// Source descriptions are often multiple long paragraphs (raw notes for the
// AI to read, not resume-ready prose) — collapsed by default so the page is
// scannable, with the full text one click away.
function DescriptionText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  if (!text) return null
  const isLong = text.length > 260
  return (
    <div className="mt-2">
      <p className={`text-sm text-neutral-600 leading-relaxed whitespace-pre-wrap ${!expanded && isLong ? 'line-clamp-3' : ''}`}>
        {text}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-xs mt-1.5 font-medium transition-colors"
          style={{ color: 'var(--c-accent)' }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
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
  isNew,
}: {
  project: Project
  onSave: (data: Omit<Project, 'id'>) => Promise<void>
  onDelete: () => void
  onMoveUp: () => void
  onMoveDown: () => void
  canMoveUp: boolean
  canMoveDown: boolean
  startEditing?: boolean
  isNew?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [name, setName] = useState(project.name)
  const [startDate, setStartDate] = useState(project.start_date ?? '')
  const [endDate, setEndDate] = useState(project.end_date ?? '')
  const [githubUrl, setGithubUrl] = useState(project.github_url ?? '')
  const [description, setDescription] = useState(project.description ?? '')

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
        start_date: startDate || null,
        end_date: endDate || null,
        github_url: githubUrl || null,
        description,
        sort_order: project.sort_order,
      })
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
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
              <div className="grid grid-cols-2 gap-3">
                <Field label="Start date">
                  <Input value={startDate} onChange={setStartDate} placeholder="Dec 2025" />
                </Field>
                <Field label="End date">
                  <Input value={endDate} onChange={setEndDate} placeholder="Present" />
                </Field>
              </div>
            </div>
            <Field label="GitHub URL (optional)">
              <Input value={githubUrl} onChange={setGithubUrl} placeholder="https://github.com/karansidhu3/marketmind" />
            </Field>
            <Field label="Description">
              <TextArea
                value={description}
                onChange={setDescription}
                rows={7}
                maxLength={10000}
                placeholder="Describe what you built, the technical decisions, the architecture, and outcomes. Write naturally — the AI reads this and writes tailored bullets for each application."
              />
            </Field>
            <div className="flex items-center justify-between pt-1">
              <AnimatePresence mode="wait" initial={false}>
                {!confirmDelete ? (
                  <motion.button
                    key="del"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    onClick={() => setConfirmDelete(true)}
                    className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
                  >
                    Delete project
                  </motion.button>
                ) : (
                  <motion.div
                    key="confirm"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <button
                      onClick={() => { setConfirmDelete(false); onDelete() }}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors"
                    >
                      Confirm delete
                    </button>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
              <div className="flex gap-2">
                <CancelButton onClick={() => {
                  if (isNew) {
                    onDelete()
                  } else {
                    setEditing(false)
                    setConfirmDelete(false)
                  }
                }} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2.5 mb-1">
                  <h3 className="text-sm font-semibold text-neutral-800">{project.name}</h3>
                  {(project.start_date || project.end_date) && (
                    <span className="text-xs text-neutral-600">
                      {project.start_date} – {project.end_date || 'Present'}
                    </span>
                  )}
                  <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                </div>
                {project.github_url && (
                  <a
                    href={project.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs mb-1 transition-colors"
                    style={{ color: 'var(--c-accent)' }}
                    onClick={e => e.stopPropagation()}
                  >
                    <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                    </svg>
                    {project.github_url.replace(/^https?:\/\/(www\.)?github\.com\//, 'github.com/')}
                  </a>
                )}
                <DescriptionText text={project.description} />
              </div>
              <div className="shrink-0 flex items-center gap-3 opacity-60 group-hover:opacity-100 transition-opacity">
                <ReorderButtons onUp={onMoveUp} onDown={onMoveDown} canUp={canMoveUp} canDown={canMoveDown} />
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
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
  isNew,
}: {
  exp: Experience
  onSave: (data: Omit<Experience, 'id'>) => Promise<void>
  onDelete: () => void
  onMoveUp: () => void
  onMoveDown: () => void
  canMoveUp: boolean
  canMoveDown: boolean
  startEditing?: boolean
  isNew?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [company, setCompany] = useState(exp.company)
  const [role, setRole] = useState(exp.role)
  const [startDate, setStartDate] = useState(exp.start_date ?? '')
  const [endDate, setEndDate] = useState(exp.end_date ?? '')
  const [location, setLocation] = useState(exp.location ?? '')
  const [description, setDescription] = useState(exp.description ?? '')

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
        location: location || null,
        description,
        sort_order: exp.sort_order,
      })
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div layout className="py-5 group" style={itemBorder}>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Role"><Input value={role} onChange={setRole} placeholder="Full Stack Developer" /></Field>
              <Field label="Company"><Input value={company} onChange={setCompany} placeholder="UBC" /></Field>
              <Field label="Location (optional)"><Input value={location} onChange={setLocation} placeholder="Kelowna, BC" /></Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start date"><Input value={startDate} onChange={setStartDate} placeholder="May 2025" /></Field>
              <Field label="End date"><Input value={endDate} onChange={setEndDate} placeholder="Aug 2025" /></Field>
            </div>
            <Field label="Description">
              <TextArea
                value={description}
                onChange={setDescription}
                rows={6}
                maxLength={10000}
                placeholder="Describe the work, the technical stack, what you built, and the impact. Write naturally — the AI reads this and writes tailored bullets for each application."
              />
            </Field>
            <div className="flex items-center justify-between pt-1">
              <AnimatePresence mode="wait" initial={false}>
                {!confirmDelete ? (
                  <motion.button
                    key="del"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    onClick={() => setConfirmDelete(true)}
                    className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
                  >
                    Delete
                  </motion.button>
                ) : (
                  <motion.div
                    key="confirm"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <button
                      onClick={() => { setConfirmDelete(false); onDelete() }}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors"
                    >
                      Confirm delete
                    </button>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
              <div className="flex gap-2">
                <CancelButton onClick={() => {
                  if (isNew) {
                    onDelete()
                  } else {
                    setEditing(false)
                    setConfirmDelete(false)
                  }
                }} />
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
                  <span className="text-neutral-600 text-sm">at {exp.company}</span>
                  <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                </div>
                <p className="text-xs text-neutral-600 mb-1">
                  {exp.start_date} – {exp.end_date || 'Present'}
                  {exp.location && <span className="ml-2 text-neutral-300">· {exp.location}</span>}
                </p>
                <DescriptionText text={exp.description} />
              </div>
              <div className="shrink-0 flex items-center gap-3 opacity-60 group-hover:opacity-100 transition-opacity">
                <ReorderButtons onUp={onMoveUp} onDown={onMoveDown} canUp={canMoveUp} canDown={canMoveDown} />
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
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

function SkillDeleteButton({ onDelete }: { onDelete: () => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  return (
    <AnimatePresence mode="wait" initial={false}>
      {!confirmDelete ? (
        <motion.button
          key="del"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.1 }}
          onClick={() => setConfirmDelete(true)}
          className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
        >
          Delete
        </motion.button>
      ) : (
        <motion.div
          key="confirm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.1 }}
          className="flex items-center gap-3"
        >
          <button
            onClick={() => { setConfirmDelete(false); onDelete() }}
            className="text-xs text-red-400 hover:text-red-600 transition-colors"
          >
            Confirm delete
          </button>
          <button
            onClick={() => setConfirmDelete(false)}
            className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
          >
            Cancel
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function SkillCard({
  skill,
  onSave,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  startEditing,
  isNew,
}: {
  skill: SkillCategory
  onSave: (d: Omit<SkillCategory, 'id'>) => Promise<void>
  onDelete: () => void
  onMoveUp: () => void
  onMoveDown: () => void
  canMoveUp: boolean
  canMoveDown: boolean
  startEditing?: boolean
  isNew?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
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
              <SkillDeleteButton onDelete={onDelete} />
              <div className="flex gap-2">
                <CancelButton onClick={() => {
                  if (isNew) {
                    onDelete()
                  } else {
                    setEditing(false)
                  }
                }} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="text-xs text-neutral-600 mb-2">{skill.category}</p>
                <TechTags tags={skill.items} />
              </div>
              <div className="shrink-0 flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                <ReorderButtons onUp={onMoveUp} onDown={onMoveDown} canUp={canMoveUp} canDown={canMoveDown} />
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
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

// ---- Education section ----

function EducationCard({
  education,
  onSave,
  onDelete,
  startEditing,
  isNew,
}: {
  education: Education
  onSave: (data: Omit<Education, 'id'>) => Promise<void>
  onDelete: () => void
  startEditing?: boolean
  isNew?: boolean
}) {
  const [editing, setEditing] = useState(startEditing ?? false)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [school, setSchool] = useState(education.school)
  const [degree, setDegree] = useState(education.degree)
  const [minor, setMinor] = useState(education.minor ?? '')
  const [startDate, setStartDate] = useState(education.start_date ?? '')
  const [endDate, setEndDate] = useState(education.end_date ?? '')

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    try {
      await onSave({
        school,
        degree,
        field: education.field,
        minor: minor || null,
        start_date: startDate || null,
        end_date: endDate || null,
      })
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div layout className="py-5 group" style={itemBorder}>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="School"><Input value={school} onChange={setSchool} placeholder="University of British Columbia" /></Field>
              <Field label="Degree"><Input value={degree} onChange={setDegree} placeholder="BSc Computer Science" /></Field>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Minor (optional)"><Input value={minor} onChange={setMinor} placeholder="Data Science" /></Field>
              <Field label="Start date"><Input value={startDate} onChange={setStartDate} placeholder="Sep 2022" /></Field>
              <Field label="End date"><Input value={endDate} onChange={setEndDate} placeholder="Jun 2026" /></Field>
            </div>
            <div className="flex items-center justify-between pt-1">
              <AnimatePresence mode="wait" initial={false}>
                {!confirmDelete ? (
                  <motion.button
                    key="del"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    onClick={() => setConfirmDelete(true)}
                    className="text-xs text-neutral-600 hover:text-red-400 transition-colors"
                  >
                    Delete education
                  </motion.button>
                ) : (
                  <motion.div
                    key="confirm"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <button
                      onClick={() => { setConfirmDelete(false); onDelete() }}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors"
                    >
                      Confirm delete
                    </button>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
              <div className="flex gap-2">
                <CancelButton onClick={() => {
                  if (isNew) {
                    onDelete()
                  } else {
                    setEditing(false)
                    setConfirmDelete(false)
                  }
                }} />
                <SaveButton saving={saving} onClick={save} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2.5">
                  <h3 className="text-sm font-semibold text-neutral-800">{education.school}</h3>
                  <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
                </div>
                <p className="text-sm text-neutral-600 mt-0.5">
                  {education.degree}{education.minor ? `, Minor in ${education.minor}` : ''}
                </p>
                <p className="text-xs text-neutral-600 mt-1">{education.start_date} – {education.end_date}</p>
              </div>
              <div className="shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                <button onClick={() => setEditing(true)}
                  className="text-xs text-neutral-600 hover:text-neutral-700 transition-colors">
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

// ---- Personal info ----

// ---- Contact field icons — minimal line icons, matching the app's existing icon language ----

function MailIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-10 5L2 7" />
    </svg>
  )
}

function PhoneIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.362 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.338 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

function LinkedinIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6Z" />
      <rect x="2" y="9" width="4" height="12" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  )
}

function GithubIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  )
}

function ContactRow({ icon, value, href }: { icon: React.ReactNode; value: string; href?: string }) {
  const content = (
    <>
      <span className="text-neutral-600 shrink-0">{icon}</span>
      <span className="truncate">{value}</span>
    </>
  )
  return href ? (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2.5 text-sm text-neutral-700 hover:text-neutral-900 transition-colors"
    >
      {content}
    </a>
  ) : (
    <div className="flex items-center gap-2.5 text-sm text-neutral-700">
      {content}
    </div>
  )
}

function PersonalInfoEditor({ personal, onSave }: { personal: PersonalInfo; onSave: (p: PersonalInfo) => void }) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [name, setName] = useState(personal.name)
  const [email, setEmail] = useState(personal.email)
  const [phone, setPhone] = useState(personal.phone ?? '')
  const [location, setLocation] = useState(personal.location ?? '')
  const [linkedin, setLinkedin] = useState(personal.linkedin ?? '')
  const [github, setGithub] = useState(personal.github ?? '')

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const resetFields = () => {
    setName(personal.name)
    setEmail(personal.email)
    setPhone(personal.phone ?? '')
    setLocation(personal.location ?? '')
    setLinkedin(personal.linkedin ?? '')
    setGithub(personal.github ?? '')
  }

  const save = async () => {
    setSaving(true)
    try {
      const { id, ...rest } = personal
      const updated = await api.updatePersonal({
        ...rest,
        name,
        email,
        phone: phone || null,
        location: location || null,
        linkedin: linkedin || null,
        github: github || null,
      })
      onSave(updated)
      setEditing(false)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <SectionLabel>Personal info</SectionLabel>
        <AnimatePresence>{savedFlash && <SavedFlash />}</AnimatePresence>
      </div>
      <p className="text-xs text-neutral-600 mb-6 leading-relaxed">
        This becomes the header of every generated resume.
      </p>
      <AnimatePresence mode="wait">
        {editing ? (
          <motion.div key="edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3 max-w-xl">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Name"><Input value={name} onChange={setName} placeholder="Karanveer Sidhu" /></Field>
              <Field label="Email"><Input value={email} onChange={setEmail} placeholder="you@example.com" /></Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Phone (optional)"><Input value={phone} onChange={setPhone} placeholder="+1 (250) 509-2500" /></Field>
              <Field label="Location (optional)"><Input value={location} onChange={setLocation} placeholder="Kelowna, BC" /></Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="LinkedIn (optional)"><Input value={linkedin} onChange={setLinkedin} placeholder="linkedin.com/in/…" /></Field>
              <Field label="GitHub (optional)"><Input value={github} onChange={setGithub} placeholder="github.com/…" /></Field>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <CancelButton onClick={() => { resetFields(); setEditing(false) }} />
              <SaveButton saving={saving} onClick={save} />
            </div>
          </motion.div>
        ) : (
          <motion.div key="view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="group">
            <div className="flex items-start justify-between gap-4 mb-5">
              <p className="text-2xl font-semibold text-neutral-900 tracking-tight">{personal.name}</p>
              <button
                onClick={() => setEditing(true)}
                className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors shrink-0 pt-1.5"
              >
                Edit
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 max-w-xl">
              {personal.email && <ContactRow icon={<MailIcon />} value={personal.email} href={`mailto:${personal.email}`} />}
              {personal.phone && <ContactRow icon={<PhoneIcon />} value={personal.phone} />}
              {personal.location && <ContactRow icon={<PinIcon />} value={personal.location} />}
              {personal.linkedin && (
                <ContactRow
                  icon={<LinkedinIcon />}
                  value={personal.linkedin}
                  href={personal.linkedin.startsWith('http') ? personal.linkedin : `https://${personal.linkedin}`}
                />
              )}
              {personal.github && (
                <ContactRow
                  icon={<GithubIcon />}
                  value={personal.github}
                  href={personal.github.startsWith('http') ? personal.github : `https://${personal.github}`}
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---- Voice editor ----

function VoiceEditor({ personal, onSave }: { personal: PersonalInfo; onSave: (p: PersonalInfo) => void }) {
  const [voice, setVoice] = useState(personal.cover_letter_voice ?? '')
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const isDirty = voice !== (personal.cover_letter_voice ?? '')

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  const save = async () => {
    setSaving(true)
    try {
      const { id, ...rest } = personal
      const updated = await api.updatePersonal({ ...rest, cover_letter_voice: voice })
      onSave(updated)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionLabel>Cover letter voice</SectionLabel>
        <AnimatePresence>
          {savedFlash && <SavedFlash />}
        </AnimatePresence>
      </div>
      <p className="text-xs text-neutral-600 mb-3 leading-relaxed">
        How you write. Paste a sentence or two from something you've written that sounds like you,
        or describe your tone. Fed into every cover letter generation.
      </p>
      <TextArea
        value={voice}
        onChange={setVoice}
        rows={7}
        maxLength={2000}
        placeholder={'e.g. "I write directly and don\'t over-explain. Short sentences. I open with the problem, not with myself. Technical but not dense."'}
      />
      {isDirty && (
        <div className="mt-3 flex justify-end">
          <SaveButton saving={saving} onClick={save} />
        </div>
      )}
    </div>
  )
}

// ---- Resume format editor ----

const TEMPLATE_IDS = TEMPLATE_CATALOG.map(t => t.id)

function TemplateEditor({ personal, onSave }: { personal: PersonalInfo; onSave: (p: PersonalInfo) => void }) {
  const current = personal.resume_template ?? 'jake'
  const [selected, setSelected] = useState(current)
  const [customPreamble, setCustomPreamble] = useState(personal.custom_preamble ?? '')
  const [compiling, setCompiling] = useState(false)
  const [compileError, setCompileError] = useState<string | null>(null)
  const [customPreviewUrl, setCustomPreviewUrl] = useState<string | null>(null)
  const [expandedPreview, setExpandedPreview] = useState<{ url: string; title: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)

  const namedStates = useTemplatePdfPreviews(TEMPLATE_IDS)

  useEffect(() => {
    if (!savedFlash) return
    const t = setTimeout(() => setSavedFlash(false), 2000)
    return () => clearTimeout(t)
  }, [savedFlash])

  useEffect(() => {
    return () => { if (customPreviewUrl) URL.revokeObjectURL(customPreviewUrl) }
  }, [customPreviewUrl])

  const isDirty =
    selected !== current ||
    (selected === 'custom' && customPreamble !== (personal.custom_preamble ?? ''))

  const canSave = isDirty && (selected !== 'custom' || customPreviewUrl !== null)

  const compileCustom = async () => {
    if (!customPreamble.trim()) return
    setCompiling(true)
    setCompileError(null)
    try {
      const url = await api.compileCustomTemplatePdf(customPreamble)
      setCustomPreviewUrl(prev => { if (prev) URL.revokeObjectURL(prev); return url })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Compilation failed'
      try {
        const d = JSON.parse(msg)
        setCompileError(typeof d?.detail === 'string' ? d.detail : msg)
      } catch { setCompileError(msg) }
    } finally {
      setCompiling(false)
    }
  }

  const save = async () => {
    setSaving(true)
    try {
      const { id, ...rest } = personal
      const updated = await api.updatePersonal({
        ...rest,
        resume_template: selected,
        custom_preamble: selected === 'custom' ? customPreamble : null,
      })
      onSave(updated)
      setSavedFlash(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionLabel>Resume format</SectionLabel>
        <AnimatePresence>
          {savedFlash && <SavedFlash />}
        </AnimatePresence>
      </div>
      <p className="text-xs text-neutral-600 mb-4 leading-relaxed">
        Controls the LaTeX template used when generating your resume. Change this any time —
        new generations will use the updated format.
      </p>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {TEMPLATE_CATALOG.map(t => {
          const active = selected === t.id
          const previewUrl = namedStates[t.id]?.url ?? null
          return (
            <div
              key={t.id}
              role="button"
              tabIndex={0}
              onClick={() => { setSelected(t.id); setCompileError(null) }}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(t.id); setCompileError(null) } }}
              className="text-left rounded-lg overflow-hidden transition-colors cursor-pointer"
              style={{
                border: `1.5px solid ${active ? 'var(--c-accent-border)' : 'var(--c-border)'}`,
                background: active ? 'var(--c-accent-dim)' : 'transparent',
              }}
            >
              <TemplatePdfThumb
                state={namedStates[t.id]}
                scale={0.19}
                onExpand={previewUrl ? () => setExpandedPreview({ url: previewUrl, title: t.name }) : undefined}
              />
              <div className="px-2.5 py-2" style={{ borderTop: '1px solid var(--c-border)' }}>
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-medium text-neutral-800">{t.name}</p>
                  {t.recommended && (
                    <span
                      className="text-[8px] font-medium uppercase tracking-[0.06em] px-1 py-0.5 rounded"
                      style={{ background: 'var(--c-accent-dim)', color: 'var(--color-neutral-800)' }}
                    >
                      Recommended
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-neutral-600 leading-snug mt-0.5">{t.description}</p>
              </div>
            </div>
          )
        })}
      </div>

      {/* Custom template — full-width row, same treatment as onboarding */}
      <button
        onClick={() => { if (selected !== 'custom') setSelected('custom') }}
        className="w-full text-left rounded-lg overflow-hidden transition-colors mb-2"
        style={{
          border: `1.5px solid ${selected === 'custom' ? 'var(--c-accent-border)' : 'var(--c-border)'}`,
          background: selected === 'custom' ? 'var(--c-accent-dim)' : 'transparent',
        }}
      >
        <div className="px-3 py-2.5 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-800">Custom</p>
            <p className="text-[11px] text-neutral-600 leading-snug mt-0.5">
              Your own LaTeX preamble — paste and compile to apply.
            </p>
          </div>
          {selected !== 'custom' && (
            <span className="text-xs shrink-0 ml-3" style={{ color: 'var(--color-neutral-700)' }}>Use this</span>
          )}
        </div>
      </button>

      {selected === 'custom' && (
        <div className="mt-2">
          <p className="text-xs text-neutral-600 mb-2 leading-relaxed">
            Paste your full LaTeX preamble from{' '}
            <code className="font-mono">\documentclass</code> through{' '}
            <code className="font-mono">\begin&#123;document&#125;</code>.
          </p>
          <textarea
            value={customPreamble}
            onChange={e => { setCustomPreamble(e.target.value); setCompileError(null) }}
            rows={8}
            spellCheck={false}
            placeholder={'\\documentclass[letterpaper,11pt]{article}\n\\usepackage{...}\n\\begin{document}'}
            className="w-full font-mono text-xs rounded-lg p-3 resize-y"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--c-border)',
              color: 'var(--color-neutral-900)',
              outline: 'none',
            }}
          />
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <button
              onClick={compileCustom}
              disabled={compiling || !customPreamble.trim()}
              className="px-3 py-1.5 text-xs rounded-lg font-medium transition-opacity disabled:opacity-40"
              style={{ background: 'var(--c-surface-raised)', color: 'var(--color-neutral-900)', border: '1px solid var(--c-border)' }}
            >
              {compiling ? 'Compiling…' : customPreviewUrl ? 'Recompile' : 'Compile & preview'}
            </button>
            {compileError && <p className="text-xs" style={{ color: 'var(--c-danger)' }}>{compileError}</p>}
            {customPreviewUrl && !compileError && (
              <p className="text-xs" style={{ color: 'var(--c-success)' }}>Compiled — select to save</p>
            )}
          </div>

          {customPreviewUrl && (
            <div className="mt-3 rounded-lg overflow-hidden" style={{ border: '1px solid var(--c-border)' }}>
              <TemplatePdfThumb
                state={{ url: customPreviewUrl, loading: false, error: null }}
                scale={0.32}
                showTop={0.9}
                onExpand={() => setExpandedPreview({ url: customPreviewUrl, title: 'Custom' })}
              />
            </div>
          )}
        </div>
      )}

      {canSave && (
        <div className="mt-4 flex justify-end">
          <SaveButton saving={saving} onClick={save} />
        </div>
      )}

      <TemplatePreviewModal
        url={expandedPreview?.url ?? null}
        title={expandedPreview?.title ?? ''}
        onClose={() => setExpandedPreview(null)}
      />
    </div>
  )
}

// ---- Loading skeleton — mirrors the real section layout so nothing reflows on arrival ----

function ResumeSkeleton() {
  return (
    <div className="pointer-events-none" aria-hidden>
      {/* Personal info */}
      <div className="mb-10 pt-10" style={{ borderTop: '1px solid var(--c-border)' }}>
        <div className="h-3 w-24 rounded skeleton-shimmer mb-4" />
        <div className="h-4 w-40 rounded skeleton-shimmer mb-2" />
        <div className="h-3 w-64 rounded skeleton-shimmer" />
      </div>

      {/* Projects */}
      <div className="mb-10 pt-10" style={{ borderTop: '1px solid var(--c-border)' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="h-3 w-16 rounded skeleton-shimmer" />
          <div className="h-3 w-10 rounded skeleton-shimmer" />
        </div>
        {[0, 1].map(i => (
          <div key={i} className="py-3" style={i === 0 ? { borderBottom: '1px solid var(--c-border)' } : undefined}>
            <div className="h-3.5 w-1/3 rounded skeleton-shimmer mb-2" />
            <div className="h-3 w-1/4 rounded skeleton-shimmer mb-2" />
            <div className="h-3 w-3/4 rounded skeleton-shimmer" />
          </div>
        ))}
      </div>

      {/* Experience */}
      <div className="mb-10 pt-10" style={{ borderTop: '1px solid var(--c-border)' }}>
        <div className="h-3 w-20 rounded skeleton-shimmer mb-4" />
        <div className="py-3">
          <div className="h-3.5 w-2/5 rounded skeleton-shimmer mb-2" />
          <div className="h-3 w-1/3 rounded skeleton-shimmer mb-2" />
          <div className="h-3 w-2/3 rounded skeleton-shimmer" />
        </div>
      </div>

      {/* Skills */}
      <div className="mb-10 pt-10" style={{ borderTop: '1px solid var(--c-border)' }}>
        <div className="h-3 w-14 rounded skeleton-shimmer mb-4" />
        <div className="h-3 w-full rounded skeleton-shimmer" />
      </div>

      {/* Education */}
      <div className="pt-10" style={{ borderTop: '1px solid var(--c-border)' }}>
        <div className="h-3 w-20 rounded skeleton-shimmer mb-4" />
        <div className="h-3.5 w-1/2 rounded skeleton-shimmer mb-2" />
        <div className="h-3 w-1/3 rounded skeleton-shimmer" />
      </div>
    </div>
  )
}

// ---- Main page ----
// Six sections used to stack in one continuous scroll — an Apple System
// Settings-style tab bar keeps exactly one section on screen at a time
// instead, without adding a new navbar route (this is a sub-view of the
// existing /profile page, not new navigation).

const PROFILE_TABS = [
  { id: 'personal', label: 'Personal' },
  { id: 'projects', label: 'Projects' },
  { id: 'experience', label: 'Experience' },
  { id: 'skills', label: 'Skills' },
  { id: 'education', label: 'Education' },
  { id: 'preferences', label: 'Preferences' },
] as const
type ProfileTab = typeof PROFILE_TABS[number]['id']

// Shown on the Personal / Preferences tabs when personal_info doesn't exist
// yet — reachable only by navigating straight to /profile before the home
// page's onboarding gate has run (it normally creates this row first).
function NoPersonalInfoYet() {
  return (
    <div className="py-16 text-center">
      <p className="text-sm text-neutral-700 font-medium mb-1">Set up your profile first</p>
      <p className="text-xs text-neutral-600 max-w-sm mx-auto leading-relaxed">
        This is where your name, resume voice, and format live — but the setup that creates
        it hasn&apos;t run yet.{' '}
        <Link href="/" className="underline underline-offset-2 hover:text-neutral-800 transition-colors">
          Go to Home
        </Link>{' '}to finish onboarding.
      </p>
    </div>
  )
}

function ProfileTabBar({ active, onChange }: { active: ProfileTab; onChange: (t: ProfileTab) => void }) {
  return (
    <div
      className="flex items-center gap-1 mb-10 overflow-x-auto"
      style={{ borderBottom: '1px solid var(--c-border)' }}
    >
      {PROFILE_TABS.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className="relative px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors"
          style={{ color: active === t.id ? 'var(--color-neutral-900)' : 'var(--color-neutral-600)' }}
        >
          {t.label}
          {active === t.id && (
            <motion.div
              layoutId="profile-tab-underline"
              className="absolute left-0 right-0 -bottom-px h-[2px]"
              style={{ background: 'var(--c-accent)' }}
              transition={spring.snappy}
            />
          )}
        </button>
      ))}
    </div>
  )
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<FullProfile | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [activeTab, setActiveTab] = useState<ProfileTab>('personal')
  const [newProjectId, setNewProjectId] = useState<number | null>(null)
  const [newExpId, setNewExpId] = useState<number | null>(null)
  const [newSkillId, setNewSkillId] = useState<number | null>(null)
  const [newEducationId, setNewEducationId] = useState<number | null>(null)
  const [addingProject, setAddingProject] = useState(false)
  const [addingExp, setAddingExp] = useState(false)
  const [addingSkill, setAddingSkill] = useState(false)
  const [addingEducation, setAddingEducation] = useState(false)

  // Undo (Phase 6) — profile-section deletes are soft-deletes server-side now;
  // this toast is the immediate-window UX for it. The row stays recoverable
  // via the same restore endpoint even after the toast disappears — career
  // history is the most irreplaceable data in the product.
  // Rule: this toast is reserved for deletes (reversible, but destructive in
  // intent). Ordinary field saves use the inline SavedFlash checkmark instead —
  // don't blur the two; the toast's weight should stay tied to "you just
  // removed something."
  const [undoToast, setUndoToast] = useState<{ kind: 'project' | 'experience' | 'skill' | 'education'; id: number; label: string } | null>(null)
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showUndo = useCallback((kind: 'project' | 'experience' | 'skill' | 'education', id: number, label: string) => {
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current)
    setUndoToast({ kind, id, label })
    undoTimerRef.current = setTimeout(() => setUndoToast(null), 6000)
  }, [])

  const performUndo = async () => {
    if (!undoToast) return
    const { kind, id } = undoToast
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current)
    setUndoToast(null)
    try {
      if (kind === 'project') {
        const restored = await api.restoreProject(id)
        setProfile(prev => prev ? { ...prev, projects: [...prev.projects, restored].sort((a, b) => a.sort_order - b.sort_order) } : prev)
      } else if (kind === 'experience') {
        const restored = await api.restoreExperience(id)
        setProfile(prev => prev ? { ...prev, experience: [...prev.experience, restored].sort((a, b) => a.sort_order - b.sort_order) } : prev)
      } else if (kind === 'skill') {
        const restored = await api.restoreSkillCategory(id)
        setProfile(prev => prev ? { ...prev, skills: [...prev.skills, restored].sort((a, b) => a.sort_order - b.sort_order) } : prev)
      } else {
        const restored = await api.restoreEducation(id)
        setProfile(prev => prev ? { ...prev, education: [...prev.education, restored] } : prev)
      }
    } catch {
      // best-effort — if restore fails, the item just stays deleted
    }
  }

  const load = useCallback(async () => {
    try {
      setLoadError(false)
      setProfile(await api.getProfile())
    } catch {
      setLoadError(true)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Scroll newly added items into view — they appear at the bottom of the list
  useEffect(() => {
    if (!newProjectId) return
    const t = setTimeout(() => {
      document.querySelector(`[data-project="${newProjectId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 60)
    return () => clearTimeout(t)
  }, [newProjectId])

  useEffect(() => {
    if (!newExpId) return
    const t = setTimeout(() => {
      document.querySelector(`[data-exp="${newExpId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 60)
    return () => clearTimeout(t)
  }, [newExpId])

  useEffect(() => {
    if (!newSkillId) return
    const t = setTimeout(() => {
      document.querySelector(`[data-skill="${newSkillId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 60)
    return () => clearTimeout(t)
  }, [newSkillId])

  useEffect(() => {
    if (!newEducationId) return
    const t = setTimeout(() => {
      document.querySelector(`[data-education="${newEducationId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 60)
    return () => clearTimeout(t)
  }, [newEducationId])

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-neutral-600 text-sm">Could not reach the backend.</p>
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
      <div className="px-6 pb-24 max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={spring.gentle}
          className="pt-10 mb-10"
        >
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ ...spring.bouncy, delay: 0.04 }}
            className="mb-4"
          >
            <span className="brand-ring-glow-cool text-neutral-900">
              <BrandMark size={28} physicalStroke={1.5} />
            </span>
          </motion.div>
          <h1 className="text-3xl font-semibold text-neutral-900">Resume</h1>
          <p className="text-sm text-neutral-600 mt-1">
            What every generation reads from.
          </p>
        </motion.div>
        <ResumeSkeleton />
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

  const swapSkillOrder = async (idxA: number, idxB: number) => {
    const a = profile.skills[idxA]
    const b = profile.skills[idxB]
    const { id: _ia, ...restA } = a
    const { id: _ib, ...restB } = b
    await Promise.all([
      api.updateSkillCategory(a.id, { ...restA, sort_order: b.sort_order }),
      api.updateSkillCategory(b.id, { ...restB, sort_order: a.sort_order }),
    ])
    const updated = [...profile.skills]
    updated[idxA] = { ...a, sort_order: b.sort_order }
    updated[idxB] = { ...b, sort_order: a.sort_order }
    updated.sort((x, y) => x.sort_order - y.sort_order)
    setProfile(prev => prev ? { ...prev, skills: updated } : prev)
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
        start_date: null,
        end_date: null,
        github_url: null,
        description: '',
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

  const deleteProject = (id: number) => {
    // Clear "new project" marker if this was the unsaved project
    if (newProjectId === id) setNewProjectId(null)

    // Optimistic: remove from state immediately, restore the specific item on API failure
    const removed = profile!.projects.find(p => p.id === id)
    setProfile(prev => prev ? { ...prev, projects: prev.projects.filter(p => p.id !== id) } : prev)
    if (removed) showUndo('project', id, removed.name)

    api.deleteProject(id).catch(() => {
      // Restore only the deleted item — don't replace the whole array (other concurrent
      // changes would be lost if we used a snapshot of the full list)
      setUndoToast(null)
      if (removed) {
        setProfile(prev => prev
          ? { ...prev, projects: [...prev.projects, removed].sort((a, b) => a.sort_order - b.sort_order) }
          : prev)
      }
    })
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
        location: null,
        description: '',
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

  const deleteExperience = (id: number) => {
    if (newExpId === id) setNewExpId(null)

    const removed = profile!.experience.find(e => e.id === id)
    setProfile(prev => prev ? { ...prev, experience: prev.experience.filter(e => e.id !== id) } : prev)
    if (removed) showUndo('experience', id, `${removed.role} at ${removed.company}`)

    api.deleteExperience(id).catch(() => {
      setUndoToast(null)
      if (removed) {
        setProfile(prev => prev
          ? { ...prev, experience: [...prev.experience, removed].sort((a, b) => a.sort_order - b.sort_order) }
          : prev)
      }
    })
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
      setNewSkillId(s.id)
    } finally {
      setAddingSkill(false)
    }
  }

  const saveSkill = async (id: number, data: Omit<SkillCategory, 'id'>) => {
    const updated = await api.updateSkillCategory(id, data)
    setNewSkillId(null)
    setProfile(prev => prev ? { ...prev, skills: prev.skills.map(s => s.id === id ? updated : s) } : prev)
  }

  const deleteSkill = (id: number) => {
    if (newSkillId === id) setNewSkillId(null)
    const removed = profile!.skills.find(s => s.id === id)
    setProfile(prev => prev ? { ...prev, skills: prev.skills.filter(s => s.id !== id) } : prev)
    if (removed) showUndo('skill', id, removed.category)

    api.deleteSkillCategory(id).catch(() => {
      setUndoToast(null)
      if (removed) {
        setProfile(prev => prev
          ? { ...prev, skills: [...prev.skills, removed].sort((a, b) => a.sort_order - b.sort_order) }
          : prev)
      }
    })
  }

  // ---- Education handlers ----

  const addEducation = async () => {
    if (addingEducation) return
    setAddingEducation(true)
    try {
      const ed = await api.createEducation({
        school: 'School',
        degree: 'Degree',
        field: null,
        minor: null,
        start_date: null,
        end_date: null,
      })
      setProfile(prev => prev ? { ...prev, education: [...prev.education, ed] } : prev)
      setNewEducationId(ed.id)
    } finally {
      setAddingEducation(false)
    }
  }

  const saveEducation = async (id: number, data: Omit<Education, 'id'>) => {
    const updated = await api.updateEducation(id, data)
    setNewEducationId(null)
    setProfile(prev => prev ? { ...prev, education: prev.education.map(ed => ed.id === id ? updated : ed) } : prev)
  }

  const deleteEducation = (id: number) => {
    if (newEducationId === id) setNewEducationId(null)
    const removed = profile!.education.find(ed => ed.id === id)
    setProfile(prev => prev ? { ...prev, education: prev.education.filter(ed => ed.id !== id) } : prev)
    if (removed) showUndo('education', id, removed.school)

    api.deleteEducation(id).catch(() => {
      setUndoToast(null)
      if (removed) {
        setProfile(prev => prev ? { ...prev, education: [...prev.education, removed] } : prev)
      }
    })
  }

  return (
    <div className="px-6 pb-24 max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="pt-10 mb-10"
      >
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...spring.bouncy, delay: 0.04 }}
          className="mb-4"
        >
          <span className="brand-ring-glow-cool text-neutral-900">
            <BrandMark size={28} physicalStroke={1.5} />
          </span>
        </motion.div>
        <h1 className="text-3xl font-semibold text-neutral-900">Resume</h1>
        <p className="text-sm text-neutral-600 mt-1">
          What every generation reads from.
        </p>
      </motion.div>

      <ProfileTabBar active={activeTab} onChange={setActiveTab} />

      <AnimatePresence mode="wait">
      {activeTab === 'personal' && (
        <motion.section
          key="personal"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={spring.gentle}
        >
          {profile.personal ? (
            <PersonalInfoEditor
              personal={profile.personal}
              onSave={updated => setProfile(prev => prev ? { ...prev, personal: updated } : prev)}
            />
          ) : (
            <NoPersonalInfoYet />
          )}
        </motion.section>
      )}

      {activeTab === 'projects' && (
      <motion.section
        key="projects"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={spring.gentle}
      >
        <SectionHeader title="Projects" onAdd={addProject} adding={addingProject} />
        <div className="space-y-3">
          {profile.projects.length === 0 && (
            <p className="text-xs text-neutral-600 leading-relaxed">
              No projects yet. Two or three with a concrete outcome give the generator the most to work with.
            </p>
          )}
          <AnimatePresence>
            {profile.projects.map((p, i) => (
              <motion.div
                key={p.id}
                data-project={p.id}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{
                  opacity: { duration: 0.15, ease: 'easeOut' },
                  height: { duration: 0.2, ease: [0.25, 0, 0, 1] },
                }}
                className="overflow-hidden"
              >
                <ProjectCard
                  project={p}
                  startEditing={p.id === newProjectId}
                  isNew={p.id === newProjectId}
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
      )}

      {activeTab === 'experience' && (
      <motion.section
        key="experience"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={spring.gentle}
      >
        <SectionHeader title="Experience" onAdd={addExperience} adding={addingExp} />
        <div className="space-y-3">
          {profile.experience.length === 0 && (
            <p className="text-xs text-neutral-600 leading-relaxed">
              No experience yet. Even one role gives tailored resumes real grounding.
            </p>
          )}
          <AnimatePresence>
            {profile.experience.map((e, i) => (
              <motion.div
                key={e.id}
                data-exp={e.id}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{
                  opacity: { duration: 0.15, ease: 'easeOut' },
                  height: { duration: 0.2, ease: [0.25, 0, 0, 1] },
                }}
                className="overflow-hidden"
              >
                <ExperienceCard
                  exp={e}
                  startEditing={e.id === newExpId}
                  isNew={e.id === newExpId}
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
      )}

      {activeTab === 'skills' && (
      <motion.section
        key="skills"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={spring.gentle}
      >
        <SectionHeader title="Skills" onAdd={addSkill} adding={addingSkill} />
        <div className="space-y-3">
          {profile.skills.length === 0 && (
            <p className="text-xs text-neutral-600 leading-relaxed">
              No skills yet. Group them by category — Languages, Frameworks, Tools.
            </p>
          )}
          <AnimatePresence>
            {profile.skills.map((s, i) => (
              <motion.div
                key={s.id}
                data-skill={s.id}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{
                  opacity: { duration: 0.15, ease: 'easeOut' },
                  height: { duration: 0.2, ease: [0.25, 0, 0, 1] },
                }}
                className="overflow-hidden"
              >
                <SkillCard
                  skill={s}
                  startEditing={s.id === newSkillId}
                  isNew={s.id === newSkillId}
                  onSave={data => saveSkill(s.id, data)}
                  onDelete={() => deleteSkill(s.id)}
                  onMoveUp={() => swapSkillOrder(i, i - 1)}
                  onMoveDown={() => swapSkillOrder(i, i + 1)}
                  canMoveUp={i > 0}
                  canMoveDown={i < profile.skills.length - 1}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.section>
      )}

      {activeTab === 'education' && (
      <motion.section
        key="education"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={spring.gentle}
      >
        <SectionHeader title="Education" onAdd={addEducation} adding={addingEducation} />
        <div className="space-y-3">
          {profile.education.length === 0 && (
            <p className="text-xs text-neutral-600 leading-relaxed">
              No education yet. Add your degree and school.
            </p>
          )}
          <AnimatePresence>
            {profile.education.map(ed => (
              <motion.div
                key={ed.id}
                data-education={ed.id}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{
                  opacity: { duration: 0.15, ease: 'easeOut' },
                  height: { duration: 0.2, ease: [0.25, 0, 0, 1] },
                }}
                className="overflow-hidden"
              >
                <EducationCard
                  education={ed}
                  startEditing={ed.id === newEducationId}
                  isNew={ed.id === newEducationId}
                  onSave={data => saveEducation(ed.id, data)}
                  onDelete={() => deleteEducation(ed.id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.section>
      )}

      {activeTab === 'preferences' && (
        <motion.section
          key="preferences"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={spring.gentle}
          className={profile.personal ? 'space-y-10' : undefined}
        >
          {profile.personal ? (
            <>
              <VoiceEditor personal={profile.personal} onSave={updated => setProfile(prev => prev ? { ...prev, personal: updated } : prev)} />
              <div style={{ borderTop: '1px solid var(--c-border)', paddingTop: '2.5rem' }}>
                <TemplateEditor personal={profile.personal} onSave={updated => setProfile(prev => prev ? { ...prev, personal: updated } : prev)} />
              </div>
            </>
          ) : (
            <NoPersonalInfoYet />
          )}
        </motion.section>
      )}
      </AnimatePresence>

      <AnimatePresence>
        {undoToast && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={spring.snappy}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 px-4 py-3 rounded-xl text-sm z-50"
            style={{ background: 'var(--c-accent)', color: 'white', boxShadow: '0 8px 24px rgba(0,0,0,0.25)' }}
          >
            <span>Deleted &ldquo;{undoToast.label}&rdquo;</span>
            <button onClick={performUndo} className="font-semibold underline underline-offset-2">
              Undo
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
