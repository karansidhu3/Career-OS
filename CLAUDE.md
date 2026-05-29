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
- Analytics or career dashboards — CRM thinking
- Multi-user features — destroys personal context moat
- Email integration — out of scope
- Interview scheduler — out of scope
- Gamification or progress metrics — wrong emotional direction
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
| Database | PostgreSQL (SQLAlchemy async) |
| LLM | Claude API (`claude-sonnet-4-6`) |
| Hosting | Railway (Dockerfile-based build) |

---

## Information architecture

```
PRIMARY SURFACE: /
  idle       → textarea focused, faint recent list (≤4 bare text rows)
  generating → cycling messages + elapsed timer, no navigation
  result     → inline: fit + downloads + cover letter + LaTeX source
  error      → message + retry/reset inline

ARCHIVE: /jobs/[id]
  → Deep-link to a specific past result
  → Single-scroll layout, no tabs

HISTORY DRAWER
  → Archive icon in navbar → slides in from right
  → Bare list: title, fit score, date
  → Interview/offer items pinned at top with amber marker

PROFILE: /profile
  → Person icon in navbar
  → Full profile editor
  → Rare interaction — configure once, update occasionally
```

Navbar: wordmark left, two icons right (history, profile). No labels.

---

## Visual identity

Accent: indigo (`#6366F1`). Chosen for this product; not prescribed by doctrine.

---

## Karan's profile (seed data)

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

**Para 1:** What specifically caught attention about this role (from JD). One concrete sentence about fit.
**Para 2:** The most relevant project, described technically. Name it. Results where possible.
**Para 3:** Short close. Available June 2026. Open to discussion.

Tone: direct, confident. No em dashes. No "leveraging." No AI-sounding language.

---

## Resume generation rules

- One page, always
- Never include Old Navy / Sales Associate role
- Never fabricate experience or skills not in profile
- Heading and education: identical every time
- ATS keyword mirroring: extract exact terms from JD, use verbatim
- Bullet structure: strong verb → what you built → outcome/scale
- Max 3 bullets per experience role, max 2 per project, max 3 projects total

---

## Resume LaTeX template

The authoritative template is `LATEX_TEMPLATE` in `backend/app/services/generation.py`.

---

## Architecture decisions

**ADR-001** — Claude API (cloud), model `claude-sonnet-4-6`. Quality is non-negotiable for resume generation. Never change the model without updating this.

**ADR-002** — No automated job ingestion. Manual JD paste only.

**ADR-003** — Railway, Dockerfile-based build. Tectonic binary installed via curl during image build for server-side LaTeX→PDF compilation.

**ADR-004** — Background task generation. POST `/generate` returns immediately (status="processing"). Background task calls Claude, writes result to DB. Frontend polls until done. Sidesteps Railway's HTTP proxy timeout.

**ADR-005** — Inline generation flow. The home page (/) handles all states: idle → generating → result. No route change during the core loop. `/jobs/[id]` is the archive deep-link viewer only.

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
