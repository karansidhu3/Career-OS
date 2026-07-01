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

### Phase 2 — AI provider abstraction — ✅ DONE (2026-06-30)

Pure refactor, zero new behavior, zero token cost. `backend/app/services/llm_client.py` defines
`LLMClient` (abstract `call_tool()` — system + messages + a single forced tool, returns parsed
tool input + token usage) and `AnthropicAdapter`, the only implementation, wrapping
`anthropic.AsyncAnthropic` exactly as before. `get_llm_client()` is the construction seam Phase 3
will change to build the adapter from the requesting user's decrypted key instead of
`settings.anthropic_api_key`.

All three call sites in `generation.py` (`_call_compression`, `generate_materials`,
`generate_insights`) now go through `get_llm_client().call_tool(...)` instead of constructing
`anthropic.AsyncAnthropic` directly. Still uses Karan's system key globally — no behavior change.
Verified: full backend test suite (159/160 passing — the 1 failure is a pre-existing, unrelated
LaTeX non-breaking-space test on `main`) plus a live smoke-test call through the new adapter
confirming real tool-call + token-usage parsing still works.

### Phase 3 — Encrypted BYO API key — ✅ DONE (2026-06-30/07-01, local only — not yet deployed)

The phase that actually stops Karan's bill growing with other users' usage. Hard cutover: there
is no shared fallback key anymore — `settings.anthropic_api_key` was removed entirely, and every
generation/insights call requires the requesting user's own stored key or fails with a clear 400.

- New `ai_credentials` table (`backend/app/models/ai_credential.py`, RLS in
  `backend/migrations/009_ai_credentials_rls.sql`): `user_id`, `provider` (default `"anthropic"`),
  `encrypted_key`, `key_version`, `key_hint` (last 4 chars, for UX), `label`, `last_verified_at`.
  Unique on `(user_id, provider)` — adding a key again rotates it (upsert), it doesn't duplicate.
- `backend/app/services/crypto.py` — envelope encryption via `cryptography`'s `Fernet`.
  `encrypt()` uses the current `ENCRYPTION_MASTER_KEY`; `decrypt()` tries it plus any keys in
  `ENCRYPTION_MASTER_KEY_PREVIOUS` (comma-separated) via `MultiFernet`, so rotating the master key
  doesn't break decryption of rows encrypted under the old one.
