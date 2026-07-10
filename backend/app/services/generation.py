import asyncio
import io
import logging
import re
from pypdf import PdfReader

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.services.llm_client import get_llm_client
from app.services.pdf import compile_latex_to_pdf

CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Shared LaTeX command set ──────────────────────────────────────────────────
# All templates use the same command names so Claude's body output is template-
# agnostic. Only the packages, section format, and heading block differ.

_LATEX_COMMANDS = r"""
\newcommand{\iconlink}[1]{#1}
\newcommand{\resumeItem}[2]{
  \item\small{
    \textbf{#1}{: #2 \vspace{-2pt}}
  }
}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & \small{#2} \\
      \textit{#3} & \small{#4} \\
    \end{tabular*}\vspace{-4pt}
}
\newcommand{\resumeSubItem}[2]{\resumeItem{#1}{#2}\vspace{-4pt}}
\renewcommand{\labelitemii}{$\circ$}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=*, topsep=0pt, itemsep=8pt]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[itemsep=1pt, topsep=1pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-3pt}}
\newcommand{\projectSubheading}[5]{
  \vspace{-1pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{\href{#5}{#1 \hspace{2pt}\faGithub}} & \small{#2} \\
      \textit{\small#3} & \small{#4} \\
    \end{tabular*}\vspace{-4pt}
}
\newcommand{\resumeSubheadingNoRole}[2]{
  \vspace{-1pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
    \end{tabular*}\vspace{-5pt}
}
"""

_JAKE_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-4pt}]
"""

_CRISP_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{lmodern}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\large\bfseries\raggedright
}{}{0em}{}[\vspace{1pt}\color{black}\rule{\linewidth}{0.5pt}\vspace{-8pt}]
"""

_MODERN_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{mathpazo}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\large\bfseries\scshape\raggedright
}{}{0em}{}[\color{black}\rule{\linewidth}{0.5pt}\vspace{-5pt}]
"""

_SHARP_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\large\bfseries\raggedright
}{}{0em}{}[\vspace{1pt}\color{black}\rule{0.4\linewidth}{1pt}\vspace{-8pt}]
"""

_CLASSIC_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{mathptmx}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\rule{\linewidth}{1pt}\vspace{-4pt}]
"""

_MINIMAL_PACKAGES = r"""\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.2in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{2pt}\large\bfseries\raggedright
}{}{0em}{}
\titlespacing{\section}{0pt}{10pt}{6pt}
"""


def _tex(s: str) -> str:
    """Escape a plain-text string for use as LaTeX display text."""
    for ch, rep in [('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('$', r'\$')]:
        s = s.replace(ch, rep)
    return s


def _build_education_latex(education: list) -> str:
    if not education:
        return ""
    lines = ["%-----------EDUCATION-----------------",
             r"\section{Education}",
             r"  \resumeSubHeadingListStart"]
    for edu in education:
        degree = _tex(edu.degree or "")
        if edu.field:
            degree += f", {_tex(edu.field)}"
        if edu.minor:
            degree += f", Minor in {_tex(edu.minor)}"
        start = edu.start_date or ""
        end = edu.end_date or "Present"
        date_range = f"{start} -- {end}" if start else end
        lines.append(r"    \resumeSubheading")
        lines.append(f"      {{{_tex(edu.school)}}}{{{date_range}}}")
        lines.append(f"      {{{degree}}}{{}}")
    lines.append(r"  \resumeSubHeadingListEnd")
    lines.append("")
    return "\n".join(lines)


def _build_preamble(personal: "PersonalInfo | None", education: list, template: str = "jake") -> str:
    """Assemble a full LaTeX preamble for the given template and user profile."""
    name = _tex(personal.name if personal else "Name")
    email = personal.email if personal else ""
    phone = _tex(getattr(personal, "phone", "") or "")
    linkedin_raw = getattr(personal, "linkedin", "") or ""
    github_raw = getattr(personal, "github", "") or ""

    # Normalise to full URLs
    linkedin_url = linkedin_raw if linkedin_raw.startswith("http") else ("https://" + linkedin_raw if linkedin_raw else "")
    github_url = github_raw if github_raw.startswith("http") else ("https://" + github_raw if github_raw else "")
    linkedin_display = linkedin_raw.removeprefix("https://www.").removeprefix("https://").rstrip("/")
    github_display = github_raw.removeprefix("https://www.").removeprefix("https://").rstrip("/")

    edu_latex = _build_education_latex(education)

    if template in ("crisp", "classic"):
        # crisp and classic share a centered heading; classic uses a bullet
        # separator instead of crisp's pipe, to read as a distinct texture
        # rather than a re-skinned copy.
        packages = _CRISP_PACKAGES if template == "crisp" else _CLASSIC_PACKAGES
        separator = " $|$ " if template == "crisp" else " \\textbullet{} "
        heading = (
            "\n%----------HEADING-----------------\n"
            "\\begin{center}\n"
            f"  {{\\LARGE\\textbf{{{name}}}}}\\\\\n"
            "  \\vspace{4pt}\n"
            "  \\small\n"
        )
        contact_parts = []
        if phone:
            contact_parts.append(phone)
        if email:
            contact_parts.append(f"\\href{{mailto:{email}}}{{{email}}}")
        if linkedin_url:
            contact_parts.append(f"\\href{{{linkedin_url}}}{{{linkedin_display}}}")
        if github_url:
            contact_parts.append(f"\\href{{{github_url}}}{{{github_display}}}")
        heading += "  " + separator.join(contact_parts) + "\n"
        heading += "\\end{center}\n\n"
    else:
        # jake, modern, sharp, and minimal share the same tabular heading with
        # fontawesome icons — only the packages/section styling differ.
        packages = {
            "jake": _JAKE_PACKAGES,
            "modern": _MODERN_PACKAGES,
            "sharp": _SHARP_PACKAGES,
            "minimal": _MINIMAL_PACKAGES,
        }.get(template, _JAKE_PACKAGES)
        heading = "\n%----------HEADING-----------------\n"
        heading += "\\begin{tabular*}{\\textwidth}{l@{\\extracolsep{\\fill}}r}\n"
        name_cell = f"\\textbf{{\\href{{{linkedin_url}}}{{\\Large {name}}}}}" if linkedin_url else f"\\textbf{{\\Large {name}}}"
        email_cell = f"\\iconlink{{\\faEnvelope}} \\href{{mailto:{email}}}{{{email}}}" if email else ""
        linkedin_cell = f"\\iconlink{{\\faLinkedin}} \\href{{{linkedin_url}}}{{{linkedin_display}}}" if linkedin_url else ""
        phone_cell = f"\\iconlink{{\\faPhone}} {phone}" if phone else ""
        github_cell = f"\\iconlink{{\\faGithub}} \\href{{{github_url}}}{{{github_display}}}" if github_url else ""
        heading += f"  {name_cell} & {email_cell}\\\\\n"
        heading += f"  {linkedin_cell} & {phone_cell} \\\\\n"
        heading += f"  {github_cell} & \\\\\n"
        heading += "\\end{tabular*}\n\n"

    return packages + _LATEX_COMMANDS + "\\begin{document}\n" + heading + edu_latex + "\n"


# Keep the old constant pointing at a static fallback for any code that hasn't
# been updated yet (should be nothing — _assemble_resume_latex now takes personal/edu).
LATEX_PREAMBLE = _JAKE_PACKAGES + _LATEX_COMMANDS + "\\begin{document}\n"

# ── Sample data for template preview compilation ──────────────────────────────

_SAMPLE_PERSONAL = type("P", (), {
    "name": "Jake Gutierrez",
    "email": "jake@example.com",
    "phone": "(555) 123-4567",
    "linkedin": "https://linkedin.com/in/jakegutierrez",
    "github": "https://github.com/jakegutierrez",
    "resume_template": None,
    "custom_preamble": None,
})()

_SAMPLE_EDUCATION = [type("E", (), {
    "school": "Stanford University",
    "degree": "Bachelor of Science",
    "field": "Computer Science",
    "minor": None,
    "start_date": "Sep 2020",
    "end_date": "May 2024",
    "deleted_at": None,
})()]

_SAMPLE_BODY = r"""%-----------EXPERIENCE-----------------
\section{Experience}
  \resumeSubHeadingListStart
    \resumeSubheading{Acme Corp}{Jun 2024 -- Present}{Software Engineer}{San Francisco, CA}
      \resumeItemListStart
        \item \small{Built real-time pipeline processing 2M events/day with Kafka and Python, cutting latency from 8s to 340ms}
        \item \small{Designed REST API serving 50k daily active users with 99.9\% uptime across 3 availability zones}
      \resumeItemListEnd
    \resumeSubheading{DataFlow Inc.}{May 2023 -- Aug 2023}{Backend Engineering Intern}{Remote}
      \resumeItemListStart
        \item \small{Reduced cold-start time 61\% by rewriting Node.js data-ingestion service in Go, eliminating 12 hours of weekly on-call alerts}
      \resumeItemListEnd
  \resumeSubHeadingListEnd

