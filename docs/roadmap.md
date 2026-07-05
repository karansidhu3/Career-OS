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

**Cloudflare R2 — done and live in production (2026-07-01):**
`app/services/pdf_storage.py` gained `R2Storage` (boto3's S3 client against R2's S3-compatible
endpoint — `https://<account_id>.r2.cloudflarestorage.com`, `region_name="auto"`). `get_pdf_storage()`
now picks `R2Storage` automatically whenever `R2_BUCKET_NAME` is set, otherwise falls back to
`LocalFilesystemStorage` — no caller or deploy-config changes needed either way. New settings:
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`. Verified via 13
unit tests with boto3 mocked (put/get/delete calls, R2 endpoint construction, cache-miss →
`None` via `ClientError` code `NoSuchKey`, backend auto-selection) — 205/206 full suite passing
(1 pre-existing unrelated failure). Karan created the Cloudflare account/bucket/API token himself
and pasted the four values into both Backend's Variables directly and Worker's Variables as
`${{Backend.X}}` references (per this project's credential-handling rule, third-party API keys
always go in via the user's own hands, never typed into a field by the agent). Activated and
verified live via Railway's Console on the Worker: a real save/load/delete round trip against
the actual Cloudflare bucket succeeded (`backend: R2Storage`, `roundtrip ok: True`,
`after delete: None`). PDFs now survive container restarts/redeploys and are shared across
replicas — the local-filesystem fallback is no longer in use in production.

### Hosting migration — Railway → Fly.io + Vercel + Neon + Upstash — ✅ DONE (2026-07-01)

Cost-driven: Railway's Hobby plan is a flat $5/mo minimum regardless of usage, and this app's
real usage is closer to $1/mo. Moved to usage-based providers instead: **Fly.io** (backend +
worker, same Dockerfile as Railway), **Vercel** (frontend, native Next.js support, no Dockerfile
needed), **Neon** (Postgres, generous free tier), **Upstash** (Redis, pay-per-request). Cloudflare
R2 was already external to Railway and needed no changes.

- **Neon**: schema + migrations applied via the app's own startup migration runner (pointed at
  Neon instead of Railway) rather than a raw `pg_dump` of schema — Postgres roles are cluster-level
  and don't come across in a normal dump. The restricted `careeros_app` role (mirroring Railway's,
  documented in migration 006) was recreated manually on Neon with a freshly generated password.
  Data itself (1 user, profile, 36 jobs, 1 AI credential) was copied read-only from Railway via
  `pg_dump`-equivalent Python scripting, respecting FK dependency order, toggling
  `NO FORCE ROW LEVEL SECURITY` around the bulk insert (owner is otherwise subject to RLS too, by
  design), then resetting integer PK sequences afterward (same gotcha as the Phase 2 DB-recovery
  incident). Verified with a full RLS round-trip against the real migrated data post-copy: no GUC
  → 0 rows, correct user's GUC → all 36 jobs, wrong GUC → 0 rows.
- **`app.database._normalize()` bug found and fixed**: asyncpg's `connect()` has no `sslmode`
  kwarg — only `ssl` — and raises `TypeError` if `sslmode` is passed through untranslated. Railway
  never surfaced this because its connection strings omit `sslmode` entirely; Neon's (and most
  other providers') include `?sslmode=require` by default. Fixed with a query-param rewrite in
  `_normalize()`, covered by 5 new unit tests (`tests/unit/test_database_normalize.py`).
- **Fly.io**: `careeros-backend` and `careeros-worker` are separate Fly apps sharing one
  Dockerfile/image via `backend/fly.toml` / `backend/fly.worker.toml` (same split-config pattern
  as Railway's `railway.toml` / `railway.worker.toml`). Both initially deployed at
  `shared-cpu-1x:256mb` and both got OOM-killed under real load — the backend's Tectonic warmup
  compile alone uses ~150MB on top of ~100MB baseline, and the worker hit the same Tectonic cost
  plus Anthropic response handling during an actual generation job. Idle health checks looked fine
  at 256mb in both cases; the OOM only showed up under real work. Bumped both to 512mb, which held
  under a real end-to-end generation (Vercel → Fly backend → ARQ enqueue → Fly worker → Anthropic
  → Tectonic → R2). Fly defaults to provisioning 2 machines per app for HA; both apps were scaled
  down to 1 (`fly scale count 1`) since redundancy isn't worth doubling compute cost here — but
  scaling down while a machine is actively mid-job can destroy the wrong one (it destroyed the
  machine that had just picked up a retry, not an idle one), requiring `fly machine start` on
  whatever was left. Lesson: don't touch machine counts while a job is in flight.
- **Vercel**: frontend deployed with zero Dockerfile changes (Next.js is natively supported).
  `ALLOWED_ORIGINS` on the Fly backend and Clerk's dev-instance config both needed no changes
  beyond the new domain — Clerk dev instances are domain-agnostic as long as the key pair matches.
- **Verified end-to-end for real**: Karan signed in on the new stack himself and confirmed his
  real profile + all 36 jobs were intact, then ran a real generation that initially failed with
  the 256mb OOM (a genuinely useful real-world catch, not just synthetic testing) and succeeded
  cleanly once the worker was bumped to 512mb — resume LaTeX (6.8KB) and cover letter (1.6KB) both
  generated, job status `generated`.
- Railway is paused (all 5 services' active deployments removed) as of 2026-07-01, after Karan
  verified real sign-in and a real generation on the new stack. Config, env vars, GitHub
  connections, and volumes (`postgres-volume`, `redis-volume`) are untouched — any service can be
  brought back with a single "Redeploy" if ever needed. Full cancellation is a separate later step.

### Phase 6 — Account lifecycle — ✅ DONE (2026-07-01)

Four independent sub-features, all shipped: data export → account deletion → session list/revoke
→ soft-delete/undo on profile sections.

**Email carve-out**: `CLAUDE.md`'s "no email integration" rule predates this phase and conflicts
with export/deletion needing to notify the user. Resolved: a minimal `EmailClient` seam
(mirrors `LLMClient`/`PDFStorage`) sends transactional email for exactly two triggers —
export-ready, deletion-confirmation — nothing else. `app/services/email_client.py`: `EmailClient`
ABC, `ResendAdapter` (plain HTTP via `httpx`, already a dependency — no new SDK), `NoOpEmailClient`
fallback when `RESEND_API_KEY` is unset (local dev never needs a real key). 5 unit tests
(`tests/unit/test_email_client.py`).

**Data export — ✅ done (backend + frontend).** `app/models/account_export.py` +
migration 010 (RLS, same `tenant_isolation` pattern as 006/009). `app/services/account_export.py`
builds a zip: profile JSON + markdown, account metadata, application history JSON + CSV, and per-job
resume (LaTeX + PDF) / cover letter (text + PDF) — reads cached PDFs from `PDFStorage` first,
compiles fresh only on a cache miss. Runs on the ARQ worker (`run_export_job` in `app/worker.py`,
mirrors `run_generation_job`'s pattern), stores the zip via the existing `PDFStorage` seam
(`account_export_key()`), emails "your export is ready" on completion. Three endpoints under
`/admin/account/export` (request, poll status, download) with a 409 concurrency guard (one export
at a time, same pattern as generation). 19 new tests total across
`tests/integration/test_account_export.py`, `test_account_api.py`, `test_worker_export_job.py` —
full backend suite 229/230 passing (1 pre-existing unrelated LaTeX failure).

**Caught during testing**: `app.worker.AsyncSessionLocal` is a module-level global bound to
`DATABASE_URL` at import time — not `TEST_DATABASE_URL`. A worker-job test that doesn't rebind it
to the test engine would silently write to the real dev database instead of the test one. Fixed
by monkeypatching `app.worker.AsyncSessionLocal` to the test engine for the duration of those
tests only; verified afterward that the real local dev DB's row counts were unchanged. Worth
remembering for any future test of `run_generation_job` too — it was never covered by an automated
test for the same reason, only a real manual end-to-end check (see Phase 5's notes).

**Account deletion**: `users.scheduled_deletion_at` (migration 011) starts a 7-day grace period.
`POST/GET/DELETE /admin/account/delete` request/check/cancel. Requesting sends the second (and
last) of the two transactional emails this app sends — a deletion-confirmation with the deadline
and how to cancel; cancelling is silent by design (no third email trigger). An hourly ARQ cron job
(`run_account_deletion_sweep`, `WorkerSettings.cron_jobs`) hard-deletes any user past their
deadline via `app/services/account_deletion.hard_delete_user` — purges every RLS-protected
user-scoped table plus cached PDFs/export zips in object storage, then the user row itself.

**Session management**: `app/services/clerk_sessions.py` calls Clerk's Backend API
(`GET/POST .../sessions`, mirrors `_fetch_clerk_email`'s existing pattern) to list and revoke
sessions. `GET /admin/account/sessions`, `POST .../sessions/{id}/revoke`,
`POST .../sessions/revoke-others`. The revoke endpoint fetches the target session first and checks
`session.user_id` matches the caller before revoking — a Clerk session id isn't scoped to this
app, so skipping that check would let one user revoke an arbitrary other user's session by
guessing/sending its id (a real IDOR risk, caught and tested before shipping). A new
`get_current_session_id` dependency in `clerk_auth.py` decodes the `sid` claim a second time
(rather than changing `get_current_user`'s return type everywhere it's used) so the frontend can
mark which session is "this device."

**Soft-delete + undo**: `deleted_at` added to `education`/`experience`/`project`/`skill_category`
(migration 012). DELETE endpoints set it instead of removing the row; list/get/full-profile
endpoints filter it out; a `POST .../restore` endpoint clears it. Update and delete both 404 on an
already-deleted row (can't edit something in the trash without restoring it first). No forced
purge window — restore works indefinitely server-side; the frontend surfaces it as an immediate
"Undo" toast (~6s) after each delete, reusing the exact optimistic-update pattern the delete
handlers already had.

**Frontend**: `components/AccountDeletion.tsx` (danger zone, bottom of `/profile`, typed
"DELETE" confirmation — deliberate friction for a destructive action, not a single click) and
`components/SessionManagement.tsx` (placed with the other account-level settings). The undo toast
lives inline in `app/profile/page.tsx` (`undoToast` state + `performUndo`), shared across the three
sections that already had delete buttons (education never had one — out of scope, not something
this phase added). Verified live against Karan's real account via a real browser (not the embedded
preview tool — see below): sign-in carried over from an earlier session sharing the same Clerk
instance, sessions list showed 3 real devices with correct "This device" detection and live
revoke buttons, the deletion confirmation's typed-gate and cancel path both worked correctly
(never actually confirmed — would have really scheduled deletion on Karan's live account).

**Preview-tool root cause finally identified** (corrects a wrong guess from earlier this phase):
it's not the app's CSP `frame-ancestors` header. Clerk's dev-instance middleware rewrites a
truly-cold first request (no `dev-browser` cookie yet) to a synthetic bootstrap path that 404s;
every request after that correctly redirects. Reproduced deterministically with two back-to-back
`curl -I` calls against a freshly-started server. The embedded preview tool's readiness check is a
single non-retrying probe, so it permanently gets stuck showing "Awaiting server…" the moment it
loses that race — a real browser never notices because a normal page load fires many requests, not
one. Not fixable without weakening Clerk's auth middleware (not worth it for a preview tool) or the
tool adding retry logic (outside this app's control). Also caught along the way: `.claude/launch.json`'s
`careeros-backend` config can't run at all — the preview tool's process sandbox can't even read the
venv (`PermissionError` on `pyvenv.cfg`), stricter than the sandbox this session's own Bash tool runs
under. Backend must be started via Bash for local iteration; only the frontend config works with
`preview_start`.

**Also caught**: the backend dev server used for manual testing was a long-running process from a
prior session with no `--reload`, so the new `/admin/account/{delete,sessions}` routes 404'd until
it was restarted — a reminder to always confirm which process is actually serving a port before
trusting "it's already running" during manual verification.

Full backend suite: 269/270 (1 pre-existing unrelated LaTeX failure). 37 new backend tests across
account deletion (service + API + cron sweep), session management (unit + API with the IDOR test),
and soft-delete (21 parametrized tests across all 4 sections). Frontend: clean `next build` +
`tsc --noEmit`, zero new ESLint issues.

### CI/CD: auto-deploy on push + long-standing NBSP bug + E2E Clerk auth fix — ✅ DONE (2026-07-02)

Nothing had actually been auto-deploying on push — pushes to `main` just sat there until someone
manually ran `flyctl deploy`/relied on Vercel's dashboard. `.github/workflows/test.yml` gained
`deploy-backend`/`deploy-worker` jobs (gated on unit/integration/frontend tests + secret scanning,
deliberately *not* on `e2e` — see below for why) using `superfly/flyctl-actions/setup-flyctl@master`
against per-app-scoped `FLY_API_TOKEN_BACKEND`/`FLY_API_TOKEN_WORKER` secrets. Vercel's own native
GitHub integration turned out to already be connected and just needed its `vercel.json` fixed (see
next paragraph) — no new workflow job needed there.

**Long-standing NBSP bug, found while investigating why "Backend unit tests" had been failing on
every push for a long time**: `_escape_latex()` in `app/routers/jobs.py` had
`.replace(" ", " ")` — a no-op, since both sides of that replace were the exact same non-breaking-
space character, not a regular space. This wasn't just a test artifact: any resume/cover-letter
text containing a real NBSP (e.g. pasted from a Google Doc or a job posting) would have produced
literally invalid/passthrough LaTeX in production. Fixed to `.replace("\xa0", " ")`; full suite
went from red to 270/270 — necessary groundwork, since gating auto-deploy on a permanently-red test
suite would mean deploy never runs at all.

**Vercel deploy failure**: `Project framework is set to "services", but no services are declared.`
Two compounding misconfigurations, both project-level, neither actually in the code: (1)
`frontend/vercel.json` had a stray `experimentalServices` block (auto-generated by an earlier
`vercel link`) using a `framework` field instead of the required `entrypoint` — replaced with a
plain `{"framework": "nextjs"}`. (2) The Vercel *project's* Root Directory setting was `.` (repo
root) instead of `frontend` — so the Git-integration build cloned the whole monorepo, saw both
`backend/` (Python) and `frontend/` (Next.js) at top level, and Vercel's auto-detection concluded
this was a multi-service monorepo, overriding the Framework Preset to "Services" regardless of what
`vercel.json` said. Fixing `vercel.json` alone (verified via a manual `vercel deploy --prod`, which
implicitly uses the current directory as root and so never hit the Root Directory bug) wasn't
enough for the automatic Git-triggered deploys — Karan fixed Root Directory → `frontend` and
Framework Preset → Next.js in the dashboard himself (a third-party project-settings change, not
something this agent does unprompted); confirmed via `vercel ls` showing the next deploy `Ready`.

**E2E Clerk auth — three real, separate bugs, not one**: the E2E suite had never actually caught
anything, for three independent reasons stacked on top of each other, uncovered one layer at a
time only after fixing the layer above it:
1. `e2e/playwright.config.ts`'s `testDir: './e2e'` resolved relative to the config file's own
   directory (`e2e/`), pointing at a nonexistent `e2e/e2e/` — zero tests were ever discovered or
   run, on any prior CI run, ever. Fixed to `testDir: '.'`.
2. CI never set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`/`CLERK_SECRET_KEY` when building/starting the
   frontend, so the server crashed before binding to port 3000 — the `wait-on` step's timeout was
   masking bug #1 the whole time (test discovery never even got a chance to matter). Fixed by
   sourcing both from new `CLERK_E2E_PUBLISHABLE_KEY`/`CLERK_E2E_SECRET_KEY` GitHub secrets
   (reusing the same dev Clerk instance, not a separate CI-only app).
