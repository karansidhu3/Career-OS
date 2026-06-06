# CareerOS — Roadmap

## What it does

Karan pastes a job description → CareerOS generates a tailored resume (LaTeX) + cover letter
using his persistent profile DB. Copy into Overleaf, apply on LinkedIn.

---

## Sprints

### Sprint 1 — Profile DB ✅ Done
- PostgreSQL schema: personal info, education, experience, projects, skills
- Seed data: Karan's full profile
- Admin CRUD endpoints: `GET/PUT /admin/profile/*`
- Tables auto-created on server startup

### Sprint 2 — Generation Pipeline ✅ Done
- `POST /admin/jobs/generate` — accepts raw JD text, returns immediately (status=processing)
- Background task calls Claude via tool use; writes fit score + rationale + LaTeX + cover letter to DB
- Prompt engineering: scanner-first, compression-first system prompt with mandatory number preservation
- JD auto-extracts job title + company; no manual input fields

### Sprint 3 — Dashboard UI ✅ Done
- Next.js frontend (App Router)
- Paste box with JD persisted in sessionStorage across refreshes
- Inline PDF preview (iframe, Tectonic-compiled) in result state
- Strategic analysis (GOOD FIT / GAPS / IMPROVEMENT PLAN) shown before download
- Selected projects bar — see which projects the AI chose to emphasize
- Cover letter editable before download; PATCH endpoint persists edits
- Cover letter PDF download (LaTeX-compiled, charter font)
- LaTeX source toggle with copy button
- Mark applied / Got interview / offer status actions
- `/applications` page — full history with filter tabs and grouped timeline

### Sprint 4 — Deploy to Railway ✅ Done
- Backend service: FastAPI on Railway (railway.toml + nixpacks)
- Frontend service: Next.js on Railway (railway.toml + nixpacks)
- Database: Railway Postgres (DATABASE_URL env var)
- CORS driven by ALLOWED_ORIGINS env var (comma-separated)
- Seed runs automatically on startup (idempotent)
- .env.example files in backend/ and frontend/ for reference

---

## Post-launch improvements ✅ Done

- Auto-extract job title + company from JD (no manual input fields)
- Token usage tracking per generation (input, output, cache read/write)
- Cost estimate per generation (`cost_usd` computed from token counts)
- Cover letter PDF download — separate LaTeX template (charter font, gray header band)
- Cover letter editable in UI before download (PATCH endpoint persists edits)
- Regenerate button (re-runs generation with stored JD)
- Inline PDF preview in result state (iframe via `/resume-preview.pdf`)
- Selected projects field — AI commits to project list before writing; shown as "Emphasized" pills
- Candidacy insights — synthesizes pattern across 3+ applications; cached 1 hour in localStorage
- `/applications` page — full history browser with filter tabs and grouped timeline
- `cover_letter_voice` field on PersonalInfo — injected into cover letter generation prompt
- Rate limiting: 30/hour generate/regenerate, 20/hour insights (slowapi)
- API key auth on all `/admin/` routes (opt-in via `API_KEY` env var)
- SQL migration runner on startup (idempotent, alphabetical order from `backend/migrations/`)
- Tectonic package cache warmed at startup in background task

## Later (when new projects ship)

When Karan finishes a new polished project:
1. Add it to the profile DB via the Profile page
2. All future generations automatically include it
3. No code changes needed

---

## Deliberately out of scope

- Automated job ingestion (Adzuna, Indeed, scraping)
- Email digests
- Scheduled background jobs
- Auto-applying to jobs
- Multi-user support
