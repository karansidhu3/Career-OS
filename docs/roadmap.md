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

## Multi-Tenant Migration (started 2026-06-30)

CareerOS is migrating from a single-user personal tool to a product other people (friends,
classmates, eventually strangers) can sign up for, each with their own account, profile, and
job history. Triggered by a security review that prompted a rethink of the product's scope.

**Why:** Karan does not want to be the AI bill-payer for other users' generations. Each user
will eventually bring their own AI provider API key — CareerOS owns the workflow, orchestration,
and UX; users own their AI usage and its cost. This directly supersedes the old "multi-user
support: out of scope" line below.

**Guiding constraint:** none of this work may raise Karan's own AI token spend. Any phase whose
naive implementation would add an AI call (e.g. resume-import extraction, skill-confidence
inference) is redesigned to either bill the user's own key (once Phase 3 exists) or avoid the
AI call entirely (deterministic logic instead).

### Phase 0 — Infrastructure decisions (locked)

- **Auth**: Clerk. Free tier covers up to 50,000 MRU (monthly *retained* users — someone only
  counts if they return 24h+ after signup, so casual signups are free). GitHub OAuth is the
  primary sign-in path since the target audience is software engineers.
- **Encryption master key** (for Phase 3's BYO API keys): a Railway secret, never in code or DB.
- **Job queue**: ARQ + Redis — fits the existing async Python stack without Celery's complexity.
- **Object storage**: Cloudflare R2 for compiled PDFs (S3-compatible, cheaper egress).

### Phase 1 — Auth + multi-tenant schema — ✅ DONE, live in production (2026-07-01)

- Clerk session-JWT auth replaces the old static `X-API-Key` scheme entirely
  (`backend/app/auth.py` deleted; `backend/app/clerk_auth.py` is the new dependency).
  JWTs are verified against Clerk's published JWKS; JIT user provisioning on first sign-in.
  The frontend's `/api/[...path]` proxy forwards the signed-in user's real Clerk session token
  (`Authorization: Bearer ...`) instead of a shared static secret.
- Every table (`job`, `personal_info`, `education`, `experience`, `project`, `skill_category`)
  has a `user_id` FK, `NOT NULL` once backfilled. Every router query and write is scoped to the
  authenticated user — verified with cross-user isolation integration tests, not just inspection.
- **Row-Level Security**, enforced via a dedicated **non-superuser Postgres role**
  (`careeros_app`, wired as `APP_DATABASE_URL` / `app_engine` in `backend/app/database.py`).
  This was a real near-miss caught during verification: RLS is silently a no-op against the
  superuser role that Docker's `postgres` image (and Railway's default Postgres role) creates —
  `FORCE ROW LEVEL SECURITY` has no effect on superusers, no override exists. The app now runs
  all request-handling queries through the restricted role; the original owner role is reserved
  for migrations only. Role-creation SQL is documented in
  `backend/migrations/006_enable_row_level_security.sql`'s header comment.
- **One-time legacy-data claim**: the first real Clerk sign-in ever (`is_first_ever_user` check
  in `app.clerk_auth.get_current_user`) inherits every pre-multi-tenant row (all rows with
  `user_id IS NULL`). This is a "first signer wins," not an email match — Karan confirmed this
  is acceptable since he controls exactly when the app goes live and who gets the link.
  Verified end-to-end in production: Karan's real job history and profile were correctly
  claimed onto his account.
- Cover letter LaTeX no longer hardcodes a single identity — pulls name/contact info from the
  requesting user's own profile row.
- `app/seed.py` (the old single-profile bootstrap script) is now dead code — it inserted
  ownerless rows, which RLS rejects and which don't make sense once profiles are per-user.
  Left in the repo, not called from `main.py`'s lifespan. Needs a per-user redesign (e.g.
  seeding a demo Clerk account) before it's useful again.

**Three production incidents hit and fixed during this rollout** (useful precedent for future
migrations that touch data integrity, the auth boundary, or connection-scoped database state):

