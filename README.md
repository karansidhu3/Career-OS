# CareerOS

**I was spending 45 minutes per job application doing work a computer should do.**

Paste a job description. Get a tailored resume and cover letter in about 20 seconds. The system reads the JD, selects which of your projects are most relevant to that specific role, and writes targeted bullets from your profile. No re-explaining your background. No prompting. No templates.

I built this for my own job search. I use it for real applications.

<div align="center">
  <img src="screenshots/final/04-result-with-pills.png" alt="CareerOS result state: fit analysis with project selection decision visible" width="860" />
  <p><sub>The system committed to which projects to emphasize before writing a word of the resume. That decision is visible in the pills above the PDF preview.</sub></p>
</div>

---

## The Problem

Tailoring a resume for a specific job description is genuinely hard. Not hard in the sense of requiring skill, but hard in the sense of requiring careful reading, judgment about what to emphasize, and then disciplined writing to match the JD's language exactly. When I was doing this manually, a single application took 30–60 minutes: read the JD, decide which of my projects actually addressed the requirements, rewrite bullets using the JD's exact phrasing, draft a cover letter that referenced the specific technical problem they were hiring for.

Most of that time was spent on decisions, not writing. Which two projects should I put at the top? Does my distributed systems work or my ML work better match what this role needs? The writing itself was fast once I knew what to say.

The other problem was consistency. Over 20+ applications, my resume had drifted. Different phrasings for the same experiences. Projects emphasized based on what I'd most recently worked on rather than what matched the role. No systematic keyword extraction. I was losing ATS filtering on roles I was qualified for.

---

## Why Existing Solutions Failed

**ChatGPT / general LLMs:** No persistent context. Every session starts from scratch. You paste your resume, paste the JD, explain what you want, iterate on the output. The prompt-engineering burden is on you, not the system. After 20 applications, you've explained your background 20 times and the outputs reflect your prompting skill as much as your actual experience.

**AI resume builders:** Most work by taking your existing resume and rewriting it. The selection problem — which projects belong in this resume — is left to you. You still have to manually move sections around for each role.

**Job application trackers:** CRM-focused. Good for tracking status, not for generating content. Orthogonal to the problem.

**The shared failure mode:** All of these tools treat resume tailoring as a writing problem. It is primarily a selection and analysis problem. Which facts about you are most relevant to this specific role? Once that's answered correctly, the writing is easy.

---

## The Core Insight

The hardest part of resume tailoring is not writing — it's deciding what to include.

When I looked at my failed attempts with ChatGPT, most of the bad outputs had one thing in common: the model chose the wrong projects to emphasize. It picked projects based on thematic similarity ("you worked on ML, this is an ML role") rather than direct requirement coverage ("this JD specifically requires experience with evaluation frameworks and annotation pipelines, and your LLM Eval project directly covers both").

The question I needed the model to answer *before* writing anything was: given this JD, which of my projects most directly address the highest-weight requirements?

**The implementation:** I put `selected_projects` as the first field in the Claude tool schema.

```json
{
  "selected_projects": {
    "description": "FILL THIS FIRST — commit to which projects to include before writing the resume. List project names in order of JD-relevance. 2-4 projects."
  },
  "resume_latex": { ... },
  "cover_letter": { ... }
}
```

Claude's tool-use implementation fills fields in order. By placing `selected_projects` first, the model is forced to commit to a selection decision before it writes a single bullet. This is chain-of-thought via schema field ordering — not a separate reasoning step, just a structural constraint that prevents the model from jumping straight to writing.

The prompt reinforces this with an explicit four-step planning framework:

```
STEP 1 — Identify the 3-4 highest-weight JD requirements.
STEP 2 — Map each project to those requirements directly, not thematically.
         "Built a multi-agent pipeline" directly demonstrates "agent-based
         systems." It does not directly demonstrate "strong SQL skills" even
         if the project used PostgreSQL.
STEP 3 — Select the projects that collectively cover the most requirements.
         A project covering 3 JD requirements beats two projects each covering 1.
STEP 4 — Plan your bullet strategy before writing.
```

The same profile generates fundamentally different outputs for different roles:

| Role | Projects Emphasized |
|---|---|
| Backend/Systems Engineer | Distributed Tracing System · LLM Eval Framework |
| ML Engineer | LLM Eval Framework · Wildfire Pipeline · Distributed Tracing |
| Full-Stack Product | Real-time Collaborative Editor · Distributed Tracing |

