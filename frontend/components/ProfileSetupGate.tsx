'use client'

import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  api,
  ImportedEducation,
  ImportedExperience,
  ImportedProject,
  ImportedSkillCategory,
  ProfileImportDraft,
} from '@/lib/api'
import { spring } from '@/lib/motion'
import { Field, Input, PrimaryButton, inputCls, inputStyle } from '@/components/FormControls'
import { SectionLabel } from '@/components/SectionLabel'

type Stage =
  | { kind: 'choose' }
  | { kind: 'paste' }
  | { kind: 'scratch' }
  | { kind: 'extracting' }
  | { kind: 'review'; draft: ProfileImportDraft }
  | { kind: 'error'; message: string }

const emptyPersonalWrite = {
  target_roles: [] as string[],
  target_locations: [] as string[],
  cover_letter_voice: '',
}

// ---- Review step — one editable card per extracted item, removable before saving ----

function ReviewEducation({ items, onChange }: { items: ImportedEducation[]; onChange: (i: ImportedEducation[]) => void }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-3">
      <SectionLabel>Education</SectionLabel>
      {items.map((e, i) => (
        <div key={i} className="flex items-start gap-3 py-2" style={{ borderBottom: '1px solid var(--c-border)' }}>
          <div className="flex-1 grid grid-cols-2 gap-2">
            <Input value={e.school} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, school: v } : x))} placeholder="School" />
            <Input value={e.degree} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, degree: v } : x))} placeholder="Degree" />
          </div>
          <button onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-xs text-neutral-400 hover:text-red-400 mt-2 transition-colors">Remove</button>
        </div>
      ))}
    </div>
  )
}

function ReviewExperience({ items, onChange }: { items: ImportedExperience[]; onChange: (i: ImportedExperience[]) => void }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-3">
      <SectionLabel>Experience</SectionLabel>
      {items.map((e, i) => (
        <div key={i} className="flex items-start gap-3 py-2" style={{ borderBottom: '1px solid var(--c-border)' }}>
          <div className="flex-1 grid grid-cols-2 gap-2">
            <Input value={e.role} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, role: v } : x))} placeholder="Role" />
            <Input value={e.company} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, company: v } : x))} placeholder="Company" />
          </div>
          <button onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-xs text-neutral-400 hover:text-red-400 mt-2 transition-colors">Remove</button>
        </div>
      ))}
    </div>
  )
}

function ReviewProjects({ items, onChange }: { items: ImportedProject[]; onChange: (i: ImportedProject[]) => void }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-3">
      <SectionLabel>Projects</SectionLabel>
      {items.map((p, i) => (
        <div key={i} className="flex items-start gap-3 py-2" style={{ borderBottom: '1px solid var(--c-border)' }}>
          <div className="flex-1">
            <Input value={p.name} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, name: v } : x))} placeholder="Project name" />
          </div>
          <button onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-xs text-neutral-400 hover:text-red-400 mt-2 transition-colors">Remove</button>
        </div>
      ))}
    </div>
  )
}

function ReviewSkills({ items, onChange }: { items: ImportedSkillCategory[]; onChange: (i: ImportedSkillCategory[]) => void }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-3">
      <SectionLabel>Skills</SectionLabel>
      {items.map((s, i) => (
        <div key={i} className="flex items-start gap-3 py-2" style={{ borderBottom: '1px solid var(--c-border)' }}>
          <div className="flex-1 grid grid-cols-3 gap-2">
            <Input value={s.category} onChange={v => onChange(items.map((x, j) => j === i ? { ...x, category: v } : x))} placeholder="Category" />
            <div className="col-span-2">
              <Input
                value={s.items.join(', ')}
                onChange={v => onChange(items.map((x, j) => j === i ? { ...x, items: v.split(',').map(t => t.trim()).filter(Boolean) } : x))}
                placeholder="Python, TypeScript, ..."
              />
            </div>
          </div>
          <button onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-xs text-neutral-400 hover:text-red-400 mt-2 transition-colors">Remove</button>
        </div>
      ))}
    </div>
  )
}