3. Once tests actually ran, sign-in itself silently failed: `clerk.signIn()` with a password
   strategy hit Clerk's **Client Trust** attack-protection feature, which requires a second-factor
   email verification on any password sign-in from an "unrecognized device" — and a fresh
   Playwright browser context always is one. The real API response showed
   `status: "needs_client_trust"` with `created_session_id: null` — the password verified fine,
   but no session was ever created, and `@clerk/testing` v2.2.2's password strategy doesn't handle
   that status, so it silently no-opped instead of throwing. Fixed by switching
   `e2e/fixtures/auth.ts` to Clerk's `emailAddress` (ticket-based) sign-in mode, which bypasses
   Client Trust and MFA by design — and also eliminates the password entirely, so the
   `CLERK_E2E_TEST_PASSWORD` secret and its credential-rotation problem went away completely.

**A fourth bug, found only after auth actually started working and CI still failed differently**:
CI's artifact-upload step targeted `playwright-report/`, which only exists with the `html`
reporter — CI uses `reporter: 'github'`, so that directory never existed and every past E2E failure
had been investigated blind, with zero screenshots or traces. Fixed by uploading `test-results/`
instead (populated regardless of reporter) and adding `screenshot: 'only-on-failure'`. The very
next real failure's screenshot showed the actual authenticated app (not stuck on Clerk's sign-in
page) rendering its `needs-key` onboarding gate instead of the idle textarea — which led to two
more genuine, separate fixes: mocking `e2e/generate.spec.ts`'s previously-unmocked mount-time
`/admin/settings/api-key` and `/admin/profile` calls (tests had been silently depending on the real
backend's real state for the E2E test user, not running hermetically as documented), and a real
(non-test) product bug — `app/page.tsx`'s auto-focus `useEffect` was keyed on `appState.mode`, but
`AnimatePresence mode="wait"` doesn't mount the idle surface (and its textarea) until the outgoing
surface's exit animation finishes, so the effect fired while `textareaRef.current` was still
`null` and silently focused nothing — for real users on every fresh page load, not just tests.
Fixed by moving the focus call to the idle `motion.div`'s `onAnimationComplete`, which only fires
once the element actually exists.

**Verified for real, not just locally**: pushed to `main` and confirmed via `gh run view` that the
E2E job passed in actual GitHub Actions CI (`6 passed`), alongside every other job (unit,
integration, secret-scan, both Fly deploys) — the first time this repository's CI had ever
genuinely exercised the E2E suite end to end. `CLERK_E2E_TEST_PASSWORD` GitHub secret deleted as
cleanup once the password strategy was gone.

### Phase 7 — Observability + abuse guardrails — ✅ DONE, fully live (2026-07-02)

**Structured JSON logging**: `app/logging_config.py`'s `JsonFormatter` replaces the root logger's
handler at import time (`configure_logging()`, called at the top of `main.py` before anything else
logs) — every log line from this app's own loggers is now one JSON object (`level`, `logger`,
`message`, plus any `extra={...}` fields), not free-text. A new `@app.middleware("http")` in
`main.py` logs exactly one line per request via a dedicated `access` logger: `request_id` (a fresh
uuid4, also echoed back as an `X-Request-Id` response header for correlating a user's bug report to
a log line), `user_id` (populated by `app.clerk_auth.get_current_user` onto `request.state.user_id`
once auth resolves — `null` for unauthenticated/failed-auth requests, which is itself useful
signal), `method`, `path`, `status_code`, `duration_ms`. Registered after `CORSMiddleware` so it
wraps outermost and captures the true final status and full duration. Uvicorn's own
startup/access logs are untouched (separate loggers with their own handlers) — this only affects
the app's own log statements, which is what actually needs to be searchable once other people's
requests are mixed in. Verified live: `/health` produces a `200` JSON line with `user_id: null`;
an unauthenticated `/admin/jobs` request produces a `401` line, also structured, not just an
unhandled-exception trace.

