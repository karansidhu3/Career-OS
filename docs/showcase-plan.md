# CareerOS — Showcase Plan

> Living document. Refine as recording progresses.

---

## Positioning

**Not:** AI resume generator  
**Is:** Application intelligence infrastructure

One sentence for every piece of copy, every title card, every voiceover brief:
> "Your career history is a dataset. I got tired of explaining it to tools that forget. So I built one that doesn't."

---

## Deliverables

| Cut | Length | Purpose |
|-----|--------|---------|
| Full | ~90s | Portfolio, GitHub README, personal site |
| Medium | ~60s | LinkedIn, project pages |
| Short | ~30s | Twitter/X, quick share |

All three cuts from the same recording session. Edit long → short.

---

## Narrative Arc (90s master)

### Scene 1 — Hook (0:00–0:10)
**What's on screen:** The core loop. No intro. Paste a polished JD, hit ⌘↵, watch the spinner, 20 seconds later the result appears.  
**Audio:** Ambient only. No voiceover.  
**Purpose:** Product appears before it's explained. The speed is the hook. Audience is already asking "what is that?"

---

### Scene 2 — The problem (0:10–0:20)
**What's on screen:** A ChatGPT conversation — someone typing their background out for the fourth time. Cut before they finish.  
**Caption:** *"Every time. To a tool that forgets."*  
**Audio:** Voiceover fades in.  
**VO:** *"Every application starts the same way. Re-explain your background. Re-select your projects. Re-write for the role. To a tool that remembers nothing."*  
**Note:** One specific scene. Not a bullet list of pain points. Specificity creates recognition.

---

### Scene 3 — The model shift (0:20–0:30)
**What's on screen:** Slow pan through the profile page. Structured data — Experience with dates and bullets, Projects with tech stacks, Skills by category, the `cover_letter_voice` field.  
**VO:** *"Career history isn't a paragraph you paste. It's structured data. Once it's stored correctly, every application is a query against that data."*  
**Purpose:** The intellectual reframe. Sets up everything that follows. The `cover_letter_voice` field is a visual detail that signals taste — leave it visible.

---

### Scene 4 — The intelligence layer (0:30–1:00) ★ CENTERPIECE
**Three beats, no pauses between them.**

**Beat 1 (3s):** JD paste. ⌘↵.

**Beat 2 (12s):** Strategic analysis appears — Good fit / Gaps / Improvement plan. Hold on this. Let the audience read a bullet or two. The analysis must be sharp and specific (see Demo Data requirements). This is the moment that separates analysis from generation.  
**VO:** *"The system reads the job description, assesses fit, and identifies gaps. Not as prose. As structured reasoning."*

**Beat 3 (10s):** Project pills appear — "Emphasized: MarketMind AI · FDA Network Analysis." Pan to show there are other projects in the profile that weren't selected.  
**VO:** *"It selected which projects to include. You didn't."*

**Note:** If the demo analysis reads like filler, change the JD — don't change the shot. This scene either makes the demo or breaks it.

---

### Scene 5 — The artifact (1:00–1:12)
**What's on screen:** Resume PDF preview loading in the iframe. Let it render. Then the download button. Then a brief cut to the cover letter (editable textarea).  
**VO:** *"LaTeX output. Tectonic compilation. Always the same template, always compilable, always ATS-safe. The cover letter is editable before it compiles."*  
**Note:** The PDF quality must be visibly better than a Word template. If it isn't on the demo data, fix the LaTeX before recording.

---

### Scene 6 — The pipeline (1:12–1:25)
**What's on screen:** Applications page. Grouped timeline — Active (amber dot, "Interview" label), This Week, Earlier. One row with gap signal text visible below the title.  
**VO:** *"Applications persist as a pipeline. Status moves from generated → applied → interview → offer. The gap analysis from each application is surfaced inline."*  
**Note:** Make sure the demo data has at least one entry in "Interview" stage with the amber marker showing. That marker is a strong visual detail.

---

### Scene 7 — System-level intelligence (1:25–1:42)
**What's on screen:** Home page with candidacy insights section populated. Headline. Observed / Gap / Action blocks.  
**VO:** *"After enough applications, the system synthesizes patterns — about which roles fit your profile, what's working, and what isn't. That's the part I didn't plan to build."*  
**Note:** "The part I didn't plan to build" is the most human line in the demo. It signals genuine use, not a designed feature list. Keep it.

---

### Scene 8 — Engineering (1:42–1:54)
**What's on screen:** Animated architecture diagram (built in Figma). Data flow: `JD text → Claude API → {resume_latex, cover_letter, strategic_note, selected_projects} → PostgreSQL → Tectonic → PDF`  
**VO:** *"POST returns immediately. Claude runs in the background. The frontend polls. Background task architecture — because Railway's proxy timeout is 30 seconds and generation takes 20."*  
**Note:** Three sentences. One real constraint, one real solution. More credibility than any stack slide. Do NOT show stack logos.

---

