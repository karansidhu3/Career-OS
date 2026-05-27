# CareerOS — Claude Context

Read this first. Everything needed to build and continue this project without re-explanation.

---

## What this project is

CareerOS is a personal job application tool built for one user (Karan).
Karan pastes a job description → Claude reads it against his persistent profile DB →
generates a tailored resume (LaTeX) and cover letter for that specific role.

This is not a SaaS product. It is a personal tool built to accelerate a real job search.
Every decision should optimize for: reliability, low/zero cost, and speed of output quality.

---

## The problem it solves

Every application starts from scratch. Manually rewriting a resume and cover letter per role
is slow and inconsistent. CareerOS maintains a persistent profile of Karan's education,
experience, projects, and skills — and uses that to generate genuinely tailored materials
for any job description he pastes in, in seconds.

As Karan ships new projects over the coming months, he updates the profile DB once.
Every future generation automatically has access to the new work.

---

## Core features (build these, nothing else)

1. **Manual JD paste** — Karan pastes a raw job description into the dashboard.
   The system reads it and kicks off generation. No job source API needed.

2. **Fit scoring** — Claude reads the JD + full profile, returns a score 1–10 and
   3-bullet rationale. Shown before/alongside generated materials so Karan can
   decide whether to proceed with the application.

3. **Resume generation** — Claude generates a tailored resume for the specific JD.
   Output: LaTeX (.tex) matching Karan's Overleaf template. Karan copies into Overleaf,
   compiles, done.

4. **Cover letter generation** — Claude generates a tailored cover letter per job.
   Format: 3 paragraphs, no fluff. See cover letter spec below.

5. **Dashboard** — Simple web UI. Paste box, view generated materials, copy .tex,
   mark job as applied/skipped. History of all past generations.

---

## What NOT to build

- Automated job ingestion (no Adzuna, no Indeed RSS, no scrapers)
- Email digest
- Scheduled background jobs
- Skill gap analysis
- Auto-submitting applications
- Multi-user support
- Any social features

Do not add features without discussion.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12), async |
| Frontend | Next.js 15 (App Router), React, Tailwind CSS |
| Database | PostgreSQL (SQLAlchemy async) |
| LLM | Claude API (claude-sonnet-4-20250514) |
| Hosting | Railway (free tier or $5/month) |

---

## Deployment

Target: Railway. Backend + frontend + Postgres all on Railway.
Keep costs at zero or near-zero. Only real cost is Claude API usage (cents per generation).
No Docker required — Railway deploys directly from GitHub.

---

## Karan's profile (seed data for the DB)

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
- Temporal signal tracking across months; not retrieval but emergence velocity
- Thesis confidence scoring, company radar, portfolio alignment layer
- Production Docker Compose stack; local LLM pipeline at scale

**Agentic Market Sentiment System** (Dec 2025)
- Tech: Python, Groq AI, YFinance API, DuckDuckGo, FastAPI
- Multi-agent AI system; reduced manual research time by 70%
- Agents for market data, news, sentiment; 100+ structured data points per query

**FDA Cancer Drug–Protein Network Analysis** (Nov 2025)
- Tech: R, igraph, tidyverse
- Bipartite drug–protein network from FDA oncology datasets + BioGRID PPI network
- Centrality and hub analysis for drug sensitivity/resistance pathways

**[Movie Recommender removed — Karan will replace with a stronger project]**

### Skills
- Languages: Python, JavaScript, Java, C++, R
- Frameworks: React, Next.js, Node.js, Express.js, FastAPI, Docker
- Databases: PostgreSQL, MongoDB, MySQL
- Tools: Git, Jupyter, Pandas, NumPy, Matplotlib, TensorFlow, PyTorch

---

## Cover letter format spec

3 paragraphs, no filler phrases ("I am excited to apply..."), no clichés.

**Para 1:** What specifically caught my attention about this role/company (pulled from JD).
One concrete sentence about why it fits where I'm headed.

**Para 2:** The most relevant thing I've built that maps to what they need. Specific, technical,
results where possible. Reference the project by name.

**Para 3:** Short close. Available to start [date], open to discussion.