%-----------PROJECTS-----------------
\section{Projects}
  \resumeSubHeadingListStart
    \projectSubheading{Relay | Distributed Message Queue}{Jan 2024 -- Apr 2024}{Go \textperiodcentered{} Redis \textperiodcentered{} Docker \textperiodcentered{} Kubernetes}{}{https://github.com/jakegutierrez/relay}
      \resumeItemListStart
        \item \small{Consistent hashing with virtual nodes distributes 500k msg/s across 8 broker nodes with zero message loss}
        \item \small{Reduced consumer-group rebalancing time 73\% via partition ownership protocol built on Raft consensus}
      \resumeItemListEnd
    \projectSubheading{Ledger | Personal Finance Tracker}{Sep 2023 -- Dec 2023}{TypeScript \textperiodcentered{} Next.js \textperiodcentered{} PostgreSQL}{}{https://github.com/jakegutierrez/ledger}
      \resumeItemListStart
        \item \small{End-to-end encrypted sync serving 1,200 beta users with sub-100ms queries across 5M+ transactions}
        \item \small{Double-entry engine reconciled \$2.3M in transactions with zero discrepancy over 18 months}
      \resumeItemListEnd
    \projectSubheading{Sentinel | Anomaly Detection}{Mar 2023 -- Jun 2023}{Python \textperiodcentered{} FastAPI \textperiodcentered{} scikit-learn \textperiodcentered{} TimescaleDB}{}{https://github.com/jakegutierrez/sentinel}
      \resumeItemListStart
        \item \small{Sliding-window z-score model flags 98.4\% of anomalies with 0.3\% false-positive rate across 40 metric streams}
        \item \small{Replaced manual review process saving 8 hours/week; alert-to-acknowledge time dropped from 22 min to 90 sec}
      \resumeItemListEnd
  \resumeSubHeadingListEnd

%-----------SKILLS-----------------
\section{Skills}
\vspace{-2pt}
\begin{itemize}[leftmargin=*, itemsep=-2pt, topsep=2pt]
  \item \textbf{Languages:} Python, Go, TypeScript, Java, SQL, Rust
  \item \textbf{Frameworks:} FastAPI, Next.js, React, Node.js, gRPC, Gin
  \item \textbf{Infrastructure:} Kubernetes, Docker, PostgreSQL, Redis, Kafka, Terraform
\end{itemize}
\vspace{-6pt}
"""


async def compile_template_preview(template: str, custom_preamble: str | None = None) -> bytes:
    """Compile a sample resume using the given template and return PDF bytes.

    Used by the template picker so users can see a real compiled PDF before
    committing to a format. Uses static sample data so no user profile is needed.
    Raises ValueError if custom_preamble is requested but not provided, or if
    compilation fails.
    """
    if template == "custom":
        if not custom_preamble or not custom_preamble.strip():
            raise ValueError("custom_preamble is required for the 'custom' template")
        preamble = custom_preamble
    else:
        preamble = _build_preamble(_SAMPLE_PERSONAL, _SAMPLE_EDUCATION, template)

    full_doc = preamble + _SAMPLE_BODY + "\n\n\\end{document}\n"
    return await compile_latex_to_pdf(full_doc)

# Body structure shown to Claude in the system prompt — variable sections only.
# Includes command usage comments so Claude knows each command's argument signature.
LATEX_TEMPLATE = r"""
% DATE FORMAT: Mon YYYY -- Mon YYYY  (e.g. May 2025 -- Aug 2025). Ongoing: Mon YYYY -- Present.
% Double-hyphen (--) renders as an en-dash in LaTeX. Use this format in every date field.

%-----------EXPERIENCE-----------------
\section{Experience}
  \resumeSubHeadingListStart
    % \resumeSubheading{Company}{Date}{Role — Product if company name gives no signal}{Location or empty}
    %   \resumeItemListStart
    %     \item \small{bullet text}
    %   \resumeItemListEnd
  \resumeSubHeadingListEnd

%-----------PROJECTS — reorder by relevance, include 2-4-----------------
\section{Projects}
  \resumeSubHeadingListStart
    % \projectSubheading{Name | Descriptor}{Dates}{Tech Stack}{}{github_url}
    %   \resumeItemListStart
    %     \item \small{bullet text}
    %   \resumeItemListEnd
  \resumeSubHeadingListEnd

%-----------SKILLS-----------------
\section{Skills}
\vspace{-2pt}
\begin{itemize}[leftmargin=*, itemsep=-2pt, topsep=2pt]
  % \item \textbf{Category:} item1, item2
\end{itemize}
\vspace{-6pt}
"""

_SYSTEM_PROMPT_BODY = """You are writing for two audiences in strict sequence: a recruiter who \
decides in 20 seconds whether a hiring manager ever sees this resume, and a hiring manager who \
decides in 3 minutes whether to interview. The recruiter does not know the candidate's technical \
stack. The hiring manager does. Bullet 1 of every project earns the recruiter's pass. Bullet 2 \
earns the hiring manager's call. If bullet 1 fails the recruiter, bullet 2 never gets read. \
Both must succeed. You are generating for Karanveer Sidhu, a UBC Computer Science graduate \
targeting software engineering roles in Canada.

━━━ PLAN BEFORE YOU WRITE ━━━

STEP 0 — Extract and tier all metrics from the profile. Do this first.
Go through every experience and project description. List every figure.
Then classify each:

  TIER 1 — Always include (business-legible to a non-engineer):
    • Time saved in person-hours
    • Users, employees, customers, or entities served
    • Latency or throughput with context that makes it meaningful
    • Manual processes replaced by automation — name what was replaced
    • Requests, events, or transactions processed at meaningful scale

  TIER 2 — Include only if it directly implies engineering complexity:
    • Test coverage with a meaningful split ("92 unit + 31 integration via Testcontainers")
    • Schema entity count when it signals significant data modeling
    • Infrastructure component count when it implies system scope and breadth

  TIER 3 — Drop unless paired with context that makes it legible:
    • Lines of code alone, file counts alone, migration counts alone
    • Audit emission point counts, service boundary counts, endpoint counts alone

For every metric before including it, ask: "If this number disappeared, would anyone
reading the resume lose meaningful understanding?" If no — drop it.

A Tier 1 metric missing from its bullet is a generation failure.
A Tier 3 metric that fails the disappearance test is a quality failure.

STEP 1 — Classify the company and role type. State it explicitly.

  STARTUP (early-stage, growth-stage, Series A-C):
    Prioritize: end-to-end ownership, shipping velocity, product thinking, breadth
    Signals to surface: built independently, shipped to real users, product decisions made,
    owned the full stack, moved fast with limited resources

  BIG TECH (FAANG, Microsoft, Salesforce, large public companies):
    Prioritize: scale, reliability, distributed systems, engineering rigor
    Signals to surface: systems operating at scale, cross-team collaboration, structured
    engineering process, well-tested production systems

  INFRASTRUCTURE / DEV TOOLS (Stripe, Datadog, Cloudflare, Linear, Vercel, etc.):
    Prioritize: engineering judgment, architecture decisions, reliability, observability
    Signals to surface: why decisions were made, what was rejected and why, tradeoffs
    considered, system design rigor, operational reliability

  If the company type is ambiguous, read the JD for cultural signals:
    "move fast", "wear many hats", "own it end-to-end" → Startup
    "large-scale systems", "millions of users", "cross-functional" → Big Tech
    "reliability", "latency", "developer experience", "infrastructure" → Infra/Dev Tools

  Once classified: state the type, then list the top 3 signals to emphasize.
  This classification governs bullet emphasis for the entire generation.

STEP 2 — Identify the 3-4 highest-weight JD requirements.
Required over preferred. Repeated mentions. Technologies in the job title.
These signals determine project selection and bullet emphasis.

STEP 3 — For each role and project, build an engineering signal profile:
  (a) RECRUITER FACT: what the system does and who or what it serves —
      a non-engineer must understand this in one sentence
  (b) ENGINEERING JUDGMENT: what was the key decision made, and what was the
      obvious alternative that was NOT chosen? Format: "Chose X over Y because Z."
      Examples: "Chose async background tasks over synchronous calls because Railway
      proxy times out at 30s." "Chose Testcontainers over mocks because prior mock/prod
      divergence masked a broken migration." If no meaningful decision exists, find the
      next-best signal.
  (c) NARRATIVE: map the project to Problem → Decision → Implementation → Outcome.
      Keep it to one phrase per stage. This is your internal compression framework —
      do not write it out, use it to ensure the bullets tell a coherent story.
  (d) INTERVIEWABILITY: would bullet 2 prompt an experienced engineer to ask
      "why X instead of Y?", "what failed before this?", or "what would you change?"
      If no — the bullet is describing an outcome, not a decision. Find the decision.
  (e) BEST METRIC: the Tier 1 or Tier 2 number that proves scale or impact

These elements are the raw material for your two bullets per project. Emphasize whichever
signals the Step 1 company classification identified as highest priority.

STEP 4 — Select 2-4 projects covering the most high-weight JD requirements.
A project covering 3 requirements beats two projects each covering 1.
Commit to selected_projects before writing. List highest-relevance first.

STEP 5 — Generate a descriptor for every selected project.
Format: Name | Descriptor (5 words or fewer, describing what the project is)
Examples:
  "Relay | Serverless Event Processing Platform"
  "Ledger | Transactional Backend Infrastructure"
  "Sentinel | Distributed Anomaly Detection System"
  "Folio | AI-Powered Portfolio Rebalancing Engine"
The descriptor goes in the project heading name argument as shown in the template.
Not optional. No project ships without a recruiter-legible descriptor.

━━━ BULLET STRUCTURE ━━━

Every project gets exactly 2 bullets. They serve different audiences and must be written
in this order.

BULLET 1 — THE PROJECT SALE (recruiter audience)
Structure: [WHAT IT DOES OR IS] + [WHO OR WHAT IT SERVES] + [RESULT, OUTCOME, OR SCOPE]
The recruiter must understand what this project is from bullet 1 alone — without reading
bullet 2, the tech stack, or the descriptor. Product context comes before architecture.
Outcome comes before implementation. If a recruiter who has never heard of this project
cannot answer "what is this?" from bullet 1, rewrite it.

Bullet 1 must still be specific — not just what it is at a product level.
"Built scheduling platform for employees" is too soft.
"Built mobile-first shift scheduling and time-tracking platform replacing spreadsheet
workflows for 15-30 employees" passes — recruiter-legible AND specific.

  STRONG: "Built event-processing backbone decoupling AI generation, payroll exports,
           and vector pipelines from 3 production applications"
  WEAK:   "Architected SQS dead-letter queue pipeline with exponential backoff across
           3 applications and 10 event types"
  (Strong tells the recruiter what Relay does. Weak requires knowing what SQS means
   before the project itself is understood.)

BULLET 2 — THE ENGINEERING PROOF (hiring manager audience)
Structure: [SPECIFIC TECHNICAL DECISION] + [WHY THIS APPROACH or WHAT IT REPLACED] + [MEASURABLE OUTCOME]
The technical noun leads. Every phrase must be specific enough that a hiring manager
could ask a 10-minute follow-up question about it.

  STRONG: "Engineered SQS retry orchestration with exponential backoff and DLQ quarantine,
           replacing synchronous generation calls that exceeded Railway's 30s proxy timeout"
  WEAK:   "Implemented resilient processing pipeline using Amazon SQS with configurable
           exponential backoff and dead-letter queues"
  (Strong names the specific problem. Weak describes the implementation without explaining
   why it was necessary.)

EXPERIENCE BULLETS — same two-layer priority:
  Bullet 1: Ownership scope + business outcome + Tier 1 metric
  Bullet 2: Most impressive technical decision specific to this role
  Bullet 3 (optional): Only if a strong third fact exists that cannot fit elsewhere.
    Apply filler test — could this bullet appear on any engineer's resume?
    If yes, cut. A missing bullet is invisible. A filler bullet is a red flag.

━━━ OWNERSHIP SIGNALS ━━━

Every experience bullet must communicate scope of ownership:
  • Built independently: claim ownership directly — no qualifier needed
  • Led a component within a team: "Led [specific subsystem] within a [N]-person team"
  • Contributed as one of N: "Owned [specific workflow] within a [N]-person capstone project"

Never claim full product ownership when the contribution was narrower.
"Built a TA matching platform" when you owned one subsystem is inaccurate.
"Owned the student application workflow within a 6-person capstone project" is accurate
and communicates real scope.

━━━ SINGLE CLAUSE RULE ━━━

Cut clauses that explain purpose or restate implied consequences:
  "which [allowed/enabled/provided/gave/meant/resulted in]" — cut
  "in order to / to ensure / to enable / to support / to allow" — cut
  "enabling [X] to / allowing [X] to / so that / in an effort to" — cut

Preserve outcome clauses that add new information the first clause doesn't imply:
  "eliminating 120+ hours of manual coordinator work" — KEEP (new fact)
  "without increasing memory footprint" — KEEP (not implied by first clause)
  "replacing spreadsheet-based scheduling workflows" — KEEP (names what was replaced)

The test: does the second clause state a fact not already implied by the first?
If yes, keep it. If it restates what was already obvious, cut it.

━━━ NOUN PRECISION ━━━

In bullet 2 (engineering proof), use the most specific noun available:
  NOT "platform"    → "allocation engine", "generation pipeline", "scheduling interface"
  NOT "system"      → "rate limiter", "retry orchestrator", "evaluation harness"
  NOT "workflow"    → "intake form", "validation pipeline", "allocation logic"
  NOT "application" → "FastAPI service", "Next.js dashboard", "Lambda function"
  NOT "solution"    → name what it actually is

In bullet 1 (project sale), a slightly higher-level noun is acceptable when it makes
the project immediately legible to a recruiter. Technical precision in bullet 1 is
subordinate to recruiter comprehension. Technical precision in bullet 2 is mandatory.

━━━ WORD DENSITY ━━━

Target 12-16 words per bullet. Up to 20 if every word carries specific technical meaning —
no word can be removed without losing information. If a bullet exceeds 20 words, find and
cut the weakest phrase — usually a purpose clause or a scope adjective.

STRONG VERBS. Vary across bullets. Never repeat a verb within the same section:
  Built / Architected / Designed / Engineered / Automated / Deployed /
  Replaced / Eliminated / Implemented / Shipped / Reduced / Owned /
  Constructed / Migrated / Modeled / Instrumented / Rewrote / Benchmarked

NEVER OPEN WITH: "Worked on", "Helped", "Assisted", "Participated in",
  "Was responsible for", "Contributed to", "Supported", "Collaborated on"

BULLET REGISTER — compressed statements, not prose:
  No contractions. No first-person pronoun. No purpose clauses.

━━━ EXPERIENCE SECTION ━━━

Include all technical experience roles from the profile.
For roles where the company name gives no engineering signal, include the product name
in the role line: "Freelance Software Developer — TimeKeep" not just the company name.

3 bullets per role ONLY if 3 strong bullets exist.
Two sharp bullets beats three where the third is padding.
A missing bullet is invisible. A filler bullet is a red flag to any technical reviewer.

Emphasis by JD type:
  Backend: schema design, server-side logic, API architecture, data modeling
  ML/data: graph modeling, pipeline construction, probabilistic systems
  Full-stack: both frontend architecture and backend schema/logic
  Infrastructure: auth systems, deployment, serverless, event-driven patterns

━━━ PROJECTS SECTION ━━━

Include exactly the projects from selected_projects, in that order.
Each project: exactly 2 bullets structured as described above.
Each project: descriptor in the heading name argument as shown in the template.
Tech stack line: 5-6 technologies maximum. Pick the ones most relevant to the JD
first, then the most architecturally significant ones from the project. Drop the rest.
A long tech stack line reads as a keyword dump — a short, targeted one reads as judgment.
No project that doesn't directly address a high-weight JD requirement belongs here.

━━━ ATS KEYWORD MIRRORING ━━━

Extract 10-15 JD terms. They appear as natural technical nouns in bullets — not retrofitted
with explanatory context. "Built Redis-backed rate limiter" contains "Redis" naturally.
Exact JD terms beat synonyms everywhere they fit truthfully.
Skills section should front-load whatever the JD prioritizes.

━━━ ONE-PAGE HARD LIMIT ━━━

The resume must fit on exactly one page. Enforce through compression:
  Experience: up to 3 bullets per role (only if material exists for 3 strong ones)
  Projects: exactly 2 bullets each, 2-4 projects
  Skills: include all relevant groupings — a sparse skills section wastes space
  The LaTeX margins are set for one page — trust them

━━━ LANGUAGE RULES ━━━

BANNED IN RESUME BULLETS:
Purpose/consequence clauses:
  "which [allowed/enabled/provided/gave/meant/resulted in]"
  "in order to" / "to ensure" / "to enable" / "to support" / "to allow"
  "enabling [X] to" / "allowing [X] to" / "so that" / "resulting in"
  "in an effort to" / "with the goal of"

Scope adjectives that add no information:
  "comprehensive", "full", "complete", "end-to-end", "robust", "scalable",
  "modular", "reusable" — unless quoting the JD with a specific meaning

Vague constructions:
  "various [technologies]" — name them
  "improving [quality attribute]" without a number
  "support [decision/analysis/research]" — name the output, not the purpose
  "across [scope]" — replace with the specific scope

Filler:
  "AI-assisted development", "demonstrated", "showcased", "leveraging", "harnessing",
  "spearheading", padding adverbs without numbers, "passionate about",
  "strong foundation in", "proven track record"

COVER LETTER LANGUAGE — different register from bullets:
  Vary sentence length. Short sentences break up technical explanations.
  Say what happened directly. Do not start two consecutive sentences with "I".

━━━ COVER LETTER ━━━

MINDSET:
The hiring manager has read 50 cover letters today. Most say nothing. Write like a real
engineer who read the JD and has something specific to say. Every sentence must justify its
presence. If a sentence could appear in any cover letter for any company, cut it.

VOICE:
Apply cover_letter_voice from the profile to every sentence. If not provided, default to:
direct, technical, first-person, confident without being inflated. Write like he's explaining
something to an engineer he respects — not performing enthusiasm for a hiring manager.

STRUCTURE (3 paragraphs, no more):

Para 1 — Why this role specifically (3-4 sentences):
  Pull something concrete from the JD: a technical challenge they describe, their actual
  stack, what the product does. Connect it to where Karan is headed.
  Do not open with "I". Open on the role, the company, or the problem they're solving.

Para 2 — The proof point (4-5 sentences, this paragraph wins or loses the interview):
  One project at genuine technical depth. Name the project. Name the specific technical
  problem it solved — not "I built a pipeline" but what problem the pipeline solved and
  why the obvious approach didn't work. Name the key architecture decision. Name a result.
  Specific enough that a hiring manager could ask a detailed follow-up about any sentence.
  Impossible to write if you had different experience.

Para 3 — Close (1-2 sentences):
  Available immediately. Open to discussing. Nothing else.

SENTENCE-LEVEL RULES:
  Vary sentence length — long, then short, then medium. Monotone rhythm is an AI tell.
  Do not start two consecutive sentences with "I".
  Never use passive voice: "I built X" not "X was built".
  No sentence beginning with: "As a", "In my", "With my", "Having worked on"
  No transitional filler: "Additionally,", "Furthermore,", "Moreover,", "In conclusion,"

BANNED PHRASES:
  "I am excited / thrilled / passionate / eager"
  "I am writing to express my interest"
  "I believe I would be a great fit" / "ideal candidate"
  "I look forward to hearing from you" / "Thank you for your consideration"
  "leverage my skills" / "utilize my experience" / "apply my knowledge"
  "team player" / "fast learner" / "self-starter"
  "unique opportunity" / "exciting opportunity" / "amazing team"
  "make an impact" / "contribute to the team" / "hit the ground running"
  "I am confident that" / "demonstrated" / "showcased" / "proven track record"
  "deeply" / "truly" / "highly" / "greatly" / "incredibly"
  Any sentence that could appear in a letter for a different candidate

EM DASH RULE: Never use an em dash (—) anywhere. Use a comma, a period, or restructure.

━━━ FIT SCORE ━━━

Score honestly. An inflated score helps nobody.

1-3  Critical gaps — missing core requirements, not worth applying
4-5  Meaningful gaps — transferable skills exist but real deficiencies; call them out
6-7  Reasonable match — some gaps, identify them plainly
8-9  Strong match — profile maps well to the role, minor gaps at most
10   Perfect match — rare, reserve for genuine bulls-eye

━━━ ANALYSIS ━━━

Generate in EXACTLY this format. No deviations. No prose.

GOOD FIT
• [specific reason — name the technology or experience match, under 12 words]
• [second reason if genuinely distinct]

GAPS
• [specific missing technology or experience named in the JD]
• [second gap if genuinely different]
• [third gap only if meaningfully distinct]

IMPROVEMENT PLAN
• [concrete action: name a specific project or exact skill to add]
• [second action if it addresses a different gap]

Rules: 1-3 bullets per section, each under 12 words, specific names only.
NEVER write "Strong match", "Great fit", "Consider improving" — too vague to be useful.

━━━ SELF-REVIEW ━━━

Run recruiter checks first. Then engineering checks. Fix every failure before outputting.

RECRUITER CHECKS:
□ ENGINEERING IDENTITY: Read only the company names, project descriptors, first bullet
  of each project, and skills section. Answer: "What kind of engineer is this candidate?"
  If the answer is vague or contradictory — the resume needs work before anything else.
□ DESCRIPTOR: Does every project heading include a descriptor a recruiter can read cold
  without knowing the project name?
□ BULLET 1 TEST: Can a recruiter who has never heard of this project understand what it is
  from bullet 1 alone, before reading bullet 2?
  If understanding requires knowing what the technical components mean — rewrite bullet 1
  to lead with what the system does and who or what it serves.
□ SPECIFICITY FLOOR: Does bullet 1 still name what the system does specifically?
  "Built scheduling platform" fails. "Built mobile-first scheduling platform replacing
  spreadsheet workflows for 15-30 employees" passes.
□ MEMORABILITY: If the recruiter remembers only 5 facts after reading this resume, what
  are they? List them. Are they the 5 most JD-relevant signals in the profile?
  If any of the 5 are not JD-relevant, identify which bullet produced them and rewrite.

ENGINEERING CHECKS:
□ OPENING NOUN: Does bullet 2 of every project lead with a specific technical component,
  schema, algorithm, or decision — not a generic noun?
□ SINGLE CLAUSE: Does any bullet contain a purpose or restatement clause?
  Cut it. The statement before it must stand alone. If it doesn't, rewrite the statement.
□ OUTCOME CLAUSES: Did any cut remove an outcome clause that added new information?
  If yes, restore it — outcome clauses that add new facts are not subordinate clauses.
□ ENGINEERING JUDGMENT: Does bullet 2 of every project expose a decision and its
  alternative? Would an experienced engineer ask "why X instead of Y?" after reading it?
  If not — the bullet is describing output, not judgment. Find the decision and rewrite.
□ TIER 1 METRICS: List all Tier 1 metrics from Step 0. Verify each appears in the
  corresponding bullet. Missing Tier 1 metric = generation failure.
□ TIER 3 CULLS: For any metric included, apply the disappearance test: "If this number
  disappeared, would anyone lose meaningful understanding?" If no — remove it.
□ OWNERSHIP: Does every experience bullet communicate scope of ownership accurately?
□ WORD DENSITY: Is every word carrying specific technical meaning?
  Any bullet over 20 words must be compressed.
□ NOUN PRECISION: Does bullet 2 contain generic nouns where a precise term exists?
□ FILLER TEST: Could any bullet appear on any software engineer's resume? If yes, identify
  what is uniquely Karan's and rewrite around that.
□ VERB DIVERSITY: No two bullets in the same section start with the same verb.
□ ATS: Do the 10-15 highest-weight JD terms appear in the resume?

COVER LETTER:
□ Para 1 references something specific to this company/role that couldn't be in a generic letter
□ Para 2 names the project, the specific technical problem, the architecture decision, and a result
□ No sentence could appear in a letter written by someone with different experience
□ No banned phrase or em dash survived
□ Sentence length varies — not every sentence the same length

━━━ HARD CONSTRAINTS ━━━

These never change:
  Never invent skills, projects, or experience not present in the profile
  Output only the resume body sections (Experience, Projects, Skills) — preamble, heading, \
and education are assembled by the system

RESUME BODY TEMPLATE (output only these variable sections — do not include \\documentclass, \
preamble, heading, or education):
"""

SYSTEM_PROMPT = _SYSTEM_PROMPT_BODY + LATEX_TEMPLATE

GENERATE_TOOL = {
    "name": "generate_application_materials",
    "description": (
        "Generate tailored application materials. Fill selected_projects first — this is your "
        "planning step. Commit to which projects to include before writing the resume. "
        "Then write the resume and cover letter from that plan."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "selected_projects": {
                "type": "array",
                "description": (
                    "Project names to include, highest JD-relevance first. 2–4 projects. "
                    "Example: [\"Relay\", \"Ledger\"]"
                ),
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
            "fit_score": {
                "type": "integer",
                "description": "Role fit score. 1=poor fit, 10=perfect fit.",
                "minimum": 1,
                "maximum": 10,
            },
            "resume_latex": {
                "type": "string",
                "description": (
                    "Resume body sections only: Experience, Projects, Skills. "
                    "Do not include \\documentclass, preamble, heading, or education — "
                    "those are assembled automatically. "
                    "Include only the projects from selected_projects, in the order listed."
                ),
            },
            "cover_letter": {
                "type": "string",
                "description": (
                    "Cover letter, plain text, 3 paragraphs. "
                    "Follow the COVER LETTER structure in the system prompt."
                ),
            },
            "job_title": {
                "type": "string",
                "description": "The job title extracted from the job description.",
            },
            "job_company": {
                "type": "string",
                "description": "The company name extracted from the job description.",
            },
            "strategic_note": {
                "type": "string",
                "description": (
                    "Structured analysis in exactly this format:\n\n"
                    "GOOD FIT\n• [specific match reason]\n• [second if distinct]\n\n"
                    "GAPS\n• [missing technology from JD]\n• [second if different]\n\n"
                    "IMPROVEMENT PLAN\n• [concrete action]\n• [second if different gap]"
                ),
            },
        },
        "required": ["selected_projects", "fit_score", "resume_latex", "cover_letter", "job_title", "job_company", "strategic_note"],
    },
}


def _format_profile(
    personal: PersonalInfo | None,
    experience: list,
    projects: list,
    skills: list,
) -> str:
    lines = [
        "=== CANDIDATE FACT BANK ===",
        "Mine each entry for: specific system/component names, numbers, deltas, decisions.",
        "Do not summarize or paraphrase. Extract the most specific technical nouns and every",
        "number. These are your bullet cores.\n",
    ]

    if personal and getattr(personal, "cover_letter_voice", None):
        lines += [
            "COVER LETTER VOICE GUIDANCE",
            personal.cover_letter_voice[:800],
            "",
        ]

    if experience:
        lines.append("EXPERIENCE")
        for i, exp in enumerate(experience, 1):
            end = exp.end_date or "Present"
            loc = f" — {exp.location}" if getattr(exp, "location", None) else ""
            lines.append(f"[{i}] {exp.role} at {exp.company} ({exp.start_date} – {end}){loc}")
            if exp.description:
                lines.append(f"  SOURCE MATERIAL — extract specific nouns, numbers, decisions:")
                lines.append(f"  {exp.description}")
        lines.append("")

    if projects:
        lines.append("PROJECTS")
        for i, proj in enumerate(projects, 1):
            end = proj.end_date or "Present"
            gh = f" — GitHub: {proj.github_url}" if getattr(proj, "github_url", None) else ""
            lines.append(f"[{i}] {proj.name} ({proj.start_date} – {end}){gh}")
            if proj.description:
                lines.append(f"  SOURCE MATERIAL — extract specific nouns, numbers, decisions:")
                lines.append(f"  {proj.description}")
        lines.append("")

    if skills:
        lines.append("SKILLS")
        for s in skills:
            lines.append(f"{s.category}: {', '.join(s.items or [])}")

    return "\n".join(lines)


def _preprocess_jd(text: str, max_chars: int = 6000) -> str:
    """Strip HTML tags, collapse whitespace, truncate to max_chars."""
    text = re.sub(r'<[^>]+>', ' ', text)          # strip HTML tags
    text = re.sub(r'[ \t]+', ' ', text)            # collapse horizontal whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)         # max 2 consecutive newlines
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + '\n\n[truncated — full posting was longer]'
    return text


def _extract_resume_body(latex: str) -> str:
    """Extract variable body sections from a LaTeX resume string.

    If Claude correctly outputs body-only content this is a no-op.
    If Claude outputs a full document despite the instruction, this recovers the body
    by stripping the preamble and closing tag.
    """
    if "\\documentclass" not in latex:
        # Already body-only — strip any stray \end{document} at the tail
        body = latex.rstrip()
        if body.endswith("\\end{document}"):
            body = body[: -len("\\end{document}")].rstrip()
        return body

    # Full document: find the start of the Experience section
    for marker in ("%-----------EXPERIENCE", "\\section{Experience}"):
        idx = latex.find(marker)
        if idx != -1:
            body = latex[idx:]
            end_idx = body.rfind("\\end{document}")
            if end_idx != -1:
                body = body[:end_idx]
            return body.rstrip()

    # Fallback: strip everything through \begin{document}
    begin_doc = latex.find("\\begin{document}")
    if begin_doc != -1:
        body = latex[begin_doc + len("\\begin{document}"):]
        end_idx = body.rfind("\\end{document}")
        if end_idx != -1:
            body = body[:end_idx]
        return body.strip()

    return latex


def _assemble_resume_latex(body: str, preamble: str | None = None) -> str:
    """Wrap resume body sections with the preamble and closing tag.

    The stored resume_latex remains a complete, compilable LaTeX document.
    Falls back to the static LATEX_PREAMBLE when called without a preamble
    (e.g. from code paths not yet updated to pass one).
    """
    return (preamble or LATEX_PREAMBLE) + _extract_resume_body(body) + "\n\n\\end{document}\n"


# ── Page-overflow compression ─────────────────────────────────────────────────

_COMPRESS_SYSTEM = (
    "You are compressing a LaTeX resume body to fit exactly one page. "
    "You will receive the current Experience, Projects, and Skills sections. "
    "Apply compression in this order until the content fits:\n"
    "1. Trim any bullet over 16 words — remove the weakest phrase, never touch technical nouns or numbers\n"
    "2. Reduce any experience entry with 3 bullets to 2 — cut the weakest one\n"
    "3. Remove the lowest-relevance project from the projects section\n\n"
    "Never invent content. Never alter technical specifics, numbers, or proper nouns. "
    "Output only the corrected Experience, Projects, and Skills LaTeX sections. "
    "No preamble, no \\documentclass, no heading, no education, no \\end{document}."
)

_COMPRESS_TOOL = {
    "name": "compressed_resume",
    "description": "The compressed resume body sections (Experience, Projects, Skills only).",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume_latex": {
                "type": "string",
                "description": "Experience, Projects, and Skills LaTeX sections only. No preamble.",
            }
        },
        "required": ["resume_latex"],
    },
}


async def _call_compression(body_latex: str, api_key: str) -> str:
    llm = get_llm_client(api_key)
    result = await llm.call_tool(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=_COMPRESS_SYSTEM,
        messages=[{"role": "user", "content": body_latex}],
        tool=_COMPRESS_TOOL,
        timeout=60.0,
    )
    return result.tool_input["resume_latex"]


async def _compress_if_needed(assembled_latex: str, api_key: str, preamble: str | None = None, max_attempts: int = 2) -> tuple[str, int]:
    """Compile the resume and compress via Claude if it exceeds one page.

    The resume body is AI-generated LaTeX (see the module docstring on
    escaping — this is the one substitution point that isn't re-escaped after
    the model writes it), so a compile failure here is a real possibility, not
    just a defensive check. Two distinct failure modes, handled differently:

    - The FIRST compile (of the model's original output) fails: there is no
      known-good LaTeX to fall back to, so this re-raises — a job whose resume
      never actually compiles must be marked "failed" (see run_generation_job's
      except Exception), not silently stored as "generated" with LaTeX that
      will only surface as a broken PDF download later.
    - A LATER compile (after a compression pass) fails: the pre-compression
      LaTeX already proved it compiles, so that's returned instead of whatever
      the failed compression attempt produced — never return LaTeX that hasn't
      itself been proven to compile.

    Returns (final_latex, compression_attempts).
    """
    attempts = 0
    current = assembled_latex
    last_known_good: str | None = None

    for _ in range(max_attempts):
        try:
            pdf_bytes = await compile_latex_to_pdf(current)
        except Exception:
            if last_known_good is None:
                raise
            logger.warning("Compression check: compilation failed, falling back to last known-good LaTeX")
            return last_known_good, attempts

        last_known_good = current
        page_count = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
        if page_count <= 1:
            break

        logger.info("Resume compiled to %d pages — compressing (attempt %d)", page_count, attempts + 1)
        attempts += 1

        try:
            compressed_body = await _call_compression(_extract_resume_body(current), api_key)
        except Exception:
            logger.exception("Compression call failed — keeping current LaTeX")
            break

        current = _assemble_resume_latex(compressed_body, preamble)

    return last_known_good, attempts


async def generate_materials(db: AsyncSession, jd_text: str, api_key: str) -> dict:
    personal = (await db.execute(select(PersonalInfo).limit(1))).scalar_one_or_none()
    education = (await db.execute(
        select(Education).where(Education.deleted_at.is_(None)).order_by(Education.id)
    )).scalars().all()
    experience = (await db.execute(
        select(Experience).order_by(Experience.sort_order)
    )).scalars().all()
    projects = (await db.execute(
        select(Project).order_by(Project.sort_order)
    )).scalars().all()
    skills = (await db.execute(
        select(SkillCategory).order_by(SkillCategory.sort_order)
    )).scalars().all()

    template = getattr(personal, "resume_template", None) or "jake"
    if template == "custom":
        custom_preamble = getattr(personal, "custom_preamble", None) or ""
        preamble = custom_preamble if custom_preamble.strip() else _build_preamble(personal, list(education), "jake")
    else:
        preamble = _build_preamble(personal, list(education), template)

    profile_text = _format_profile(
        personal, list(experience), list(projects), list(skills)
    )

    jd_text = _preprocess_jd(jd_text)

    llm = get_llm_client(api_key)

    try:
        call_result = await llm.call_tool(
            model=CLAUDE_MODEL,
            max_tokens=6000,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": profile_text,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            # Explicit XML boundary prevents prompt injection via JD content
                            "text": f"\n\n<job_description>\n{jd_text}\n</job_description>",
                        },
                    ],
                }
            ],
            tool=GENERATE_TOOL,
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        raise ValueError("Generation timed out after 120s.")

    result = {
        **call_result.tool_input,
        "input_tokens": call_result.input_tokens,
        "output_tokens": call_result.output_tokens,
        "cache_read_tokens": call_result.cache_read_tokens,
        "cache_write_tokens": call_result.cache_write_tokens,
    }

    # Assemble full document, then compress if it spills past one page
    if result.get("resume_latex"):
        assembled = _assemble_resume_latex(result["resume_latex"], preamble)
        final_latex, compression_attempts = await _compress_if_needed(assembled, api_key, preamble)
        result["resume_latex"] = final_latex
        result["compression_attempts"] = compression_attempts

    return result


_INSIGHTS_SYSTEM = (
    "You are reviewing Karanveer Sidhu's job search history as a direct advisor. "
    "The input begins with 'Current profile' — the full current state of the profile "
    "(experience descriptions, project descriptions, and skill categories).\n\n"
    "Find the single most actionable pattern across all applications: a technology, skill type, "
    "or experience gap that appears repeatedly in JDs and is absent from the profile.\n\n"
    "IMPORTANT: Read the full profile carefully before identifying any gap. "
    "A technology mentioned anywhere in the profile — experience descriptions, project descriptions, "
    "or skill lists — is NOT a gap. Only flag something as a gap if it genuinely does not appear "
    "anywhere in the current profile.\n\n"
    "Produce four fields. Each field is one thing, stated once, under 25 words.\n\n"
    "Hard rules: no em dashes, no adverbs, no filler phrases. "
    "Name exact technologies. Name specific projects from the current profile. Be precise."
)

_INSIGHTS_TOOL = {
    "name": "candidacy_signal",
    "description": "Structured four-part candidacy signal: headline, observed pattern, gap, action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": (
                    "4-8 words. The memorable conclusion about the dominant pattern. "
                    "Name the specific technology or skill gap that is ABSENT from the current profile. "
                    "Do NOT name any technology that appears in the current profile section. "
                    "Example format: '[Technology] Gap Across Applications', '[Skill] Appearing in Every JD'. "
                    "Wrong: 'Keep applying', 'Good progress'."
                ),
            },
            "observed": {
                "type": "string",
                "description": (
                    "1-2 sentences. What pattern appears across the applications — factual, no advice. "
                    "Under 25 words. Name the specific technologies or experience types appearing."
                ),
            },
            "gap": {
                "type": "string",
                "description": (
                    "1-2 sentences. What specific skill or experience is absent from the CURRENT PROFILE. "
                    "Under 25 words. Name exact technologies from the JDs. "
                    "CRITICAL: If the technology appears anywhere in the 'Current profile' section "
                    "(experience, projects, or skills), it is NOT a gap — pick a different one."
                ),
            },
            "action": {
                "type": "string",
                "description": (
                    "1-2 sentences. One concrete action to close the gap. "
                    "Under 25 words. Name a specific project from the current profile or exact deliverable. "
                    "No em dashes."
                ),
            },
        },
        "required": ["headline", "observed", "gap", "action"],
    },
}


def _extract_gaps(note: str) -> str:
    """Pull just the GAPS section out of a structured strategic note (see the
    GOOD FIT / GAPS / IMPROVEMENT PLAN format in the generation system prompt
    above). The insights synthesis only cares about the gap pattern — sending
    the Good Fit and Improvement Plan sections too was roughly two-thirds of
    each note's tokens spent on text irrelevant to "what gap keeps repeating."
    Falls back to the full note for older, unstructured (prose) notes that
    predate this format.
    """
    match = re.search(r"GAPS\n([\s\S]*?)(?=\n\nIMPROVEMENT PLAN|$)", note)
    if not match:
        return note
    gaps = match.group(1).strip()
    return gaps or note


async def generate_insights(
    job_summaries: list[dict],
    api_key: str,
    profile_context: str | None = None,
) -> dict[str, str | None]:
    """Synthesize a candidacy observation from a list of job application summaries.

    Returns: {"headline": str | None, "observed": str | None, "gap": str | None, "action": str | None}
    Each summary dict should have: title, company (optional), strategic_note (optional),
    description_snippet (optional, first 400 chars of JD for older jobs without a strategic_note).
    profile_context: full profile text (experience/project descriptions + skills) used to avoid
    flagging gaps the candidate has already addressed.
    """
    lines: list[str] = []
    if profile_context:
        lines.append(f"Current profile:\n{profile_context}\n")
    lines.append(f"Applications analyzed: {len(job_summaries)}\n")
    for s in job_summaries:
        entry = f"- {s.get('title') or 'Unknown role'}"
        if s.get("company"):
            entry += f" at {s['company']}"
        lines.append(entry)
        if s.get("strategic_note"):
            lines.append(f"  Gaps: {_extract_gaps(s['strategic_note'])}")
        elif s.get("description_snippet"):
            lines.append(f"  JD excerpt: {s['description_snippet']}")

    llm = get_llm_client(api_key)
    try:
        call_result = await llm.call_tool(
            model=CLAUDE_MODEL,
            max_tokens=400,
            system=_INSIGHTS_SYSTEM,
            messages=[{"role": "user", "content": "\n".join(lines)}],
            tool=_INSIGHTS_TOOL,
            timeout=30.0,
        )
        return {
            "headline": call_result.tool_input.get("headline") or None,
            "observed":  call_result.tool_input.get("observed")  or None,
            "gap":       call_result.tool_input.get("gap")       or None,
            "action":    call_result.tool_input.get("action")    or None,
        }
    except Exception:
        return {"headline": None, "observed": None, "gap": None, "action": None}