- `backend/app/routers/credentials.py` — `GET/POST/DELETE /admin/settings/api-key`. POST
  validates the submitted key with one tiny real forced-tool-call to Anthropic (billed to the
  submitter's own key) before encrypting and storing it; on failure returns a specific 400
  (`anthropic.AuthenticationError` → "Invalid API key", etc.) rather than a generic error.
- `backend/app/services/llm_client.py`'s `get_llm_client()` now takes an explicit `api_key`
  argument (no more reading a global settings key) — this is the exact seam Phase 2 built.
  `generate_materials`/`generate_insights`/`_call_compression` in `generation.py` all take an
  `api_key` parameter now and thread it through to the adapter.
- `backend/app/routers/jobs.py` — `generate_job`/`regenerate_job` check for a stored key
  *before* doing anything (fail fast, no half-created job) and return
  `400 "Add your Anthropic API key in Settings before generating."` if missing. Insights
  (an automatic background fetch, not user-initiated) instead fails quietly to the same
  all-`None` shape as "not enough applications yet" rather than surfacing a hard error.
- Frontend: `ApiKeySettings` section on `/profile` (top of page, before Projects — the
  doctrine's minimal-nav principle argued against a new navbar icon for this). Add/rotate/remove
  a key inline, masked input, last-4-hint + verified-date display when a key is stored.
  `frontend/lib/api.ts` gained `CredentialStatus` + `getApiKeyStatus`/`setApiKey`/`deleteApiKey`.

**Verified:** 174/175 backend tests passing (1 pre-existing, unrelated LaTeX failure) including
new `tests/unit/test_crypto.py` (round-trip, non-determinism, key-rotation via `MultiFernet`) and
`tests/integration/test_credentials_api.py` (full CRUD, validation-failure paths, rotation,
never-returns-raw-key). A real end-to-end in-process run confirmed: adding a key stores it
encrypted and retrievable, generation through the real per-user-key path succeeds (Anthropic call
mocked — Phase 2 already proved the real adapter works; this phase's own logic is the encrypt/
store/decrypt/gate plumbing), a user with no key gets a clear 400, and the local DB was verified
byte-for-byte unchanged (35 real jobs, 0 leftover test credentials) after the run. Frontend
verified via a clean `next build` + `tsc --noEmit` (the interactive browser preview hit an
unrelated environment/tooling issue in this session and couldn't be used for visual confirmation).
`frontend/app/page.tsx` has a pre-existing, unrelated hydration-mismatch warning around the
insights `AnimatePresence` block — not touched by this phase, worth a separate fix.

### Phase 4 — Onboarding + profile import — ✅ DONE (2026-07-01, local only — not yet deployed)

Enforced order via the home page's own state machine, not a separate route: `app/page.tsx` gained
`checking` → `needs-key` → `needs-profile` → `idle` gate states, checked once on mount
(`GET /admin/settings/api-key` then `GET /admin/profile`). A returning user with both already
falls straight through to `idle`; a brand new signup cannot reach the core loop until both exist.
Any network failure during the check fails open to `idle` (consistent with this file's existing
fail-open patterns for non-critical fetches) rather than hard-locking a returning user out on a
hiccup.

- **`needs-key`**: renders `ApiKeySettings` (extracted from `/profile` into
  `components/ApiKeySettings.tsx` so both surfaces share one implementation) with an `onSaved`
  callback that re-checks the profile and advances to `needs-profile` or `idle`.
- **`needs-profile`**: renders `components/ProfileSetupGate.tsx` — the three entry paths from the
  spec: upload a resume (PDF/DOCX), paste resume text, or start from scratch (a minimal
  name+email form; the rest is added later via `/profile` at their own pace — this is also what
  finally makes personal-info *creation* possible from the UI at all, which nothing did before).
- Resume import: `backend/app/services/resume_import.py` — `extract_text_from_pdf`/
  `extract_text_from_docx` (new `python-docx`/`python-multipart` deps) feed raw text into one
  forced tool-call via the Phase 2/3 `LLMClient` seam, billed to the *user's own* key (the
  Phase 3 gate applies here too — `POST /admin/profile/import` 400s without a stored key).
  Returns a structured draft; **never writes to the database**.
- Review/edit step is real, not decorative: `ProfileSetupGate`'s review stage renders every
  extracted education/experience/project/skill row as an editable, removable card. Nothing is
  persisted until the user hits "Looks good — save my profile," which then calls the *existing*
  per-item CRUD endpoints (`POST /admin/profile/education` — added a `createEducation` frontend
  method since one never existed; education previously had no create UI at all).
- Skill-confidence inference (the "if kept" note in the original spec) was **not built** — it was
  explicitly optional and nothing in this phase's actual deliverables depended on it.

**Verified:** 185/186 backend tests (1 pre-existing, unrelated LaTeX failure) including new
`tests/unit/test_resume_import.py` and `tests/integration/test_profile_import_api.py` (PDF/DOCX
text extraction, AI-extraction reshaping, the import endpoint's key gate, and — importantly — a
dedicated test asserting the import endpoint writes nothing to the profile tables). A real
in-process run through a throwaway JIT-provisioned account (never Karan's) walked the entire
sequence for real: no key → add key → no profile → import (paste text, AI call mocked) → draft
returned but nothing written → save via CRUD → profile now populated — 19/19 checks passed, and
the real local DB was confirmed byte-for-byte unchanged afterward. Frontend verified via clean
`next build` + `tsc --noEmit`; the interactive browser preview hit the same unrelated
environment/tooling issue as Phase 3 (stuck tab, can't reach `localhost`) and couldn't be used —
worth investigating separately.

### Phase 5 — Reliability — ✅ DONE and deployed to Railway (2026-07-01)

Built and verified locally first; Karan then explicitly chose to deploy the worker + Redis to
Railway despite being on the trial plan with ~$1.42 credit left (flagged the risk, he said to
proceed anyway). Cloudflare R2 itself is still deferred — no Cloudflare account access exists to
provision a bucket — but the storage *seam* is built now, backed by local filesystem, so
swapping in R2 later is a config change, not a rewrite.

**Production deployment**: new Redis service (Railway's own template) and a new Worker service
(same repo, root `/backend`, custom start command `arq app.worker.WorkerSettings`). The Worker
needed its own `backend/railway.worker.toml` — sharing Backend's `railway.toml` meant Railway
tried to healthcheck `/health` against a service with no HTTP server at all, failing every
deploy. All cross-service config (`REDIS_URL`, `ENCRYPTION_MASTER_KEY`, `DATABASE_URL`,
`APP_DATABASE_URL`) uses Railway variable references (`${{Backend.X}}`, `${{Redis.REDIS_URL}}`)
rather than Railway's auto-suggested values — it suggested a freshly-random
`ENCRYPTION_MASTER_KEY` for the worker that would have silently broken decryption. Verified live
via deploy logs: Backend starts clean with a working healthcheck (proves the ARQ pool connected
to real Redis without crashing); Worker logs show `Starting worker for 1 functions:
run_generation_job` with a real Redis connection — matching local verification exactly.

- **ARQ + Redis job queue**: `backend/app/worker.py` — `run_generation_job` is now the only place
  generation actually runs, in a completely separate process (`arq app.worker.WorkerSettings`)
  from the API. `generate_job`/`regenerate_job` in `jobs.py` enqueue via `request.app.state.arq_pool`
  (created in `main.py`'s lifespan) instead of FastAPI's `BackgroundTasks`, which silently dropped
  in-flight jobs on redeploy — acceptable risk for one user, a real trust problem once other
  people depend on it. Local Redis runs as a dedicated `careeros-redis` Docker container on port
  6380 (6379 was already occupied locally by an unrelated project's Redis — same collision
  pattern as the Postgres/backend port issues from earlier phases).
- **Per-user concurrency limit**: `generate`/`regenerate` now check for an existing `processing`
  job for that user and return `409` ("already in progress") instead of allowing two concurrent
  generations to race on the same profile/session state.
- **PDF storage seam**: `backend/app/services/pdf_storage.py` — `PDFStorage` interface (mirrors
  the `LLMClient` pattern from Phase 2/3) with `LocalFilesystemStorage` as the only implementation.
  Cache keys are deterministic functions of `job_id` (`resume-{id}.pdf` / `cover-letter-{id}.pdf`),
  so nothing new needed to be stored in the database to track them. Resume and cover letter PDFs
  are compiled once — resume right after a successful generation (in the worker), cover letter on
  first request — and served from cache afterward instead of recompiling LaTeX on every download
  (the old pattern didn't scale past a handful of users). Editing the cover letter invalidates its
  cached PDF so the next download recompiles from the new text rather than serving stale bytes.
  Deleting a job removes its cached PDFs too.

**Verified:** 197/198 backend tests (1 pre-existing, unrelated LaTeX failure) including new
`tests/unit/test_pdf_storage.py`, `tests/integration/test_pdf_caching.py` (compile-once,
cache-hit-on-second-request, invalidate-on-edit, cleanup-on-delete — all with `compile_latex_to_pdf`
mocked), and new `test_jobs_api.py` cases for ARQ enqueue assertions and the 409 concurrency limit.
Beyond mocked tests, ran a **real** end-to-end check: started an actual `arq app.worker.WorkerSettings`
process, enqueued a job directly against real Redis (bypassing the API entirely), and polled
Postgres directly (not through the API) to confirm a completely independent process picked it up,
set the RLS GUC correctly, decrypted the credential, made a real call to Anthropic (which correctly
401'd — a deliberately fake key was used, per the same credential-handling rule from Phase 3: never
inject a real key into an automated script), and wrote `status="failed"` without crashing. That the
job left `"processing"` and reached a real terminal state, driven entirely by a process this script
never touched afterward, is the actual reliability property Phase 5 is about. Confirmed the real
local DB was unchanged (35 jobs, 1 user, 0 stray credentials) after every check.

**Cloudflare R2 — code done, activation pending Karan's account (2026-07-01):**
`app/services/pdf_storage.py` gained `R2Storage` (boto3's S3 client against R2's S3-compatible
endpoint — `https://<account_id>.r2.cloudflarestorage.com`, `region_name="auto"`). `get_pdf_storage()`
now picks `R2Storage` automatically whenever `R2_BUCKET_NAME` is set, otherwise falls back to
`LocalFilesystemStorage` — no caller or deploy-config changes needed either way. New settings:
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`. Verified via 13
new unit tests with boto3 mocked (put/get/delete calls, R2 endpoint construction, cache-miss →
`None` via `ClientError` code `NoSuchKey`, backend auto-selection) — 205/206 full suite passing
(1 pre-existing unrelated failure). Not yet activated: needs Karan to create the Cloudflare
account/bucket/API token himself (no Cloudflare access exists here) and set the four env vars on
Railway directly — per this project's credential-handling rule, third-party API keys always go
in via the user's own hands, never typed into a field by the agent. Until then, the app keeps
using the local-filesystem fallback, which works but doesn't survive a container restart/redeploy.

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