export function ProfileSetupGate({ onComplete }: { onComplete: () => void }) {
  const [stage, setStage] = useState<Stage>({ kind: 'choose' })
  const [pasteText, setPasteText] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Scratch-path + review-step personal fields share this state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')

  const runExtraction = async (input: { file: File } | { text: string }) => {
    setStage({ kind: 'extracting' })
    try {
      const draft = await api.importResume(input)
      setName(draft.personal.name ?? '')
      setEmail(draft.personal.email ?? '')
      setStage({ kind: 'review', draft })
    } catch (e) {
      let detail = e instanceof Error ? e.message : 'Could not extract profile data.'
      try { detail = JSON.parse(detail).detail ?? detail } catch { /* not JSON */ }
      setStage({ kind: 'error', message: detail })
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) runExtraction({ file })
  }

  const saveScratch = async () => {
    if (!name.trim() || !email.trim()) return
    setBusy(true)
    try {
      await api.updatePersonal({ name: name.trim(), email: email.trim(), phone: null, linkedin: null, github: null, location: null, ...emptyPersonalWrite })
      onComplete()
    } finally {
      setBusy(false)
    }
  }

  const saveReviewedDraft = async (draft: ProfileImportDraft) => {
    if (!name.trim() || !email.trim()) return
    setBusy(true)
    try {
      await api.updatePersonal({
        name: name.trim(),
        email: email.trim(),
        phone: draft.personal.phone,
        linkedin: draft.personal.linkedin,
        github: draft.personal.github,
        location: draft.personal.location,
        ...emptyPersonalWrite,
      })
      // Sequential per-type creation — small lists, clarity over throughput.
      for (const e of draft.education) {
        await api.createEducation(e)
      }
      for (const [i, e] of draft.experience.entries()) {
        await api.createExperience({ ...e, sort_order: i })
      }
      for (const [i, p] of draft.projects.entries()) {
        await api.createProject({ ...p, sort_order: i })
      }
      for (const [i, s] of draft.skills.entries()) {
        await api.createSkillCategory({ ...s, sort_order: i })
      }
      onComplete()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="pt-16 max-w-lg mx-auto">
      <AnimatePresence mode="wait">
        {stage.kind === 'choose' && (
          <motion.div key="choose" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <h1 className="text-2xl font-semibold text-neutral-900 mb-2 text-center">Set up your profile</h1>
            <p className="text-sm text-neutral-500 text-center mb-10 leading-relaxed">
              CareerOS reads this to write tailored resumes and cover letters.
            </p>
            <div className="space-y-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full text-left px-5 py-4 rounded-2xl transition-colors hover:bg-black/[0.02]"
                style={{ border: '1px solid var(--c-border)' }}
              >
                <p className="text-sm font-semibold text-neutral-800">Upload existing resume</p>
                <p className="text-xs text-neutral-400 mt-0.5">PDF or DOCX — we&apos;ll extract your info for review</p>
              </button>
              <input ref={fileInputRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleFileChange} />

              <button
                onClick={() => setStage({ kind: 'paste' })}
                className="w-full text-left px-5 py-4 rounded-2xl transition-colors hover:bg-black/[0.02]"
                style={{ border: '1px solid var(--c-border)' }}
              >
                <p className="text-sm font-semibold text-neutral-800">Paste resume text</p>
                <p className="text-xs text-neutral-400 mt-0.5">Copy from anywhere — no file needed</p>
              </button>

              <button
                onClick={() => setStage({ kind: 'scratch' })}
                className="w-full text-left px-5 py-4 rounded-2xl transition-colors hover:bg-black/[0.02]"
                style={{ border: '1px solid var(--c-border)' }}
              >
                <p className="text-sm font-semibold text-neutral-800">Start from scratch</p>
                <p className="text-xs text-neutral-400 mt-0.5">Add your name and fill in the rest later</p>
              </button>
            </div>
          </motion.div>
        )}

        {stage.kind === 'paste' && (
          <motion.div key="paste" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <h1 className="text-2xl font-semibold text-neutral-900 mb-6 text-center">Paste your resume text</h1>
            <textarea
              value={pasteText}
              onChange={e => setPasteText(e.target.value)}
              rows={12}
              placeholder="Paste your resume content here…"
              className={`${inputCls} resize-none leading-relaxed`}
              style={inputStyle}
            />
            <div className="flex items-center justify-between mt-4">
              <button onClick={() => setStage({ kind: 'choose' })} className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors">Back</button>
              <PrimaryButton onClick={() => runExtraction({ text: pasteText })} disabled={pasteText.trim().length < 20}>
                Extract profile
              </PrimaryButton>
            </div>
          </motion.div>
        )}

        {stage.kind === 'extracting' && (
          <motion.div key="extracting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-4 pt-12">
            <div className="w-8 h-8 rounded-full animate-spin" style={{ border: '2px solid var(--c-accent-dim)', borderTopColor: 'var(--c-accent)' }} />
            <p className="text-sm text-neutral-500">Reading your resume…</p>
          </motion.div>
        )}

        {stage.kind === 'error' && (
          <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center pt-12">
            <p className="text-sm text-neutral-700 font-medium mb-2">{stage.message}</p>
            <div className="flex items-center justify-center gap-4 mt-4">
              <button onClick={() => setStage({ kind: 'paste' })} className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors">Paste text instead</button>
              <button onClick={() => setStage({ kind: 'choose' })} className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors">Start over</button>
            </div>
          </motion.div>
        )}

        {stage.kind === 'scratch' && (
          <motion.div key="scratch" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle}>
            <h1 className="text-2xl font-semibold text-neutral-900 mb-6 text-center">A few basics to start</h1>
            <div className="space-y-3">
              <Field label="Name"><Input value={name} onChange={setName} placeholder="Jane Doe" /></Field>
              <Field label="Email"><Input value={email} onChange={setEmail} placeholder="jane@example.com" /></Field>
            </div>
            <p className="text-xs text-neutral-400 mt-4 leading-relaxed">
              Add education, experience, projects, and skills on the Profile page whenever you&apos;re ready.
            </p>
            <div className="flex items-center justify-between mt-6">
              <button onClick={() => setStage({ kind: 'choose' })} className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors">Back</button>
              <PrimaryButton onClick={saveScratch} disabled={busy || !name.trim() || !email.trim()}>
                {busy ? 'Saving…' : 'Continue'}
              </PrimaryButton>
            </div>
          </motion.div>
        )}

        {stage.kind === 'review' && (
          <motion.div key="review" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.gentle} className="max-w-xl">
            <h1 className="text-2xl font-semibold text-neutral-900 mb-2 text-center">Review what we found</h1>
            <p className="text-xs text-neutral-400 text-center mb-8 leading-relaxed">
              Edit anything that&apos;s wrong, remove anything you don&apos;t want. Nothing is saved until you confirm.
            </p>

            <div className="space-y-2 mb-6">
              <Field label="Name"><Input value={name} onChange={setName} placeholder="Your name" /></Field>
              <Field label="Email"><Input value={email} onChange={setEmail} placeholder="you@example.com" /></Field>
            </div>

            <div className="space-y-6">
              <ReviewEducation
                items={stage.draft.education}
                onChange={education => setStage({ kind: 'review', draft: { ...stage.draft, education } })}
              />
              <ReviewExperience
                items={stage.draft.experience}
                onChange={experience => setStage({ kind: 'review', draft: { ...stage.draft, experience } })}
              />
              <ReviewProjects
                items={stage.draft.projects}
                onChange={projects => setStage({ kind: 'review', draft: { ...stage.draft, projects } })}
              />
              <ReviewSkills
                items={stage.draft.skills}
                onChange={skills => setStage({ kind: 'review', draft: { ...stage.draft, skills } })}
              />
            </div>

            <div className="flex items-center justify-between mt-8">
              <button onClick={() => setStage({ kind: 'choose' })} className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors">Start over</button>
              <PrimaryButton onClick={() => saveReviewedDraft(stage.draft)} disabled={busy || !name.trim() || !email.trim()}>
                {busy ? 'Saving…' : 'Looks good — save my profile'}
              </PrimaryButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
