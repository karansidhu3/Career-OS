# CareerOS

Paste a job description. In about twenty seconds, get back a resume and a cover letter written specifically for that role — not reworded from a template, built from a career history the system actually understands.

<br>

## The problem

Tailoring a resume for a single posting takes real work: rereading the description, deciding which two or three projects actually matter for it, rewriting bullets so the numbers and keywords line up, writing a cover letter that doesn't sound like every other cover letter. A real job search means doing that dozens of times. Most people stop doing it carefully somewhere around the fifth application, and stop doing it at all somewhere around the fifteenth.

The common workaround is a general chat window: paste your background, paste the posting, ask for a resume, edit what comes back, ask again next time. It works. It also means re-explaining who you are, from scratch, for every single application.

CareerOS removes the re-explaining. A person's background lives in the system once. Every generation starts from there.

<br>

## What it looks like

> **[VISUAL — hero, idle state]**
> The home screen at rest: a single paste box, focused automatically on load, nothing else competing for attention. Capture at the app's real content width, light background, cropped tight with no browser chrome.

> **[VISUAL — generating state]**
> A few seconds of screen recording rather than a static frame: the elapsed-time counter and the status line changing as it works ("Matching your background to this role…").

> **[VISUAL — result state]**
> The most important image in this document. Fit score, the strategic read on the role (what's a genuine strength, what's a real gap, what to do about it), which projects the system chose to lead with and why, and the compiled resume sitting inline as a live preview.

> **[VISUAL — cover letter and source]**
> The editable cover letter panel, and underneath it, the LaTeX source it compiles from, collapsed by default. For anyone technical reading this: the output isn't a black box. The typeset source is one click away.

<br>

## How it works, from the outside

Open the app. Paste a job description. One key combination. Wait roughly twenty seconds. Read a short, specific read on the fit. Download a resume and a cover letter, both compiled to PDF, both built for that posting. Move to the next application.

There's no dashboard to configure first, no template to choose, no fields beyond the one paste box. During that loop the interface has exactly one job, and it does nothing else while the user is in it.

<br>

## Why it isn't just a resume generator

Every generation writes back into the same place it reads from. CareerOS keeps a structured model of a person's work — companies, roles, projects, skills, education — not a resume file, but the underlying facts a resume gets assembled from. That structure is what makes tailoring possible at all: the system isn't rewriting a document, it's selecting and reframing from a body of knowledge it already has, choosing which projects matter for this specific posting and building bullets around the numbers that posting actually asked for.

The same structure lets the system notice things a single resume never could. After enough applications, CareerOS looks across every one of them and surfaces a pattern: which roles a person is consistently strong for, where the same gap keeps showing up, what's worth fixing before the next application instead of after. One specific observation, generated the same way the resumes are — not a dashboard of counts to feel good about.

It also doesn't get quietly more expensive to run the more it's used. Every generation runs on the user's own AI provider key, encrypted at rest, never shared, never billed to anyone but its owner. CareerOS owns the workflow. Each person owns their own usage.

<br>

---

<br>

*Everything below this line is about how CareerOS is built, not what it does. The [stack](#built-with) and [local setup](#running-it-locally) are further down if that's what brought you here.*

<br>

## Under the hood

> **[VISUAL — architecture diagram]**
> Request flow: browser → Vercel (Next.js) → Fly.io API (FastAPI) → Postgres / Redis / Anthropic, with a separate worker process pulling from the same queue for anything too slow for a request/response cycle. Plain boxes and arrows — no gradients, matching the product's own restraint.

**Every user's data is isolated by the database, not just by application code.**
Most multi-tenant systems enforce "your data, not theirs" entirely in application code — a `WHERE user_id = …` clause that has to be remembered, correctly, on every query, forever, by everyone who ever touches the codebase. One missed clause is a data leak. CareerOS enforces isolation at the database itself: every user-scoped table runs under Postgres row-level security, forced on, tied to a value set once per request, through a database role that has no ability to bypass it. Postgres exempts superusers from row-level security unconditionally, so the role that actually handles requests deliberately isn't one. The application-layer checks still exist. Row-level security is what holds if one of them is ever wrong.

**The AI provider is a seam, not a dependency baked into the business logic.**
Generation code calls an interface, not Anthropic's SDK directly. The same pattern repeats for PDF storage and for the two transactional emails the system sends: an abstract interface, one real implementation, and a no-op fallback for local development. Changing providers, or adding a second one, is a new implementation of an existing interface — not a rewrite of everything that calls it.

**Generation runs somewhere that can fail without losing anything.**
A resume call can run long enough that it doesn't belong inside the request that triggered it. CareerOS enqueues the work and runs it in a separate worker process reading from the same queue. If the API redeploys mid-generation, the job is still there when the worker comes back. Nothing disappears because a container happened to restart at the wrong moment.

**The output is typeset, not approximated.**
Resumes aren't styled HTML printed to PDF. They're assembled as LaTeX and compiled with Tectonic, in a fresh, sandboxed subprocess per request, with a stripped environment that never has access to a database credential or an API key. The document that comes out the other end is the same class of artifact a person who cared about kerning would produce by hand, because it's actually typeset.

**It was reviewed before it was trusted with anyone else's data.**
Before extending access past its own author, CareerOS went through a full security review — authentication, authorization, secrets handling, upload safety, subprocess isolation — treating every earlier assumption as unproven and re-checking it against the code as it actually exists today. What the review found, and what came out of fixing it, is part of the project's history, not something smoothed over.

<br>

## Built with

| | |
|---|---|
| **Frontend** | Next.js (App Router), React, Tailwind, Framer Motion |
| **Backend** | FastAPI, async Python |
| **Database** | PostgreSQL, row-level security, SQLAlchemy |
| **Auth** | Clerk |
| **AI** | Claude (Anthropic), behind a swappable provider interface |
| **Job queue** | ARQ + Redis |
| **Document generation** | LaTeX, compiled with Tectonic |
| **Object storage** | Cloudflare R2 |
| **Hosting** | Fly.io (API + worker), Vercel (frontend), Neon (Postgres), Upstash (Redis) |
| **Observability** | Structured JSON logging, Sentry |

<br>

## Running it locally

<details>
<summary><strong>Setup instructions</strong></summary>

<br>

Requires Python 3.12+, Node 20+, a Postgres instance, a Redis instance, a Clerk application, and an Anthropic API key for local testing.

```bash
git clone https://github.com/karansidhu3/Career-OS.git
cd Career-OS

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL, CLERK_*, ENCRYPTION_MASTER_KEY
uvicorn app.main:app --reload

# Worker — separate terminal
arq app.worker.WorkerSettings

# Frontend — separate terminal
cd frontend
npm install
cp .env.local.example .env.local   # Clerk keys
npm run dev
```

Every user supplies their own Anthropic key through the interface after signing in. There's no shared key to configure, by design.

</details>

<br>

---

<br>

CareerOS started as a tool built to fix one person's own job search. It's still used that way — by the person who built it, on every application he sends. That's the standard it's actually held to: not a feature roadmap, but whether it makes the next application meaningfully better than doing it by hand.
