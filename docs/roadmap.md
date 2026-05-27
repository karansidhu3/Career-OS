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

### Sprint 2 — Generation Pipeline 🔨 Next
- `POST /admin/jobs/generate` — accepts raw JD text + optional title/company
- Single Claude API call returns: fit score (1–10) + 3-bullet rationale + LaTeX resume + cover letter
- Job record stored to DB with all generated content
- Prompt engineering: profile context + LaTeX template + cover letter spec baked in

### Sprint 3 — Dashboard UI
- Next.js 15 frontend
- Paste box for raw JD text
- Loading state while Claude generates (~10–20s)
- Display: fit score, rationale, resume (.tex), cover letter
- One-click copy for .tex and cover letter text
- Mark job as applied / skipped
- History list: all past generations, filterable by status

### Sprint 4 — Deploy to Railway ✅ Done
- Backend service: FastAPI on Railway (railway.toml + nixpacks)
- Frontend service: Next.js on Railway (railway.toml + nixpacks)
- Database: Railway Postgres (DATABASE_URL env var)
- CORS driven by ALLOWED_ORIGINS env var (comma-separated)
- Seed runs automatically on startup (idempotent)
- .env.example files in backend/ and frontend/ for reference

---

## Later (when new projects ship)

When Karan finishes a new polished project:
1. Add it to the profile DB via `POST /admin/profile/projects`
2. All future generations automatically include it
3. No code changes needed

---

## Deliberately out of scope

- Automated job ingestion (Adzuna, Indeed, scraping)
- Email digests
- Scheduled background jobs
- Auto-applying to jobs
- Multi-user support