**Sentry**: `app/services/error_tracking.py` — not a per-call adapter like `LLMClient`/
`PDFStorage`/`EmailClient` (Sentry's SDK is a global capture hook installed once, not something
invoked per-operation), but the same "no-op when unconfigured" idiom applies throughout:
`init_error_tracking()` (called at import time in `main.py`, right after `configure_logging()`)
and `set_user_context()` (called from `get_current_user`, tagging the rest of that request's scope
with the local `user_id` so any later exception is attributed to a user in the Sentry UI) are both
complete no-ops whenever `SENTRY_DSN` is unset — local dev never talks to Sentry, never needs a
DSN. `traces_sample_rate=0.0` (error tracking only, no perf tracing — deliberate cost control) and
`send_default_pii=False`, plus a `before_send` hook that strips `Authorization`/`Cookie` headers
from any captured event as defense in depth beyond the SDK's own PII heuristics — this app's
requests can carry a Clerk bearer token, and decrypted Anthropic keys pass through request
handling, so scrubbing auth headers from crash reports is cheap insurance. **Live in production**:
Karan created a Sentry project and set `SENTRY_DSN` as a Fly secret on both `careeros-backend` and
`careeros-worker`; confirmed via each app's own startup logs switching from `"SENTRY_DSN not set —
error tracking disabled"` to `"Sentry error tracking enabled"`. This also surfaced a real gap —
see `app/worker.py`'s fix below, in the same section — the worker runs as its own process and
never imported `app.main`, so it had never actually initialized Sentry at all despite being the
most exception-prone code in the app.