That variance is the whole product. If every role got the same output, there would be no point.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js 16)                          │
│                                                                         │
│   /            idle → generating → result (one surface, no nav)        │
│   /profile     persistent profile editor                                │
│   /jobs/[id]   archive deep-link viewer                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP (X-API-Key auth)
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                          Backend (FastAPI)                               │
│                                                                         │
│   POST /admin/jobs/generate     returns immediately (status=processing) │
│   GET  /admin/jobs/:id          poll until status=generated             │
│   GET  /admin/jobs/:id/resume.pdf   compile LaTeX → PDF via Tectonic   │
│   GET  /admin/jobs/insights         cross-application pattern analysis  │
│   GET  /admin/profile               full profile read                   │
└────────────┬────────────────────────────────────────┬───────────────────┘
             │                                        │
    Background Task                          PDF Compilation
    (asyncio, no proxy timeout)              (Tectonic, server-side)
             │                                        │
    ┌────────▼────────┐                    ┌──────────▼──────────┐
    │   Claude API    │                    │     Tectonic        │
    │ tool_use call   │                    │ LaTeX → PDF binary  │
    │ ~20s wall time  │                    │ packages cached     │
    └────────┬────────┘                    └─────────────────────┘
             │
    ┌────────▼────────┐
    │   PostgreSQL    │
    │                 │
    │  personal_info  │
    │  experience     │
    │  project        │
    │  skill_category │
    │  job            │  ← resume_latex, cover_letter, selected_projects,
    └─────────────────┘    fit_score, fit_rationale, strategic_note
```

**Why background tasks?** Generation takes 20–30 seconds. Railway's HTTP proxy has a hard timeout below this. The standard pattern for long-running LLM calls on Railway is to return immediately with a job ID and have the client poll. `POST /generate` creates the job record (status=`processing`), kicks off the background task, and returns the job immediately. The frontend polls `GET /jobs/:id` every 2 seconds until the status changes.

**Why one surface?** The core loop — paste JD, generate, download — should never require navigation. The home page handles all states: idle, generating, result, error. `/jobs/:id` exists only as a deep-link to past results. This constraint forced cleaner state management and meant there was never a page transition mid-workflow.

---

## Generation Pipeline

The system prompt is the primary engineering artifact. Not the API call — the prompt architecture.

```
JD Text ──────────────┐
                       ├──► _format_profile() ──► context string
Candidate Profile ─────┘
  (personal, experience,
   projects, skills,
   cover_letter_voice)

Context String ──────────────────────────────────────────────────────► Claude tool_use
                                                                              │
                                                                              ▼
                                                              ┌───────────────────────┐
                                                              │   GENERATE TOOL       │
                                                              │                       │
                                                              │  1. selected_projects │ ← filled first
                                                              │  2. fit_score         │
                                                              │  3. fit_rationale     │
                                                              │  4. resume_latex      │
                                                              │  5. cover_letter      │
                                                              │  6. job_title         │
                                                              │  7. job_company       │
                                                              │  8. strategic_note    │
                                                              └───────────────────────┘