Tone: direct, confident, not desperate. Read like a person wrote it, not an AI.

---

## Resume LaTeX template

When generating tailored resumes:
- Reorder projects to put most relevant first
- Rewrite bullet points to emphasize skills/outcomes matching the JD
- Never fabricate experience or skills not in the profile DB
- Keep education and contact info identical every time
- The Sales Associate experience at Old Navy is NOT a technical role — omit it always
- MarketMind AI is the strongest project — include it first for most tech roles
- Movie Recommendation Engine has been removed from the profile

Note: `\iconlink` is used in the heading but not defined in the preamble.
Add `\newcommand{\iconlink}[1]{#1}` to the preamble before compiling.

```latex
%-------------------------
% Resume in Latex
% Author : Sourabh Bajaj
% License : MIT
%------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[pdftex]{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome5}



\pagestyle{fancy}
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.7in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-6pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-4pt}]

%-------------------------
% Custom commands
\newcommand{\resumeItem}[2]{
  \item\small{
    \textbf{#1}{: #2 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-4pt}
}

\newcommand{\resumeSubItem}[2]{\resumeItem{#1}{#2}\vspace{-4pt}}

\renewcommand{\labelitemii}{$\circ$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=*]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\newcommand{\projectSubheading}[5]{
  \vspace{-1pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{\href{#5}{#1 \hspace{2pt}\faGithub}} & #2 \\
      \textit{\small#3} & \textit{\small#4} \\
    \end{tabular*}\vspace{-5pt}
}

\newcommand{\resumeSubheadingNoRole}[2]{
  \vspace{-1pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
    \end{tabular*}\vspace{-5pt}
}



%-------------------------------------------
%%%%%%  CV STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%


\begin{document}

%----------HEADING-----------------
\begin{tabular*}{\textwidth}{l@{\extracolsep{\fill}}r}
  \textbf{\href{https://www.linkedin.com/in/karan-sidhu3/}{\Large Karanveer Sidhu}} &
  \iconlink{\faEnvelope} \href{mailto:karansidhu5550@gmail.com}{karansidhu5550@gmail.com}\\
  \iconlink{\faLinkedin} \href{https://www.linkedin.com/in/karan-sidhu3/}{linkedin.com/in/karan-sidhu3} &
  \iconlink{\faPhone} +1 (250) 509-2500 \\
  \iconlink{\faGithub} \href{https://github.com/karansidhu3}{github.com/karansidhu3} & \\
\end{tabular*}


%-----------EDUCATION-----------------
\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {University of British Columbia}{Sep. 2022 -- Jun. 2026}
      {Bachelor of Science in Computer Science, Minor in Data Science}
      {}
  \resumeSubHeadingListEnd

%-----------EXPERIENCE-----------------
\section{Experience}
  \resumeSubHeadingListStart

    \resumeSubheading
      {Full Stack Developer}{May 2025 -- Aug. 2025}
      {University of British Columbia}{}
      \resumeItemListStart
        \resumeItem{\href{https://github.com/karansidhu3/TA-Connect.git}{TA Matching Platform \hspace{2pt}\faGithub}}
          {Developed a full-stack platform using \textbf{Next.js, React, and Node.js} to automate TA profile matching across the Science faculty, \textbf{reducing 120+ hours} of manual allocation work per term.}
        \resumeItem{Frontend Architecture}
          {Designed a \textbf{modular, multi-step form workflow} with schema-based validation, improving code maintainability, reusability, and UX consistency.}
        \resumeItem{Relational Data Modeling \& Infrastructure}
          {Implemented and \textbf{Dockerized} a normalized \textbf{PostgreSQL} schema with many-to-many relationships, supporting efficient querying and scalable backend development.}
      \resumeItemListEnd

    \resumeSubheading
      {Research Assistant}{May 2024 -- Aug. 2024}
      {University of British Columbia — SIMLAB Research Group}{}
      \resumeItemListStart
        \resumeItem{Wildfire Graph Modeling}
          {Built \textbf{spatial graph models} representing terrain, vegetation, and powerline networks in Kelowna to simulate wildfire spread and connectivity patterns.}
        \resumeItem{Algorithmic Risk Analysis}
          {Implemented graph algorithms to compute probabilistic fire propagation paths, identify \textbf{high-risk nodes} near infrastructure, and quantify potential impact on the Western Interconnected Grid.}
      \resumeItemListEnd

  \resumeSubHeadingListEnd


%-----------PROJECTS-----------------
\section{Projects}
  \resumeSubHeadingListStart

    \projectSubheading
      {Agentic Market Sentiment System}{Dec. 2025}
      {Python, Groq AI, YFinance API, DuckDuckGo, FastAPI}{}
      {https://github.com/karansidhu3/finance_agent.git}
      \resumeItemListStart
        \resumeItem{Autonomous Multi-Agent System}
          {Built a multi-agent AI system using \textbf{Groq-hosted LLMs} with agents for market data, news, and sentiment analysis, processing equities and reducing manual research time by 70\%.}
        \resumeItem{External Data Orchestration}
          {Integrated YFinance APIs and DuckDuckGo web search to ingest real-time market data and news, processing \textbf{100+} structured data points per query with source attribution.}
      \resumeItemListEnd

    \projectSubheading
      {FDA Cancer Drug--Protein Network Analysis}{Nov. 2025}
      {R, igraph, tidyverse, Network Analysis, Community Detection}{}
      {https://github.com/karansidhu3/Network-Analysis-of-FDA-Approved-Cancer-Drugs-and-Protein-Interactions.git}
      \resumeItemListStart
        \resumeItem{Network Construction \& Integration}
          {Built a large-scale \textbf{bipartite drug--protein network} from FDA oncology datasets and expanded it using the \textbf{BioGRID human PPI network}.}
        \resumeItem{Centrality \& Hub Analysis}
          {Identified key hub proteins using degree and betweenness centrality, highlighting pathways driving drug sensitivity and resistance.}
      \resumeItemListEnd

  \resumeSubHeadingListEnd


%--------PROGRAMMING SKILLS------------
\section{Skills}
\vspace{-2pt}
\begin{itemize}[leftmargin=*, itemsep=-2pt, topsep=2pt]
  \item \small{\textbf{Languages}: Python, JavaScript, Java, C++, R}
  \item \small{\textbf{Frameworks \& Tools}: React, Next.js, Node.js, Express.js, FastAPI, Docker}
  \item \small{\textbf{Databases}: PostgreSQL, MongoDB, MySQL}
  \item \small{\textbf{Tools \& Libraries}: Git, Jupyter, Pandas, NumPy, Matplotlib, igraph, TensorFlow, PyTorch}
\end{itemize}
\vspace{-6pt}


\end{document}
```