**Per-user daily generation cap**: counted in Redis (`daily_gen_count:{user_id}`, 24h TTL) via the
existing ARQ pool connection — `ArqRedis` subclasses `redis.asyncio.Redis`, so plain `get`/`incr`/
`expire` work directly on `request.app.state.arq_pool` with no new Redis client or DB column
needed. A rolling 24h window, not calendar-day, so it can't be reset by waiting for midnight UTC.
Deliberately *not* counted via `Job` row creation — `regenerate` reuses an existing row rather than
creating a new one, so counting rows would have undercounted actual Anthropic calls and let
`regenerate` bypass the cap entirely. `generate_job`/`regenerate_job` in `app/routers/jobs.py` both
check `_daily_generation_count()` right after the existing Phase 5 concurrency check and return
`429` with the limit in the message if reached; the counter only increments (`_record_generation()`)
after a generation attempt has passed every other gate and actually been enqueued, so a request
rejected by the concurrency/API-key/cap checks doesn't consume a slot it never used.
`DAILY_GENERATION_LIMIT` (default 20) is a new setting.

**Anomaly detection on generation velocity**: plain request counting, no AI, per the roadmap's own
constraint — a second Redis counter (`gen_velocity:{user_id}`, 10-minute TTL) incremented in the
same `_record_generation()` call. Logs one structured `WARNING` (`anomaly: "generation_velocity"`)
the moment the counter first *crosses* `VELOCITY_ANOMALY_THRESHOLD` (default 5) — checked with `==`
against the post-increment count, not `>=`, so it fires exactly once per 10-minute window rather
than spamming a warning on every request after the threshold. Detection only; it never blocks the
request — `DAILY_GENERATION_LIMIT` is the actual hard limit. This is aimed at the same threat as
the daily cap (a leaked API key being drained) but surfaces it faster, before a full day's quota is
burned.

