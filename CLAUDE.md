# CareerOS

---

## What this product is

CareerOS is a personalized application generation engine.

One workflow: paste job description → generate tailored resume + cover letter → download → repeat.

Not a CRM. Not a dashboard. Not a workspace. A focused utility that compresses the most tedious part of job searching into ~20 seconds of active work.

---

## Product moat

1. **Persistent profile context** — Profile stored and grows over time. Never re-explain your background.
2. **Automatic project selection** — System reads the JD and selects which projects to emphasize. User never thinks about this.
3. **Compilable LaTeX output** — Always the correct template, always compiles with Tectonic.
4. **ATS-optimized pipeline** — Keyword mirroring, bullet quality, output consistency built into the system prompt.
5. **Workflow compression** — 12+ manual steps in ChatGPT → 1 paste + 1 keypress.

---

## Core loop (the only loop that matters)

```
Open app → textarea focused → paste JD → Cmd+Enter → ~20s → result inline → download → New application → repeat
```

No navigation. No page transitions. One surface.

---

## What NOT to build

- Chat interface — destroys "no prompt engineering" moat
- Job scraping / sourcing — wrong product
- Analytics or career dashboards — CRM thinking. **Onboarding exception** (decided
  2026-07-09, see ADR-016): a one-time, pre-core-loop setup gate for brand-new users is not
  "the dashboard" — it is a prerequisite screen that exists only until a profile meets the
  minimum bar, then disappears for good. It must not persist, resurface, or grow status/analytics
  features of its own once the user is past it.
- Multi-user features — destroys personal context moat. Superseded by ADR-013 (BYO-key
  multi-tenancy, Phase 3) — the product is now multi-user by design; this line is kept for
  historical context only.
- Email integration for notifications, digests, or marketing — pull-only product. **Exception**
  (decided during Phase 6 planning, 2026-07-01): transactional email for two specific
  security-critical account-lifecycle triggers — data export ready, account deletion
  confirmation — via a minimal `EmailClient` seam (mirrors `LLMClient`/`PDFStorage`). Nothing
  beyond those two triggers; no engagement/notification email of any kind.
- Interview scheduler — out of scope
- Gamification or progress metrics — wrong emotional direction. **Onboarding exception**
  (ADR-016): step/completion progress shown only inside the one-time setup gate, never in the
  steady-state product. No streaks, counts, or achievement framing anywhere, including onboarding.