### Scene 9 — Close (1:54–2:00)
**What's on screen:** Home screen. Idle state. Textarea focused. Cursor blinking.  
**Caption:** *"Currently in use."*  
**Audio:** Silence. Fade to black.

---

## Cut Guides

### 30s cut
| Segment | Time |
|---------|------|
| Scene 1 — Loop running | 0:00–0:08 |
| Scene 4 beat 2+3 — Analysis + pills | 0:08–0:20 |
| Scene 6 — Pipeline flash | 0:20–0:26 |
| Scene 9 — Close | 0:26–0:30 |

### 60s cut
Scenes 1 → 3 → 4 → 5 → 7 → 9. Skip Scene 2 (problem) — Scene 3 implies it. Skip Scene 8 (engineering).

### 90s cut
Full arc above.

---

## Hero Shots (priority order)

1. **Strategic analysis** — goodFit / gaps / plan rendered as bullets. The single most important screen. Must be sharp and specific. If the analysis reads like filler, change the JD.
2. **Project pills** — "Emphasized: X · Y" with visible proof that other projects exist and weren't chosen. The selection is the point.
3. **Candidacy insights headline** — Whatever specific, non-generic sentence the system produces after 8–10 applications. This is what people screenshot.
4. **Generation clock** — Timer overlay during the generating state. Stops at ~20s when result appears. Time is the proof point.
5. **Applications pipeline** — Amber interview marker, grouped timeline, gap signal text inline in rows.

---

## Demo Data Requirements

The recording depends entirely on the quality of the synthetic data. Requirements:

### JD for the main loop demo
- Should be for a role that's a strong but not perfect fit (fit score 7–8/10)
- Must produce a strategic analysis with a specific, non-generic gap (e.g., "No production TypeScript — Python async patterns transfer directly")
- Must cause the system to choose MarketMind AI as the primary project

### Applications history
- Minimum 8–10 synthetic applications to unlock candidacy insights
- At least 1 in "Interview" status (for the amber marker)
- Mix of applied/generated/skipped for realistic pipeline view
- Candidacy insights headline must be sharp and specific — regenerate if it's vague

### Profile
- All sections populated: Personal, Education, Experience (2), Projects (4+), Skills
- `cover_letter_voice` field populated with a specific voice description
- Projects list should have more entries than the 2–3 that get selected (so the selection looks like a real decision)

---

## Voiceover Direction

**Tone:** Builder's voice. First person. Thinks in systems. Not a pitch.

**Avoid:**
- "CareerOS helps you…"
- "AI-powered"
- Narrating what's on screen ("Here you can see…")
- Feature lists

**Target:**
- *"I got tired of explaining myself to tools that forget. So I built one that doesn't."*
- *"Career history isn't a paragraph you paste. It's structured data."*
- *"The system selected which projects to include. You didn't."*
- *"That's the part I didn't plan to build."*
- *"Currently in use."*

**ElevenLabs settings:** Slow pacing. Confident. Minimal affect. Not warm/friendly — precise and understated.

---

## Motion Graphics (Figma)

| Graphic | Description | Used in |
|---------|-------------|---------|
| Architecture diagram | Animated data flow: JD → Claude → split outputs → DB → Tectonic → PDF. No stack logos. | Scene 8 |
| Kinetic collapse | "12 manual steps" list collapses → single line "paste + ⌘↵" | Scene 2 (optional) |
| Profile data reveal | Horizontal pan showing structured fields — not a text box | Scene 3 |
| Generation clock | Semi-transparent timer overlay on generating state | Scene 1, Scene 4 |

---

## Production Notes

- **Record in dark mode.** The charcoal surface and warm neutrals photograph better than light mode. Contrast is higher. The amber interview marker and ink buttons read clearly.
- **Window size:** Record at exactly 1440×900 or 1512×982 (MacBook native). Don't record full-screen on an external monitor — letterboxing looks bad in a video frame.
- **Screen Studio settings:** Motion blur on. Zoom transitions for key moments (the analysis appearing, the pills appearing). Background: black or very dark — let the product float.
- **Cursor:** Hide it during the generation wait. Show it for intentional interactions (the paste, the ⌘↵, the download click).
- **Don't record API errors.** Make sure the backend is warm and the demo JD produces clean output before hitting record.

---

## What to Cut / Never Include

- Stack enumeration (Next.js / FastAPI / PostgreSQL) — table stakes, communicates nothing
- "AI-generated" language anywhere
- Feature lists
- The word "tailored"
- Anything that could apply to a different AI resume tool
- The "continuously evolving through real-world use" close — replace with idle state + "Currently in use."

---

## Open Questions

- [ ] Which JD produces the sharpest strategic analysis? Test 3–4 before deciding on the demo JD.
- [ ] Does the PDF render cleanly enough to hold a 4-second close-up? Check at 1:1 zoom.
- [ ] What does the candidacy insights headline say on the current demo data? Is it specific enough to screenshot?
- [ ] Record light mode version too as a backup — decide in edit.
- [ ] ElevenLabs voice selection: test 3 voices against the VO script before committing.