**Uptime monitoring**: both target endpoints already existed — `GET /health` on the Fly backend
(already wired into `fly.toml`'s `[[http_service.checks]]`) and `GET /api/health` on the Vercel
frontend (a dedicated Next.js route, not proxied through the generic `/api/[...path]` backend-proxy
— see Phase 1's incident #2 for why it has to be separate). Karan set up UptimeRobot against both,
which immediately surfaced two real, separate production bugs neither of the above had ever caught:

1. **Backend `/health` rejected HEAD requests (405)** — UptimeRobot defaults to `HEAD`, not `GET`,
   to save bandwidth. FastAPI/Starlette doesn't auto-add HEAD support for a route registered with
   only `@app.get`. Fixed by stacking `@app.head("/health")` alongside it. The integration test
   suite's `_test_app` (`tests/integration/conftest.py`) is a deliberately separate, minimal
   FastAPI app from `app.main.app` — it had its own hand-duplicated `/health` route with the same
   gap, which would have masked this regressing again; fixed there too.
2. **Vercel Deployment Protection ("Vercel Authentication") was blocking all unauthenticated
   access to the frontend in production** — not just UptimeRobot, *any* real user without a login
   to Karan's Vercel account. `careeros-frontend`'s project settings had it enabled with no custom
   domain configured, so every URL (including the actual production aliases) redirected to
   `vercel.com/sso-api`. This had been true since the Fly/Vercel migration and nothing had
   surfaced it — Karan's own browser always carried a valid Vercel session, so he never saw the
   wall himself. Fixed by disabling it in Vercel's dashboard (Settings → Deployment Protection);
   confirmed via `curl` returning `200` instead of a `302`. Karan plans to re-enable it scoped to
   preview deployments only once a custom domain is set up (Vercel Authentication only gates the
   `*.vercel.app` URLs, not a custom domain).

Both monitors are now active against endpoints that actually return `200`.

**Verified**: full backend suite 290/290 (162 unit + 128 integration, zero pre-existing failures
remaining — the long-standing NBSP LaTeX failure was fixed earlier, see the CI/CD section above).
20 new tests: `tests/unit/test_logging_config.py` (JSON formatting, extra-field surfacing,
non-JSON-native value coercion via `default=str`), `tests/unit/test_error_tracking.py` (no-op vs.
configured branches for both `init_error_tracking`/`set_user_context`, the PII-scrubbing helper),
`tests/integration/test_generation_guardrails.py` (daily cap allow/reject/exceeded, cap rejection
leaves no stray job row and never enqueues, regenerate respects the same cap, velocity warning
fires exactly at threshold and not before/after). Along the way, found and fixed a real gap in the
shared `arq_pool_mock` test fixture (`tests/integration/conftest.py`): `Mock.reset_mock()` does not
clear `return_value`/`side_effect` by default, so a test configuring `arq_pool_mock.get`/`.incr`
(as these new guardrail tests are the first to do) would silently leak that configuration into
every later test in the same run — fixed with `reset_mock(return_value=True, side_effect=True)`.
Also verified live against the real local dev server (restarted to pick up the new code, per the
Phase 6 lesson about stale non-`--reload` processes): real JSON log lines for both a `200` and a
`401` request, correct `X-Request-Id` response header, `user_id: null` on unauthenticated paths.

**Gap found and fixed the same day**: `app/worker.py` runs as its own process
(`arq app.worker.WorkerSettings`) and never imports `app.main` — so `configure_logging()`/
`init_error_tracking()`, both wired only in `main.py`, would never have run in the worker at all.
That's arguably where they matter *most*: Anthropic calls, LaTeX compilation, and the export/
deletion sweeps are the most exception-prone code in the app, and once `SENTRY_DSN` is set, worker
exceptions would have silently never reached Sentry while API exceptions did. Fixed with an ARQ
`on_startup` hook (`_on_startup`, wired via `WorkerSettings.on_startup`) that calls both, plus
`set_user_context()` calls alongside each of the worker's three existing RLS-GUC `set_config` calls
(`run_generation_job`, `run_export_job`, the deletion sweep loop) so worker exceptions are also
attributed to a user in Sentry, matching the API's behavior. 2 new unit tests
(`tests/unit/test_worker_startup.py`); full suite 292/292 (164 unit + 128 integration).

**Final state, after the uptime-monitoring bugs above were fixed**: full backend suite 293/293
(164 unit + 129 integration — 1 more integration test than the previous count, covering `/health`'s
HEAD support). Both Fly apps confirmed live with `"Sentry error tracking enabled"` in their
startup logs; both health endpoints return `200` for real GET and HEAD requests in production;
Vercel Deployment Protection confirmed disabled via `curl` no longer redirecting to
`vercel.com/sso-api`.

### Phase 8 — Public launch readiness — in progress (started 2026-07-02)

Karan chose **waitlist over open signup** — buys time to prove Phases 5–7's guardrails hold under
real concurrent load before opening the door is irreversible. Not blocking on a custom domain
(none yet; ~$10–15/year whenever he gets one) — Clerk's production instance and everything else
below is being built against the current Vercel/Fly URLs, since none of it requires re-doing when
a domain is added later.

**Waitlist landing page — ✅ done.** `/` is now a public route (`proxy.ts`'s `isPublicRoute`) —
`app/page.tsx` calls Clerk's `useUser()` (after every other hook, per Rules of Hooks — hooks can't
be conditional) and renders `components/LandingPage.tsx` instead of the core loop whenever
`isSignedIn` is false. The landing page leads with the BYO-key model as a trust feature ("you
bring your own AI key — CareerOS never sees or pays for your usage"), not a footnote, plus an email
capture form and a "sign in" link for anyone already invited.

Backend: `app/models/waitlist.py`'s `WaitlistEntry` (email, `created_at`, `invited_at` — the last
nullable, set manually by Karan when he invites someone; no automated invite-email flow was built,
consistent with CLAUDE.md's "no email digests/marketing" carve-out — this stays a plain signup
list, not a mailing list). `app/routers/waitlist.py` — `POST /waitlist`, deliberately **not** under
`/admin` (ADR-006) since there's no authenticated user yet at this point in the funnel; rate-limited
5/hour by IP (a public, unauthenticated endpoint that writes to the database is a spam surface with
no other gate); duplicate emails return the same "joined" response rather than revealing whether an
address is already on the list.

Frontend plumbing: a new dedicated `frontend/app/api/waitlist/route.ts`, mirroring the existing
`app/api/health/route.ts` pattern — deliberately **not** routed through the generic
`app/api/[...path]/route.ts` proxy, which calls Clerk's `auth()`/`getToken()` and would 401 before
ever reaching the backend, since a pre-auth visitor has no Clerk session at all. Also added to
`proxy.ts`'s public routes alongside `/`. The CSP's `connect-src 'self'` (Phase 1) meant the
browser could never call the Fly backend directly even if we wanted to — this dedicated route is a
server-to-server passthrough instead, exactly like the health-check route already was.

**Verified for real**: this session's embedded browser preview tool could not complete navigation
to the app at all (`net::ERR_ABORTED` on every attempt, including retries and reloads, even though
`curl` against the same URL succeeded — see the updated
`feedback_clerk_coldstart_preview_tool.md` memory for the full investigation). Fell back to two
solid alternatives instead: a new React Testing Library component test suite
(`frontend/tests/unit/LandingPage.test.tsx` — this project's first `.tsx` test file) covering the
trust-message copy, email submission, success/error states, and the disabled-while-submitting
button; and three new **real-browser** Playwright E2E tests (`e2e/landing.spec.ts`, run locally
against real dev servers, not mocked) confirming a signed-out visit to `/` shows the waitlist form
with zero textareas reachable (the actual security property that matters — a signed-out visitor
genuinely cannot reach the core app), that joining the waitlist shows a confirmation, and that the
sign-in link navigates correctly. The full existing signed-in E2E suite (`generate.spec.ts`, 6
tests) was re-run alongside these and confirmed unaffected — 9/9 E2E tests total. Backend: 297/297
(164 unit + 133 integration, 8 new tests for the waitlist endpoint: creation, invalid-email
rejection, duplicate-email idempotency, and the deliberate no-auth-required requirement).

**Terms of Service / Privacy Policy — ✅ drafted, not legally reviewed.** `frontend/app/terms/page.tsx`
and `frontend/app/privacy/page.tsx`, both public routes (`proxy.ts`), sharing a
`components/LegalPageShell.tsx` wrapper. Both open with an explicit, visible disclaimer that this
is an AI-drafted starting point, not reviewed by a lawyer, and shouldn't be relied on as final
before real public launch — that disclaimer is load-bearing, not boilerplate CYA. Content reflects
this app's actual behavior rather than generic template text: the BYO-key billing model and who's
responsible for Anthropic costs, the real list of third-party processors (Clerk, Anthropic, Neon,
Cloudflare R2, Upstash, Fly/Vercel, Resend scoped to its two transactional triggers, Sentry with
PII-scrubbing called out specifically), the actual data export/7-day-grace-period deletion flow
from Phase 6, and the actual daily-cap/velocity-anomaly guardrails from Phase 7 described accurately
(plain request counting, no AI, never inspects generation content). Linked from the waitlist
landing page's footer. Verified via 3 new real-browser E2E tests
(`e2e/legal-pages.spec.ts` — both pages reachable while signed out, both links from the landing
page work) — full E2E suite now 12/12 (6 existing signed-in + 3 landing + 3 legal pages).

### Security hardening — full pre-launch audit + top 7 remediations — ✅ DONE (2026-07-03)

Ran a from-scratch, no-prior-findings-assumed security audit (5 parallel research passes across
auth/IDOR, secrets/crypto/AI-provider isolation, API/upload/subprocess safety, database/RLS/infra,
and frontend/XSS/CSP) covering every layer through OWASP Top 10, trust-boundary analysis, and a
scored assessment per category. Zero Critical findings; RLS, authorization, and AI-key isolation
were all independently confirmed sound. One High finding (below) and several Medium findings came
back — one of which (an "IP spoofing" claim) turned out to be wrong on independent verification
against `slowapi`'s actual source, and was corrected before acting on it rather than fixed as
reported. Implemented the top 7 remediations:

1. **Resume upload resource-exhaustion guard (the one High finding)** — `backend/app/routers/profile.py`
   now caps uploads at 5MB, and `backend/app/services/resume_import.py` reads a DOCX's central
   directory (via `zipfile.infolist()`, which doesn't decompress anything) to reject a declared
   uncompressed size over 50MB *before* `python-docx` ever decompresses it — a classic zip bomb is
   tiny on the wire and huge decompressed, so the upload-size cap alone doesn't catch it. This
   mattered more here than in a typical app: backend and worker each run on a single
   `shared-cpu-1x:512mb` Fly machine (`fly scale count 1`, deliberate per ADR-010, and this exact
   machine already OOM'd once under real load during Phase 5) — one bad upload could take the app
   down for every user, not just the uploader. Also added a global `MAX_REQUEST_BODY_BYTES` (10MB)
   middleware in `main.py`, checked via `Content-Length` before the body is ever read, as
   defense-in-depth beyond this one endpoint.
2. **Rate-limit key fixed to use Fly's real client IP** — new `backend/app/rate_limit.py` replaces
   4 duplicated copies of `_limiter_key` (main.py, jobs.py, credentials.py, profile.py) plus
   waitlist.py's separate `get_remote_address` usage. The actual bug: `slowapi`'s own
   `get_remote_address()` reads only `request.client.host`, and uvicorn is started without
   `--proxy-headers` — so behind Fly's edge, every unauthenticated request (the waitlist, or any
   auth-less hit to a protected endpoint) was likely bucketed by Fly's internal proxy address
   rather than the real visitor, making the waitlist's "5/hour by IP" limit unreliable with zero
   attacker effort required. Now keyed off Fly's own `Fly-Client-IP` header, set by Fly's edge and
   not forgeable by a client outside Fly's network.
3. **`azp` origin check now fails closed** — `backend/app/clerk_auth.py`'s defense-in-depth check
   (rejects a token minted for a different frontend under the same Clerk instance) previously
   no-opped entirely if `ALLOWED_ORIGINS` was ever empty. One `allowed and` removed from the
   condition — if `azp` is present, it's always checked, so a token with an azp claim is rejected
   rather than silently passed if origins were ever accidentally misconfigured to empty.
4. **`ENCRYPTION_MASTER_KEY` validated at boot, not lazily** — new `crypto.validate_master_keys()`
   eagerly constructs a `Fernet` instance for the current key and any previous (rotation) keys,
   called from both `main.py`'s lifespan and `worker.py`'s `_on_startup`. A malformed/missing key
   previously passed a clean startup and healthcheck, surfacing only as a confusing 500 for
   whoever was the first real user to touch credentials.
5. **`ON DELETE CASCADE` on every `user_id` foreign key** — migration 013 (idempotent
   drop-then-recreate, matching every other migration here) plus the matching model change on all
   8 FKs. `hard_delete_user()` already deletes every user-scoped row correctly, in the right order,
   in one transaction — this is defense-in-depth for the case where a user row is ever deleted
   through some other path (a future admin script, a manual `psql` session).
6. **Sentry scrubbing extended beyond headers** — `_scrub_pii` already stripped
   `Authorization`/`Cookie` headers; now also regex-redacts `sk-ant-...`-shaped substrings from
   exception messages, log entries, and the top-level event message, since header-stripping alone
   doesn't cover a key that ends up embedded in an exception's own text rather than a header.
7. **Resume LaTeX compile failures now fail correctly instead of silently** — real gap found while
   scoping this fix: the resume body is AI-generated LaTeX that (unlike this app's own cover-letter
   template) isn't re-escaped after Claude writes it, so a compile failure is a real possibility.
   `_compress_if_needed` in `generation.py` had two bugs: if the *first* compile ever failed, it
   silently returned the broken LaTeX as if generation had succeeded (the job would show
   "generated" but PDF downloads would always fail); if a *later* compile — after a compression
   pass — failed, it returned that broken result instead of falling back to the pre-compression
   version that had already proven it compiles. Fixed both: a first-compile failure now propagates
   so `run_generation_job` correctly marks the job "failed" instead of storing unusable LaTeX, and
   a later failure now returns the last version actually proven to compile.

**Scope note on severity**: traced the actual exploitability of the LaTeX-escaping gap (#7) before
treating it as more than a reliability fix — Tectonic has no `--shell-escape` (no code execution
path), each compile runs in a fresh per-request sandboxed temp directory with a restricted
environment, and any injection would only affect the *acting user's own* PDF, never another user's
data. So the real-world security impact was low even before the fix; the fix is primarily a
reliability improvement (a job that will only ever produce a broken PDF should say so, not claim
success), not a vulnerability closure.

**Verified**: full backend suite 319/319 (186 unit + 133 integration — 26 new tests across
`test_rate_limit.py`, new `azp`/crypto/error-tracking/resume-import cases, and a new
`test_compress_if_needed.py` exercising both fixed failure modes with mocked compilation). Full
local E2E suite re-run against real dev servers after all 7 changes — 12/12 passing, confirming
real Clerk sign-in still works correctly with the `azp` fail-closed change and that rate limiting
doesn't block normal authenticated traffic. Migration 013 applied and confirmed live against the
real local dev DB (`confdeltype = 'c'` on all 8 FKs). Global body-size middleware confirmed live
(`413` on an 11MB body, `422` — correctly past the middleware — on a 6MB body that only fails
Pydantic validation).

**Remaining for Phase 8**:
- Actual legal review of the ToS/Privacy drafts above before public launch.
- Production Clerk instance — still on the free dev instance (usage caps, visible warning banner
  in the sign-in UI). Not yet started.
- Remaining Medium/Low audit findings (redis-backed rate-limit storage, CSP nonce migration,
  backend security headers, dependency pinning) — deferred, tracked in the audit report itself,
  not urgent at current "friends only" scale.

---

### Phase 9 — Design consistency + product architecture restructuring — ✅ DONE (2026-07-03)

Two passes, deliberately kept separate: a visual design-consistency audit first, then a
structural (information architecture / workflow / navigation) review that explicitly ignored
colors, typography, spacing, and animation.

**Design consistency** (all 17 ranked findings from the design audit fixed):
Clerk `<SignIn>`/`<SignUp>` themed via a shared `appearance` config (previously rendered with
zero customization — stock Clerk styling next to a fully custom-designed app); duplicated
input/button styling across 5 files consolidated into `components/FormControls.tsx`; the
result-view (`AnalysisSection`, `LatexSection`, `Divider`, `SelectedProjectsBar`,
`ResumePreview`, `ResumeDownloadOverlay`) extracted into `components/ResultSections.tsx` so `/`
and `/jobs/[id]` render the same components instead of two independently-drifting copies; plus
a batch of smaller fixes (missing hover/focus states, inconsistent disabled opacity and icon
sizing, a hardcoded status color, dead CSS tokens, mismatched springs, missing empty states, an
inconsistent section divider on `/profile`).

**Product architecture** (see ADR-011 in CLAUDE.md for full rationale): `/profile` split into
`/profile` ("Background" — career content) and `/account` (billing key, data export, deletion);
the custom `SessionManagement` component and its backend endpoints
(`app/services/clerk_sessions.py`, `GET/POST /admin/account/sessions*`) removed in favor of
Clerk's own native session UI (`<UserButton>` → "Manage account"); `HistoryDrawer.tsx` deleted
(fully built, imported nowhere — superseded by the Command Palette at some earlier point and
never removed); the idle home screen's own "Recent" list removed in favor of the Command
Palette, which already did the same job; the generation flow's URL is now shallow-synced to
`/jobs/{id}` via `window.history.replaceState` the moment a job starts, fixing a real gap where
refreshing during or immediately after generation silently lost the result back to a blank idle
screen even though the job was fully persisted server-side; onboarding reordered to profile
setup before the API key ask, so a new signup's first action is free/low-friction rather than
handing over a billing credential before seeing any value.

**Verified**: `tsc --noEmit` clean, `eslint` clean (no unused/undefined), `vitest` 37/37 passing,
`next build` succeeds with `/account` as a new static route, backend unit suite 182/182 passing
after the session-management removal (integration tests require `TEST_DATABASE_URL`, not set in
this environment — confirmed they at least import/collect cleanly, i.e. no broken references).

---

### Resume/cover-letter download + preview unification — ✅ DONE (2026-07-05)

The result view had two separate resume-download affordances (one inside the PDF preview
overlay, one below it) and a cover letter that was a plain editable textarea with no visual
relationship to the typeset resume sitting next to it — a real inconsistency once both
documents are meant to read as the same product's output. Unified in `frontend/components/
ResultSections.tsx`:

- **One icon-only download button per document** (`DownloadIconButton` — rounded-square,
  spinner → checkmark states) replacing the old labeled-button-plus-overlay pattern for the
  resume, and the plain "download" link for the cover letter.
- **Cover letter now gets the resume's exact treatment**: a real compiled-PDF preview
  (`CoverLetterPreview`, self-fetching) instead of a bare textarea, backed by a new
  `GET /admin/jobs/{id}/cover-letter-preview.pdf` endpoint that mirrors the existing resume
  preview endpoint and reads/writes the same `PDFStorage` cache the download endpoint uses.
  Editing moved into a collapsible panel below the preview rather than being always-visible;
  saving remounts the preview via a changed `key` prop (not an effect-driven state reset,
  which trips `react-hooks/set-state-in-effect`) so the next render recompiles from the edited
  text.
- Both `/` and `/jobs/[id]` share these components — `/jobs/[id]` previously had **no** cover
  letter editing at all and now does.
- `ResumeDownloadOverlay`, listed as one of the components extracted into `ResultSections.tsx`
  during Phase 9's design-consistency pass, is now deleted as dead code — this rework replaced
  it rather than reusing it.
- Fixed a local-dev-only bug along the way: the cover letter preview 404'd because the local
  backend process predated the new route (no `--reload`) and, separately, the local
  `careeros-redis` Docker container had stopped (blocks backend startup via the ARQ pool in
  `main.py`'s lifespan) — both are environment issues, not product bugs, but worth remembering
  per the recurring "confirm which process is actually serving a port" lesson from Phase 6/7.
- Verified the displayed `$X.XXXX generation cost` figure is real Anthropic token telemetry
  (`usage.input_tokens`/`output_tokens`/cache tokens) times the current Sonnet 4.6 pricing
  constants in `Job.cost_usd` — not a placeholder or estimate.

**Cover letter LaTeX header rework** (`_COVER_LETTER_LATEX` in `backend/app/services/
generation.py`): name is now vertically centered inside the shaded header band (via
`\AddToShipoutPictureBG*` + a fixed-height centered `minipage`, independent of document
margins), with the contact/links line pulled tight against the band's bottom edge. Tuned
entirely through real Tectonic compiles + rendered-PDF inspection, not source-only guessing.

Also: the Generate button's keyboard-shortcut hint is now OS-accurate (`⌘↵` on Mac,
`Ctrl ↵` elsewhere, detected client-side via `navigator.platform`) — the underlying handler
already accepted both Cmd and Ctrl, only the displayed glyph was hardcoded to Mac.

**Not verified via full test suite this session** — per standing instruction, routine UI edits
lean on CI to catch regressions instead of a local `tsc`/`vitest`/`pytest` run per change;
verification here was via real LaTeX compiles, `curl` against the new endpoint, and reading the
actual `cost_usd`/token-usage code paths.

---

## Deliberately out of scope

- Automated job ingestion (Adzuna, Indeed, scraping)
- Email digests
- Scheduled background jobs
- Auto-applying to jobs
- ~~Multi-user support~~ — superseded by the Multi-Tenant Migration above (started 2026-06-30).
  What remains out of scope even under multi-tenancy: chat interfaces, analytics dashboards,
  gamification/usage-streak features, and CareerOS ever paying for another user's AI usage.