```

**Profile as prose, not structured data.** Early versions stored experience and projects as pre-written bullet arrays. The model would select bullets from a list. This created a ceiling: the model could only pick what was already written, not extract different aspects for different roles. The backend engineer JD and the ML engineer JD both match MarketMind AI, but they match different things about it — the backend role cares about the FastAPI + PostgreSQL architecture, the ML role cares about the multi-agent pipeline design. Pre-written bullets can't serve both.

Current approach: every experience and project has a prose description field (up to 10,000 chars). The model reads the description and writes targeted bullets from scratch per application. The description is raw material; the bullets are extractions.

**ATS keyword mirroring.** The system prompt explicitly requires using the JD's exact phrasing — not synonyms. `RESTful APIs` not `web services`. `Kubernetes` not `container orchestration`. This is the highest-priority instruction in the prompt because ATS filtering is binary: either the keyword is there or it isn't.

**The cover letter problem.** Cover letters are the most detectable AI output in job applications. The failure modes are predictable: opening with "I am excited to apply", generic enthusiasm, no specific technical content. The prompt addresses this structurally:

- Para 1 must open on the role or company, not the applicant
- Para 2 must be specific enough that "a hiring manager could ask a detailed follow-up question about any sentence and get a 10-minute answer"
- Para 3 is two sentences maximum (availability + open to discuss)
- Em dashes are post-processed out before storage — models generate them constantly despite explicit prohibition

**Self-review step.** The prompt ends with a checklist the model is instructed to run before outputting:
```
□ selected_projects are the highest-JD-coverage choice, not the most impressive
□ Every JD keyword from the requirements is present verbatim
□ Bullets pass the quality test (strong verb → what built → outcome/scale)
□ Cover letter Para 2 names the project, the problem, the decision, the result
□ No sentence could appear in a letter for a different candidate
```

Whether models actually follow self-review instructions is debatable. The checklist serves as emphasis for the most failure-prone behaviors, not a guarantee.

---

## Key Technical Decisions

### 1. Background task pattern instead of streaming

The alternative was streaming the Claude response to the frontend as it arrived, showing the resume being written in real time. This is more interactive and arguably better UX. I chose polling because:

- Railway's proxy timeout is a hard constraint
- Streaming requires keeping an HTTP connection open for 20–30 seconds, which the infrastructure doesn't support
- Polling with a job record means the result persists — a refresh or navigation doesn't lose the output

The tradeoff: the UX has an explicit waiting state with a progress message. Users see a spinner. With streaming they'd see text appearing. For this use case (once or twice per application session) the polling latency is acceptable.

### 2. LaTeX for PDF output, not HTML/CSS

The alternative was rendering the resume as HTML and using a headless browser (Puppeteer) to generate the PDF. LaTeX is harder to generate correctly but gives better output. The specific reasons:

- ATS parsers handle LaTeX-generated PDFs better than browser-rendered ones (better text layer)
- Pixel-perfect line breaking and hyphenation — LaTeX's typesetting engine is decades more mature than CSS
- Resume templates in LaTeX are standardized; the same template always produces the same layout regardless of content length
- Tectonic (the compiler used here) is a single statically-linked binary with no TeX distribution dependencies

The cost: Tectonic needs to download LaTeX packages (~150MB) on first run. Each subsequent compilation on the same container takes 5–15 seconds. When the container restarts (new deployment), the cache clears. I added a startup warmup task that compiles a minimal document at boot to pre-download packages before the first real request arrives.

### 3. No persistent DB columns for compiled PDFs

Currently, PDFs are compiled on every download request. The LaTeX source is stored; the PDF bytes are not. This means every download triggers a Tectonic compilation.

The case for storing compiled PDF bytes in the DB is strong: faster downloads, no Tectonic dependency at request time, one compile per generation. I didn't implement this because it requires a schema change (BYTEA column on the jobs table), and the current approach is functional with a warm Tectonic cache. It's the first thing I'd fix.

### 4. API key in the frontend bundle

The production setup uses `NEXT_PUBLIC_API_KEY` — a key baked into the JavaScript bundle at build time. Anyone who views source can extract it.

For a personal tool that only I visit, the risk is low: the key protects against automated scanners but not a determined person. The alternative is routing all API calls through Next.js server-side route handlers so the key never reaches the browser. This requires rewriting the entire API client layer and introducing a server-to-server hop on every request. For a single-user personal tool, the complexity isn't justified.

If this becomes a multi-user product, the key exposure is the first thing to fix.

### 5. No chat interface

The most common suggestion when I showed this to people was "you should add a chat so you can refine the output." I deliberately didn't.

Chat shifts the cognitive burden back to the user. If the output is wrong, you have to figure out what instruction to give. With a chat interface, the quality of the output depends on your prompting skill — which is what I was trying to eliminate. The correct response to bad output is fixing the profile or the system prompt, not teaching users to prompt better.

The regenerate button exists for cases where the output is genuinely bad. But the solution to systematic quality issues is improving the generation pipeline, not giving users a chat.

---

## Security

Relevant decisions for a deployed personal tool:

**Authentication.** All `/admin/*` routes require an `X-API-Key` header. The key is a 32-byte hex string (`openssl rand -hex 32`). Empty key = auth disabled (local dev). The middleware short-circuits immediately if the key doesn't match — no DB query, no logging of the attempt.

**Input validation.** Pydantic models with explicit `Field(max_length=...)` on everything that touches a Claude prompt. Job description capped at 50,000 chars. Profile descriptions at 10,000 chars. Cover letter voice at 2,000 chars (truncated to 800 at prompt injection). The purpose is twofold: prevent context bloat that degrades generation quality, and prevent a crafted input from exhausting Claude API credits.

**Rate limiting.** The three endpoints that call Claude (`/generate`, `/regenerate`, `/insights`) are rate-limited via `slowapi`. 30/hour on generate and regenerate, 20/hour on insights. The limits are per-IP. For a single user this doesn't matter; they exist to make the cost of abuse concrete.

**Output sanitization.** AI output is capped before storage (`resume_latex` at 120k chars, `cover_letter` at 10k). Em dashes are stripped from cover letters post-generation (models generate them despite explicit prohibition; post-processing is more reliable than prompting). Error messages to the client never contain the underlying exception — stack traces go to server logs only.

**Docker.** The container runs as a non-root user (`appuser`, UID 1001). The Tectonic binary and application code are chowned to that user at build time.

**CORS.** Restricted to the specific frontend origin, not `*`. This was previously hardcoded as `*` — a security audit caught it.

What's deliberately not implemented: GDPR compliance, audit logging, session management, and the full security posture of a multi-user SaaS. This is a personal tool. The surface area is small.

---

## Demo

The demo uses a fictional candidate (Jordan Park, UBC Waterloo CS) with four projects designed to produce different selection outputs for different role types.

<table>
<tr>
<td width="50%">

**Idle state** — single surface, textarea auto-focused

<img src="screenshots/final/01-idle.png" alt="Idle state" width="420" />

</td>
<td width="50%">

**JD pasted** — paste and Cmd+Enter, nothing else

<img src="screenshots/final/02-jd-filled.png" alt="JD filled" width="420" />

</td>
</tr>
<tr>
<td width="50%">

**Generating** — ~20 seconds, background task running

<img src="screenshots/final/03-generating.png" alt="Generating state" width="420" />

</td>
<td width="50%">

**Result** — analysis first, then project selection decision, then resume

<img src="screenshots/final/04-result-with-pills.png" alt="Result with project pills" width="420" />

</td>
</tr>
</table>

**The same profile, three different roles, three different project orderings:**

<table>
<tr>
<td width="33%">
<img src="screenshots/final/05-backend-analysis.png" alt="Backend role result" width="280" />
<p align="center"><sub>Backend/Systems — Distributed Tracing leads</sub></p>
</td>
<td width="33%">
<img src="screenshots/final/06-ml-analysis.png" alt="ML role result" width="280" />
<p align="center"><sub>ML Engineer — LLM Eval Framework leads</sub></p>
</td>
<td width="33%">
<img src="screenshots/final/07-fullstack-analysis.png" alt="Full-stack role result" width="280" />
<p align="center"><sub>Full-Stack Product — Collaborative Editor leads</sub></p>
</td>
</tr>
</table>

The fit analysis is specific enough to be actionable — not "good communication skills" but "Yjs CRDT, WebSocket relay, IndexedDB offline: exact JD requirements built." Gaps are named as specific missing technologies, not vague observations.

<div align="center">
  <img src="screenshots/final/09-history-drawer.png" alt="History drawer showing application archive" width="860" />
  <p><sub>Application history with fit scores. The candacy insights section (left) synthesizes patterns across all applications — here it's flagging that Prometheus is absent from every backend project despite appearing in multiple JDs.</sub></p>
</div>

---

## Running the Demo

The demo uses a fictional candidate profile isolated in its own database.

**Requirements:** Docker, Python 3.12, Node.js 20+, an Anthropic API key.

```bash
# 1. Start a demo Postgres instance
docker run -d --name careeros-demo-db \
  -e POSTGRES_DB=careeros_demo \
  -e POSTGRES_USER=careeros \
  -e POSTGRES_PASSWORD=demopass \
  -p 5433:5432 postgres:16-alpine

# 2. Start the backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

DATABASE_URL=postgresql+asyncpg://careeros:demopass@localhost:5433/careeros_demo \
ANTHROPIC_API_KEY=your-key-here \
ALLOWED_ORIGINS=http://localhost:3000 \
API_KEY="" \
uvicorn app.main:app --reload --port 8000

# 3. Seed the demo profile (in a second terminal)
DATABASE_URL=postgresql+asyncpg://careeros:demopass@localhost:5433/careeros_demo \
ANTHROPIC_API_KEY=placeholder \
ALLOWED_ORIGINS=http://localhost:3000 \
API_KEY="" \
python demo/seed_demo_profile.py

# 4. Start the frontend
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Then open `http://localhost:3000` and paste any of the JDs from `demo/sample_jds/`.

See `demo/README.md` for the full setup guide and what to look for when generating the three sample applications.

---

## Lessons Learned

**Prompt architecture matters more than prompt content.** I rewrote the cover letter section five times before I understood the core problem: the model was skipping directly to writing. Explicit instructions to "be specific" didn't fix it because the model didn't have a structure for what specificity meant. When I added the Para 2 rule ("specific enough that a hiring manager could ask a detailed follow-up question about any sentence and get a 10-minute answer"), the cover letters improved immediately. The change wasn't telling the model *what* to do; it was giving it a verifiable test.

**Schema field order is chain-of-thought.** I spent two weeks trying to fix bad project selection with prompt instructions before I realized the model was writing bullets and *then* deciding what it had "selected." Moving `selected_projects` first in the tool schema fixed the selection quality faster than any prompt change. The model commits to the decision before it can anchor on the writing it's about to produce.

**Post-processing beats prompting for stylistic rules.** Em dashes appear in almost every generated cover letter despite appearing twice in the banned phrases list. Stripping them with a string replacement after generation is 100% reliable. Trying to get the model to consistently avoid a specific Unicode character is not. For stylistic rules where the failure mode is predictable and the fix is deterministic, post-processing is the right tool.

**Persistent profile descriptions are a forcing function.** When I stored pre-written bullets, I was tempted to pre-optimize them — write "the best version" of each bullet and store it. This created mediocre output because the same bullet was used for every role. Switching to prose descriptions removed the temptation. The descriptions contain everything; the model decides what's relevant. This also makes updating the profile feel more natural — describing what you built rather than writing resume bullets.

**The UX constraint I got right:** making the profile editor feel like a document, not a form. Long textarea for each project and experience instead of bullet-point editors. This seemed like a product decision but it was actually a generation quality decision — richer input produces richer output.

**What I got wrong first:** I initially built a chat interface. It made everything worse. Users spent time writing prompts instead of writing profiles. The output quality was proportional to prompt quality. Once I removed chat and made generation one-shot, the incentive structure changed — to get better output, you improve the profile, which is the right behavior.

---

## What I Would Build Next

**Compile PDF at generation time, not request time.** Currently, every download triggers a Tectonic compilation (~10 seconds on a warm container). The right approach is to compile the PDF when the generation background task completes and store the bytes in the database. Downloads then just serve stored bytes. This requires adding `resume_pdf` and `cover_letter_pdf` BYTEA columns to the jobs table and running the compilation in the same background task. The tradeoff: larger database storage, one compile per generation instead of one per download. Worth it.

**Automatic Tectonic package pre-baking.** Right now the startup warmup downloads LaTeX packages at container boot (~90 seconds). The right fix is to run a compilation during `docker build` so the package cache is baked into the image. This would make the Tectonic compile ~3 seconds instead of ~15, and the first request after deployment would be fast immediately. Cost: ~200MB larger Docker image.

**Multi-tenancy.** The current architecture has no `user_id` on any table. Adding multi-tenancy requires `user_id` on `personal_info`, `experience`, `project`, `skill_category`, and `job`; a users table; session management; and an authentication system. The profile editor would need to enforce row-level isolation at the query layer. Nothing structurally prevents this — it's additive work. The API key model would be replaced with per-user JWT tokens. The NEXT_PUBLIC_API_KEY exposure issue disappears because auth moves to the server.

**A/B testing generation approaches.** The system has no way to evaluate whether a prompt change made output better or worse. A proper evaluation setup would require: a set of JD + profile pairs with known expected outputs (or human-rated reference outputs), a pipeline to run both prompt versions and score the outputs, and a way to track which application sessions led to responses or interviews (the only real signal that matters). Without this, prompt changes are driven by intuition and small samples.

**Resume PDF delivery from Railway volumes.** The container's `/tmp/tectonic-cache` is ephemeral. Every deployment clears it. A Railway volume mounted at the cache path would survive redeployments and make the first-compile cost a one-time event per container instance rather than per deployment.

**The hardest thing to build next:** connecting application outcomes to generation quality. Right now I track whether I marked an application as "interview" or "offer", but I don't have a systematic way to ask "did applications generated with this version of the prompt lead to more interviews than the previous version?" Building that feedback loop — even informally — is the highest-leverage improvement. A prompt that produces resumes that get interviews is the only meaningful metric.

---

<div align="center">

**Stack:** FastAPI · Next.js 16 · PostgreSQL · Claude API · Tectonic · Docker · Railway

Built by [Karan Sidhu](https://github.com/karansidhu3) · UBC Computer Science · Class of 2026

*If you're a recruiter or hiring manager reading this: I used CareerOS to apply to your role.*

</div>