1. **Migration 008 (`user_id NOT NULL`) crashed startup.** It ran unconditionally in the same
   startup batch as the columns being added, before anyone had signed in — production's
   pre-existing rows still had `user_id IS NULL`, so `ALTER COLUMN ... SET NOT NULL` raised and
   crashed the app. All migrations run in one transaction, so the failure rolled back cleanly
   (nothing partially applied) and Railway kept the previous deployment live — no downtime, but
   the new code never actually went out until fixed. **Fix:** wrap each `ALTER` in a
   `DO $$ IF NOT EXISTS (... WHERE user_id IS NULL) THEN ALTER ... END IF; END $$` block, so it's
   a no-op until the legacy claim has actually run and self-applies on a later restart. Also had
   to teach `_run_migrations()`'s statement splitter to treat `$$`-delimited regions as atomic —
   naive semicolon-splitting was breaking DO blocks into invalid fragments.
2. **Frontend healthcheck failed under Clerk auth.** `railway.toml` pointed `healthcheckPath` at
   `"/"`, which `proxy.ts` now protects with `auth.protect()`. Railway's health probe carries no
   Clerk session, so it got a 307 redirect instead of 200 and the healthcheck failed (same safe
   rollback behavior — no downtime, but blocked). **Fix:** added a dedicated public
   `/api/health` route excluded from the Clerk auth check, pointed `healthcheckPath` at it.
3. **RLS connection-pooling race caused intermittent 500s on writes.** Adding a project (and
   likely any create/update route doing `commit()` then `refresh()`) intermittently failed with
   `invalid input syntax for type uuid: ""`. Two compounding bugs: (a) `AsyncSession`'s default
   behavior releases its connection back to the pool on every `commit()` — since the RLS GUC
   (`app.current_user_id`) is set session-scoped specifically to survive a request's own commits,
   a *different concurrent request* could grab the released connection between this request's
   commit and its next query, and that other request's cleanup could reset the GUC first;
   (b) `get_db()`'s cleanup called `rollback()` then `set_config(..., false)` to reset the GUC but
   never committed that reset — Postgres reverts a session-scoped `SET` issued inside a
   transaction if that transaction later rolls back (a real, easy-to-miss behavior), so the reset
   silently never took effect, meaning a *real* leftover user_id — not just an empty string —
   could persist on a reused connection. **Fix:** `get_db()` now explicitly holds one connection
   for the entire request via `engine.connect()`, never releasing it mid-request regardless of
   internal commits; cleanup now commits the GUC reset so it can't be rolled back away. Reproduced
   deterministically with event-synchronized concurrent asyncio tasks against real Postgres —
   confirmed the exact production error first, then confirmed the fix — and added as a permanent
   regression test (`backend/tests/integration/test_database.py`) against the real
   `app.database.get_db`, since the existing test fixtures override `get_db` entirely for
   convenience and wouldn't have caught this.

**Lessons for future migrations:**
- Anything touching `user_id`/data-integrity constraints must assume production has real
  pre-existing unclaimed data — never assume a clean database.
- Anything touching `proxy.ts`'s route protection must double-check `healthcheckPath` (both
  services) still resolves publicly.
- Any RLS-dependent session-level Postgres state (GUCs set via `set_config`) must be paired with
  a connection held for the whole request. SQLAlchemy's `AsyncSession` releases connections back
  to the pool between transactions by default, which silently breaks this pattern under
  concurrent load. Any new code opening its own session outside `get_db` needs the same care.

### Phase 2 — AI provider abstraction — not started

Pure refactor, zero new behavior, zero token cost. Introduce an `LLMClient` interface with an
`AnthropicAdapter` wrapping the current SDK calls. `generate_materials`/`generate_insights` call
the interface, not the Anthropic SDK directly. Still uses Karan's system key globally at this
point — this phase just builds the seam Phase 3 plugs into. Sets up for provider flexibility in
2+ years without another rewrite.