---

## Sprint structure

**Sprint 1** — Profile DB + schema. Seed Karan's data. Admin endpoints to view/edit profile. ✅ Done.

**Sprint 2** — Generation pipeline. Manual JD paste endpoint. Claude generates fit score + resume (LaTeX) + cover letter in one call. Store results to DB.

**Sprint 3** — Dashboard UI. Next.js frontend: paste box, loading state, display generated resume + cover letter, copy .tex button, mark applied/skipped, history list.

**Sprint 4** — Deploy to Railway. Backend + frontend + Postgres. Production env vars. Done.

---

## Architecture decisions

- **ADR-001** — Claude API (cloud) not local LLM. Quality matters for resume generation.
  MarketMind uses local LLM because volume is high; CareerOS volume is low (one JD at a time)
  so API cost is negligible (~cents per generation) and output quality is higher.
- **ADR-002** — No automated job ingestion. Karan pastes JDs manually from LinkedIn or
  wherever he finds them. Simpler, more focused, works with any job source.
- **ADR-003** — Railway for hosting. Zero-config deploys from GitHub. Free/cheap tier.
  No Docker complexity needed at this scale.

---

## What not to do without discussion

- Do not add automated job ingestion of any kind
- Do not auto-submit applications — Karan submits manually after review
- Do not add multi-user features
- Do not change the Claude model without updating ADR-001
- Do not fabricate profile data in generated resumes — only use what's in the DB
- Do not run DB migrations without flagging to Karan