- Status tracking beyond interview/offer — CRM thinking
- Notifications or reminders — pull-only product
- Salary benchmarking — different product
- AI feedback on uploaded resumes — dilutes the paradigm

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12), async |
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS v4, Framer Motion |
| Database | PostgreSQL (SQLAlchemy async), Row-Level Security, hosted on Neon |
| Auth | Clerk (session-JWT, verified against Clerk's JWKS) |
| LLM | Claude API (`claude-sonnet-4-6`), user's own BYO key (see ADR-013) |
| Job queue | ARQ + Redis (Upstash) |
| Object storage | Cloudflare R2 (compiled PDFs) |
| Hosting | Fly.io (backend + worker, Dockerfile-based), Vercel (frontend) |
| Observability | Structured JSON logging, Sentry |

---

## Information architecture

```
PUBLIC (signed out): /, /terms, /privacy
  → `/` renders `components/LandingPage.tsx` instead of the core loop whenever Clerk's
    useUser() reports signed-out (waitlist gate, ADR-014) — email capture + "sign in" link,
    leads with the BYO-key trust model. /terms and /privacy (`LegalPageShell.tsx`) are
    AI-drafted, not legally reviewed, linked from the landing page footer.

PRIMARY SURFACE: / (signed in)
  idle       → textarea focused, JD persisted in sessionStorage and restored on load
               candidacy insights (headline/observed/gap/action) shown after 3+ applications
               setup nudge if profile is empty
               no recent-applications list here — that's /applications' job (see below), kept
               off this screen so it stays a single-action surface
  generating → cycling messages + elapsed timer, no navigation
               URL is shallow-synced to /jobs/{id} the moment the job is created (no visible
               transition) so refresh/bookmark/share land on the real archive page instead of
               losing the job back to a blank idle screen
  result     → strategic analysis (GOOD FIT / GAPS / IMPROVEMENT PLAN)
               selected projects bar (which projects the AI chose — "Emphasized" pills)
               inline PDF preview (iframe, compiled on demand) + status actions
               (Mark applied / Got interview) + one icon-only download button
               (`DownloadIconButton`, shared with cover letter below — see ADR-015)
               cover letter — same treatment as the resume: real compiled PDF preview
               (`/cover-letter-preview.pdf`), its own icon-only download button, editing
               moved into a collapsible panel below the preview instead of a bare textarea
               (`CoverLetterSection`/`CoverLetterPreview` in `ResultSections.tsx`, shared by
               `/` and `/jobs/[id]`) — PATCH still persists edits
               LaTeX source toggle (expandable, copy button)
  error      → message + retry/reset inline

ARCHIVE: /jobs/[id]
  → Deep-link to a specific past result — renders the same shared result-view components as
    the home page's result state (frontend/components/ResultSections.tsx)
  → Single-scroll layout, no tabs
  → This is also where a freshly generated job's URL points once generation starts (see above)

APPLICATIONS: /applications
  → Full history browser
  → Filter tabs (all / generated / applied / interview / offer / skipped)
  → Grouped timeline (Active pinned at top, This week, Earlier)
  → Each row shows gap signal from strategic_note

RESUME: /profile
  → Book icon in navbar ("Resume") — previously titled "Background" with a document/folder
    icon; renamed because a page glyph read as "your generated resumes/applications" (the
    actual output of this product) rather than "the structured data that feeds generation,"
    and "Profile" was considered and rejected since it collides with account identity, which
    lives separately under Settings
  → Career content only — personal info, education, experience, projects, skills,
    cover_letter_voice (how Karan writes, injected into the cover letter prompt)
  → This is content the AI reads, not account administration — deliberately separate from
    Account (below)
  → Rare interaction — configure once, update when new work lands

ACCOUNT: /account
  → Reached via the avatar's dropdown → "Settings" (no standalone navbar icon — removed once
    Settings had a path through the avatar menu, to avoid two navbar routes to the same page)
  → Administrative, not content: Anthropic API key, account data export, account deletion
  → No session/device management UI — see note on UserMenu below
```

Navbar: wordmark left, two icons + a custom avatar menu on the right (Applications, Resume, then
the avatar). No labels beyond tooltips. Amber dot next to the wordmark when any job is in
interview/offer status. Search lives inline on /applications now, not behind a navbar icon or a
command-palette overlay — the Command Palette component was deleted (see ADR-012).

The avatar opens a custom `UserMenu` (name, email, Settings, Sign out) instead of Clerk's stock
`<UserButton>` — its "Manage account" modal exposed a native "Delete account" action that bypassed
this app's own grace-period deletion flow (`components/AccountDeletion.tsx`) entirely, deleting
the Clerk identity directly without cleaning up app data first. Session/device management is
consequently not exposed in-app at all; use the Clerk dashboard if a session ever needs a manual
revoke. See ADR-012.

---

## Visual identity

App is dark-mode-only (ADR-012) — the inverted neutral scale (`--color-neutral-900` through `-50`) does most of the structural work, and accent is a warm off-white, not a chromatic color: `--c-accent: #E8E8E4`. The original "ink" (`#18181B`) accent choice predates the dark-mode-only pivot and no longer appears anywhere in the codebase. Semantic colors (success/warn/danger) are the only chromatic notes, per the global doctrine's fixed palette.

---

## Karan's profile (initial seed — DB is the source of truth)

The DB is the live source of truth. The profile page (`/profile`) is where updates are made.
This section reflects the initial seed state; the actual DB may have newer project descriptions
or updated experience bullets.

### Personal
- Name: Karanveer Sidhu
- Email: karansidhu5550@gmail.com
- Phone: +1 (250) 509-2500
- LinkedIn: linkedin.com/in/karan-sidhu3
- GitHub: github.com/karansidhu3
- Location: Kelowna, BC, Canada (open to remote + Vancouver/BC)

### Education
- University of British Columbia | BSc Computer Science, Minor Data Science | Sep 2022 – Jun 2026

### Target roles
- Entry-level software engineer (full stack, backend, AI/ML engineering)
- Location: Canada (remote preferred, BC in-person okay)

### Experience

**Full Stack Developer — UBC (May–Aug 2025)**
- Built TA matching platform with Next.js, React, Node.js; automated allocation across Science faculty; reduced 120+ hours of manual work per term
- Designed multi-step form workflow with schema-based validation
- Dockerized PostgreSQL schema with many-to-many relationships

**Research Assistant — UBC SIMLAB (May–Aug 2024)**
- Built spatial graph models for wildfire spread simulation (terrain, vegetation, powerline networks)
- Implemented graph algorithms for probabilistic fire propagation and infrastructure risk quantification

### Projects

**MarketMind AI** (Dec 2025 – present)
- Tech: Python, FastAPI, Next.js, React, PostgreSQL, Redis, Qdrant, Ollama, Docker
- Persistent investment intelligence platform; multi-agent pipeline ingesting SEC filings daily
- Temporal signal tracking; thesis confidence scoring, company radar, portfolio alignment layer

**Agentic Market Sentiment System** (Dec 2025)
- Tech: Python, Groq AI, YFinance API, DuckDuckGo, FastAPI
- Multi-agent AI system; reduced manual research time by 70%
- Agents for market data, news, sentiment; 100+ structured data points per query

**FDA Cancer Drug–Protein Network Analysis** (Nov 2025)
- Tech: R, igraph, tidyverse
- Bipartite drug–protein network from FDA oncology datasets + BioGRID PPI network
- Centrality and hub analysis for drug sensitivity/resistance pathways

### Skills
- Languages: Python, JavaScript, Java, C++, R
- Frameworks: React, Next.js, Node.js, Express.js, FastAPI, Docker
- Databases: PostgreSQL, MongoDB, MySQL
- Tools: Git, Jupyter, Pandas, NumPy, Matplotlib, TensorFlow, PyTorch

---

## Cover letter format spec

3 paragraphs. No filler. Must read like a person wrote it.

**Para 1:** What specifically caught attention about this role (from JD). One concrete sentence about fit. Don't open with "I".
**Para 2:** The most relevant project, described technically. Name it. Name the specific technical problem and architecture decision. Results where possible. Specific enough for a hiring manager to ask a follow-up.
**Para 3:** Short close. Available June 2026. Open to discussion.

Voice is driven by `cover_letter_voice` in the profile — if set, apply it to every sentence. Default: direct, technical, first-person, confident without being inflated.

Tone: direct, confident. No em dashes. No "leveraging." No AI-sounding language. No banned phrases (see system prompt in `generation.py` for the full list).

---

## Resume generation rules

- One page, always
- Never include Old Navy / Sales Associate role
- Never fabricate experience or skills not in profile
- Heading and education: identical every time
- ATS keyword mirroring: extract exact terms from JD, use verbatim
- Bullet structure: specific technical noun first → number or concrete scale → what changed/replaced
- Max 3 bullets per experience role (only if 3 strong bullets exist — two sharp beats three with filler)
- Exactly 2 bullets per project
- 2–4 projects total (selected by AI based on JD; committed to `selected_projects` before writing)
- Numbers from source description are mandatory — a number in the source that's absent from the bullet is a generation failure
- See `_SYSTEM_PROMPT_BODY` in `backend/app/services/generation.py` for the full prompt

---

## Resume LaTeX template

The authoritative template is `LATEX_TEMPLATE` in `backend/app/services/generation.py`.

---

## Architecture decisions

**ADR-001** — Claude API (cloud), model `claude-sonnet-4-6`. Quality is non-negotiable for resume generation. Never change the model without updating this.

**ADR-002** — No automated job ingestion. Manual JD paste only.

**ADR-003** — Fly.io for backend + worker (Dockerfile-based build, same image for both — worker overrides the start command). Tectonic binary installed via curl during image build for server-side LaTeX→PDF compilation. Frontend on Vercel, Postgres on Neon, Redis on Upstash. Migrated off Railway (2026-07-01) — Railway's Hobby plan charges a flat $5/mo minimum regardless of usage; this app's real usage is closer to $1/mo, and Fly/Vercel/Neon/Upstash's usage-based billing (plus generous free tiers on Neon/Upstash) tracks actual cost instead. See ADR-010.

**ADR-004** — Background/async generation. POST `/admin/jobs/generate` returns immediately (status="processing"); actual generation runs in a separate ARQ worker process (see ADR-010 / Phase 5), not inline in the request. Frontend polls every 2.5s until done. Sidesteps HTTP proxy timeouts on generation requests that take longer than a typical request/response cycle.

**ADR-005** — Inline generation flow. The home page (/) handles all states: idle → generating → result. No route change during the core loop. `/jobs/[id]` is the archive deep-link viewer only.

**ADR-006** — All authenticated routes are under `/admin/` prefix. Auth is a Clerk session JWT (`Authorization: Bearer ...`), verified against Clerk's published JWKS in `app/clerk_auth.py`'s `get_current_user` dependency, with JIT user provisioning on first sign-in — this replaced an earlier static `X-API-Key` scheme entirely during the Phase 1 multi-tenant migration (2026-07-01); there is no shared key left to configure. `/waitlist` is a deliberate exception, *not* under `/admin` — it's hit by pre-auth visitors with no Clerk session, rate-limited 5/hour by IP instead. Rate limiting (slowapi) is centralized in `app/rate_limit.py`: 30/hour generate/regenerate, 20/hour insights, keyed off Fly's `Fly-Client-IP` header rather than `request.client.host` (uvicorn runs without `--proxy-headers` behind Fly's edge, so the raw client address is unreliable — found during the pre-launch security audit, see roadmap).

**ADR-007** — Candidacy insights. After 3+ completed applications, `GET /admin/jobs/insights` synthesizes a pattern across all job strategic_notes and returns headline/observed/gap/action. Cached in localStorage for 1 hour on the frontend.

**ADR-008** — Cover letter compiled to PDF server-side using a separate LaTeX template (charter font, gray header band). Plain text cover letter is stored in DB and can be edited before download; PATCH `/admin/jobs/{id}/cover-letter` persists edits.

**ADR-009** — Tectonic package cache warmed at startup. First real PDF request is fast; warmup happens in a background asyncio task so it doesn't block server startup.

**ADR-010** — Migrated hosting from Railway to Fly.io + Vercel + Neon + Upstash (2026-07-01), cost-driven (see ADR-003). Backend and worker are separate Fly apps (`careeros-backend`, `careeros-worker`) sharing one Dockerfile/image via `backend/fly.toml` and `backend/fly.worker.toml` — the worker's config overrides the start command (`arq app.worker.WorkerSettings`) and has no `[http_service]` block, since it has no HTTP server. Both run on `shared-cpu-1x:512mb` — 256mb OOM-killed both the backend (Tectonic's warmup compile alone uses ~150MB on top of ~100MB baseline) and the worker (same Tectonic cost, plus the Anthropic response handling, during a real generation job) under real load, even though idle health checks looked fine at 256mb. Fly defaults to provisioning 2 machines per app (HA); both are intentionally scaled to 1 (`fly scale count 1`) since redundancy isn't worth doubling compute cost for this app's traffic — **be careful when scaling down while a machine is actively processing a job**: `fly scale count` can destroy the machine mid-work rather than the idle one, requiring `fly machine start` on whatever's left. Postgres connection strings from non-Railway providers (Neon included) include `?sslmode=require`, which asyncpg's `connect()` rejects outright (`TypeError: unexpected keyword argument 'sslmode'` — it wants `ssl=` instead); `app.database._normalize()` now rewrites this automatically. The Neon `careeros_app` restricted role (mirroring Railway's, per migration 006) was created manually with a fresh generated password — never reuse a role/credential across providers, and never let a provider's "suggested variables" autofill a security-relevant secret across services (same lesson as Phase 5's Redis setup, this time against Neon's own owner role auto-suggestion habits).

**ADR-011** — Product architecture restructuring (2026-07-03), following a first-principles structure review (independent of visual design — information architecture, workflow, navigation only). Four changes: (1) `/profile` split into `/profile` ("Background" — career content that feeds generation: personal/education/experience/projects/skills/voice) and `/account` (administrative: API key, data export, deletion) — these were previously one page conflating "content you maintain" with "account you administer," discoverable only by accident. (2) Removed the custom `SessionManagement` component and its backend endpoints (`GET/POST /admin/account/sessions*`, `app/services/clerk_sessions.py`) entirely — Clerk's own `<UserButton>` → "Manage account" modal already lists active sessions and revokes them via `UserProfile`'s native Security tab, so the custom implementation was a straight duplicate, not a gap-filler. (3) Deleted `HistoryDrawer.tsx`, a fully-built archive-browsing drawer that had been superseded by the Command Palette (⌘K) at some earlier point but was never removed — it was imported nowhere and completely unreachable. (4) The idle home screen's home-grown "Recent" list (last 4 jobs) was removed in favor of the Command Palette, which already does the same job with search — the core-loop screen went from three "browse my past applications" surfaces (idle list + palette + `/applications`) down to two, with the palette and `/applications` covering quick-jump and full-browse respectively. Separately, the generation flow's URL is now shallow-synced to `/jobs/{id}` via `window.history.replaceState` the moment a job starts (no visible navigation, no change to the "no navigation during the core loop" feel) — previously the entire idle→generating→result sequence lived in React state with zero URL involvement, meaning a refresh at any point during or after generation silently lost the job back to a blank idle screen even though it was fully persisted server-side.

**ADR-012** — Navbar and account-menu overhaul (2026-07-03), dark-mode-only pass. (1) App is now dark-mode-only — `globals.css`'s `@media (prefers-color-scheme: dark)` block was removed and its values promoted to the permanent `:root` defaults; there was never a real light mode meant to be seen, just an unstyled fallback. (2) Clerk's `appearance` config moved to the `ClerkProvider` level (`lib/clerkAppearance.ts`) so it covers every Clerk component uniformly. Root-caused a dark-mode contrast bug that looked like a single broken icon but wasn't: Clerk computes several element text colors (`headerTitle`, `profileSectionTitleText`, `navbarButtonText`, and others) via automatic contrast against the `colorBackground` variable, and a literal `'transparent'` value read as "light" to that calculation — producing solid near-black text across every Clerk screen regardless of `colorText`/`colorNeutral`. Fixed by giving `colorBackground` a real dark hex value used only for Clerk's internal contrast math (the actual visible glass background still comes from the `card` element's own `backgroundColor` override); also layered `@clerk/themes`' `baseTheme: dark` underneath as a foundation, since some sub-components (modal close button, inactive nav tabs, device-session icons) don't derive from theme variables at all. (3) Replaced Clerk's stock `<UserButton>` dropdown + "Manage account" modal with a custom `UserMenu` component (name, email, Settings, Sign out) — beyond the contrast bugs, Clerk's Security tab exposes a native "Delete account" action that bypasses this app's own grace-period deletion flow (`components/AccountDeletion.tsx`) entirely, deleting the Clerk identity directly without cleaning up app data first; removing the modal removes that landmine along with the theming burden. Session/device management is consequently not exposed in-app — use the Clerk dashboard directly if a manual revoke is ever needed. (4) Deleted `CommandPalette.tsx` (⌘K) as dead code — search moved to a plain inline input on `/applications` itself, filtering the existing list by title/company alongside the status tabs; the navbar's search icon and the standalone Account gear icon were both removed, since Settings is now reachable via the avatar dropdown and reintroducing a second nav path to the same page added clutter without adding capability. (5) Navbar icons redesigned: Applications is now stacked layers ("a pile of submitted things" — briefcase was the first pass but layers reads more like a history/archive), and the former "Background" page — previously a document/folder icon — is now titled "Resume" with a closed-book icon; a plain document glyph risked reading as "your generated resumes/applications" (this product's actual output) rather than "the structured data that feeds generation," and "Profile" was considered and rejected as a title since it collides with account identity, which lives separately under Settings.

**ADR-013** — Encrypted BYO Anthropic API key, no shared fallback (Phase 3, 2026-07-01). Every generation/insights call requires the requesting user's own stored key or fails with a clear 400 — `settings.anthropic_api_key` was removed entirely, this is a hard cutover, not an optional path. Keys live in `ai_credentials` (`user_id`, `provider`, `encrypted_key`, `key_hint`), encrypted via `app/services/crypto.py`'s envelope encryption (`cryptography`'s `Fernet`/`MultiFernet`, so rotating `ENCRYPTION_MASTER_KEY` doesn't break decryption of rows encrypted under a previous key — `ENCRYPTION_MASTER_KEY_PREVIOUS` holds prior keys comma-separated). `POST /admin/settings/api-key` validates the submitted key with one real tiny forced-tool-call to Anthropic, billed to the submitter's own key, before storing it. This is the actual mechanism behind "CareerOS owns the workflow, users own their AI usage" — see README's "why it isn't just a resume generator."

**ADR-014** — Public waitlist landing page + legal pages (Phase 8, 2026-07-02). `/` is a public route; `app/page.tsx` renders `components/LandingPage.tsx` instead of the core loop whenever Clerk's `useUser()` reports signed-out, gating open signup behind an invite (Karan chose waitlist over open signup deliberately — buys time to prove the reliability/abuse guardrails from Phases 5–7 hold under real concurrent load before opening the door, which is irreversible). Waitlist entries (`app/models/waitlist.py`) are a plain signup list, not a mailing list — no automated invite-email flow, consistent with the "no email digests/marketing" constraint above; `invited_at` is set manually by Karan. `/terms` and `/privacy` are public, AI-drafted and explicitly marked as not legally reviewed — real legal review is still outstanding before a genuine public launch (see roadmap Phase 8 "Remaining").

**ADR-015** — Resume/cover-letter download and preview unification (2026-07-05). The result view previously had two separate resume-download affordances (one in the PDF preview overlay, one below it) and a cover letter that was a plain editable textarea with no visual relationship to the typeset resume next to it. Replaced with one shared pattern in `components/ResultSections.tsx`: a single icon-only `DownloadIconButton` (rounded-square, spinner → checkmark states) per document, and a `CoverLetterSection`/`CoverLetterPreview` pair that gives the cover letter the exact same real-compiled-PDF-preview treatment the resume already had, via a new `GET /admin/jobs/{id}/cover-letter-preview.pdf` endpoint (mirrors the existing resume preview endpoint, shares the same `PDFStorage` cache the download endpoint reads from). Editing moved into a collapsible panel below the preview instead of always-visible; saving remounts the preview via a changed `key` (not an effect-driven state reset, to avoid `react-hooks/set-state-in-effect`) so it recompiles from the edited text. Both `/` and `/jobs/[id]` share these components — the archive page gained cover-letter editing it never had before. Also reworked the cover letter LaTeX header (`_COVER_LETTER_LATEX` in `backend/app/services/generation.py`): name vertically centered in the shaded band via `\AddToShipoutPictureBG*`, contact/links line pulled tight against the band's bottom edge — tuned entirely through real Tectonic compiles, not source inspection alone.

---

## Hard constraints

- Do not add automated job ingestion
- Do not auto-submit applications
- Do not add multi-user features
- Do not change the Claude model without updating ADR-001
- Do not fabricate profile data in generated resumes
- Do not run DB migrations without flagging to Karan
- Do not add chat interfaces
- Do not add analytics dashboards
- Commit freely; push only when explicitly told to