### Phase 3 — Encrypted BYO API key — not started

The phase that actually stops Karan's bill growing with other users' usage. New `ai_credentials`
table: `user_id`, `provider`, `encrypted_key` (envelope-encrypted with the Phase 0 master key,
versioned for future key rotation), `key_hint` (last 4 chars, for UX), `label`,
`last_verified_at`. Settings UI to add/verify/rotate/delete a key. One validation call on
key-add (tiny, billed to the user's own key, never Karan's). Every generation and insights call
switches to pull the *requesting user's* decrypted key instead of `ANTHROPIC_API_KEY` — this
also migrates `generate_insights`, which currently silently bills Karan's key for every user's
candidacy insights and would otherwise be missed.

### Phase 4 — Onboarding + profile import — not started

Enforced order: account creation → API key setup (validated) → profile creation. This ordering
is deliberate: resume import (PDF/DOCX → structured profile via AI extraction) only runs *after*
the key exists, so extraction is billed to the user, never to Karan. Always a review/edit step
before accepting AI-extracted data as ground truth — never silently trust it. Three profile-entry
paths: upload existing resume, start from scratch, paste raw text. Skill-confidence inference
(if kept) is deterministic keyword/substring matching against experience/project text, not an
LLM call — cut specifically during the original design discussion to keep this phase token-free
on Karan's side.

### Phase 5 — Reliability — not started

ARQ + Redis background job queue so generation survives server restarts — the current in-process
`BackgroundTasks` silently loses jobs on redeploy, which was an acceptable risk for a single user
but becomes a real trust problem once other people depend on it (losing someone's resume
generation on an application deadline is bad). PDFs compiled once at generation time and stored
in Cloudflare R2, served via signed URL — no recompiling on every download (the current
compile-on-request pattern doesn't scale past a handful of users). Per-user concurrency limit
(one active generation at a time) to avoid races.

### Phase 6 — Account lifecycle — not started

Async data export (zip: profile JSON + markdown, all resumes/cover letters as LaTeX + PDF,
application history as CSV/JSON, account metadata) — delivered by email when ready, not
generated synchronously. Account deletion with a 7-day grace period before hard delete, with an
email confirmation. Session list + revoke (per-device, "revoke all others") — standard security
hygiene expected by serious users. Soft-delete + undo specifically on profile sections, since
that's the most irreplaceable data in the product (accidentally deleting years of career history
should be recoverable).

### Phase 7 — Observability + abuse guardrails — not started

Structured JSON logging tagged with `user_id`/`request_id`/`duration_ms` (retrofitting this after
real users exist is much more painful than building it now). Sentry for exception tracking with
user context. Uptime monitoring on `/health` and `/api/health`. Per-user daily generation cap —
protects a user whose leaked API key is being drained through CareerOS, and protects the app's
own infra from runaway load. Anomaly detection on generation velocity — plain request counting,
no AI involved, consistent with the token-cost guardrail.

### Phase 8 — Public launch readiness — not started

Landing page (pre-auth) explicitly states the BYO-key model as a trust feature: "you bring your
own AI key, we never see your generation costs." Decision point: open signup vs. waitlist — a
waitlist buys time to prove Phases 5–7 hold under real concurrent load before it's irreversible.
Terms of Service / Privacy Policy — non-negotiable once the app stores other people's resumes,
job application history, and encrypted API credentials. Separate Clerk **production** instance
(currently still using the free dev instance, which has usage caps and a visible warning banner)
before any real traffic beyond Karan and close friends.

---

## Deliberately out of scope

- Automated job ingestion (Adzuna, Indeed, scraping)
- Email digests
- Scheduled background jobs
- Auto-applying to jobs
- ~~Multi-user support~~ — superseded by the Multi-Tenant Migration above (started 2026-06-30).
  What remains out of scope even under multi-tenancy: chat interfaces, analytics dashboards,
  gamification/usage-streak features, and CareerOS ever paying for another user's AI usage.
