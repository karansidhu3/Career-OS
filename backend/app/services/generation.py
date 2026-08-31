import asyncio
from difflib import SequenceMatcher
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
GENERATION_VERSION = "original-v1-qg-local-recovery"

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
    replacements = {
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
        "&": r"\&", "%": r"\%", "#": r"\#", "$": r"\$", "_": r"\_",
    }
    return re.sub(r"[\\{}&%#$_]", lambda match: replacements[match.group()], str(s))


def _build_education_latex(education: list) -> str:
    if not education:
        return ""
    lines = ["%-----------EDUCATION-----------------",
             r"\section{Education}",
             r"  \resumeSubHeadingListStart"]
    for edu in education:
        degree = _tex(edu.degree or "")
        # Avoid headings such as "BSc Computer Science, Computer Science" when
        # the stored degree already contains the field name.
        if edu.field and edu.field.casefold() not in (edu.degree or "").casefold():
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
    % \resumeSubheading{Exact profile company}{Date}{Profile role}{Location or empty}
    %   \resumeItemListStart
    %     \item \small{bullet text}
    %   \resumeItemListEnd
  \resumeSubHeadingListEnd

%-----------PROJECTS — reorder by relevance, include 2-3-----------------
\section{Projects}
  \resumeSubHeadingListStart
    % \projectSubheading{CareerOS-supplied exact heading}{Dates}{Tech Stack}{}{github_url}
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

_SYSTEM_PROMPT_BODY = """Write a one-page résumé for two audiences:

  • A recruiter, who needs to understand the candidate's relevant work quickly
  • A hiring manager, who needs credible technical depth worth discussing in an interview

For each selected project, Bullet 1 establishes recruiter clarity and Bullet 2 establishes
engineering credibility. Both must be understandable, specific, and grounded.

Treat the supplied candidate profile and job description as the source of the candidate's
identity, experience, target role, and evidence. Do not rely on assumptions outside them.

━━━ PLAN BEFORE YOU WRITE ━━━

STEP 0 — Rank supported evidence before writing.

Priority A: recruiter-legible scope or outcome, such as people or workflows served,
manual work replaced, meaningful data volume, or a product result.
Priority B: engineering proof, such as a relevant latency, recovery, reliability,
contention, or data-scale measurement.
Priority C: supporting inventory, such as test, endpoint, file, migration, schema,
or line counts.

Prefer one coherent metric story to unrelated numbers. Use Priority C only when the job
values it and stronger evidence cannot explain the work. A decision, failure boundary, or
verified property can be stronger than a weak metric. Preserve qualifiers exactly: controlled
is not production, local is not deployed, and intended use is not verified use. Include a
number only when its absence would reduce understanding of fit.

STEP 1 — Classify the JD internally, using the posting rather than company reputation.
Choose one primary engineering environment and role family; add a secondary only when the
posting truly combines two contexts. Do not display classifications.

Environment → evidence to emphasize:
  • Product/startup → end-to-end ownership, user workflows, shipping, deployment, pragmatic tradeoffs
  • Large-scale technology → performance, failure handling, system boundaries, testing, collaboration
  • Infrastructure/developer tools → architecture, observability, retries, recovery, APIs, automation
  • Enterprise/regulated → transactions, authorization, auditability, validation, data integrity, process
  • Consulting/client delivery → scoped ownership, requirements, integration, stakeholders, delivery
  • Research/education/public operations → data stewardship, documentation, privacy, support, maintainability

Role family → evidence to emphasize:
  • Backend → APIs, data, transactions, authentication, reliability
  • Frontend → workflows, interactions, state, accessibility, performance
  • Full stack → frontend/backend integration, validation, persistence
  • AI/data → model integration, ingestion, retrieval, evaluation, data quality
  • Infrastructure/platform → asynchronous systems, cloud, observability, deployment, recovery
  • Embedded/hardware/networking → protocols, devices, resource constraints, field reliability
  • Support/implementation/operations → debugging, documentation, incidents, configuration, user support

Identify the three evidence signals that make the candidate credible for this role and use
them to govern selection and emphasis.

STEP 2 — Identify the 3-4 highest-weight requirements: required duties and technologies
first, then repeated terms and title signals.

STEP 3 — For each source, silently identify: (1) a recruiter fact — what it is, who or
what it is for, and relevant scope/outcome; (2) an engineering proof — a supported decision,
mechanism, constraint, failure boundary, implementation, or verified property; and (3) one
best metric story, if stronger than a non-numeric result. Do not force a fixed narrative or
rejected alternative.

STEP 4 — Select the smallest complementary project set covering the highest-weight
requirements. Default to exactly 3; use 2 only when a third adds no distinct required or
repeated responsibility. Rank by direct role relevance, proof of primary work, recruiter-
legible value, engineering depth, and evidence not already covered. Order strongest first.
Do not select a fourth project; only CareerOS may later admit one without displacing relevant
Skills, experience evidence, or a stronger project.

━━━ PROJECT HEADINGS ━━━

CareerOS supplies every heading as [PROJECT BRAND] | [PROFILE PROJECT NAME]. Copy it exactly;
never rename it, generate a descriptor, or alter its emphasis for a JD.

━━━ BULLET STRUCTURE ━━━

Every project gets exactly 2 bullets. They serve different audiences and must be written
in this order.

BULLET 1 — PROJECT SALE (recruiter audience)

Write: [what it is/does] + [who or what it is for] + [strongest relevant supported
outcome, scope, or differentiator]. A recruiter must understand the project without its
technology line or Bullet 2; lead with the product, workflow, or problem, not architecture.

Preserve status exactly: “used by” and “serves” require verified use; “deployed” requires
a deployed capability; “production” requires explicit production operation. Intended or
local work remains intended or local; a controlled benchmark remains controlled. Do not infer
users, adoption, impact, completed integrations, or production scale from architecture.

BULLET 2 — ENGINEERING PROOF (hiring manager audience)

Write: [specific component, decision, or mechanism] + [documented constraint, tradeoff,
or failure boundary] + [supported result or technical property]. Prefer a concrete subject
such as a transaction boundary, state machine, queue, schema, recovery path, authorization
policy, ingestion gate, or benchmark harness. It should invite a useful follow-up question.

Do not claim a previous approach, rejected alternative, or failure unless documented. One
coherent metric story is enough; a defensible decision or verified property can be stronger
than an unrelated number. Technologies alone are not proof unless they explain behaviour,
a decision, a constraint, or a result.

━━━ OWNERSHIP ━━━

Make personal scope clear in at least one bullet per experience entry; other bullets may
focus on technical evidence. For independent work, use direct ownership language. For team
work, name the owned workflow or component and documented team size once when useful. Use
“Led” only for documented technical direction or coordination, not component ownership alone.
Never claim whole-product ownership, leadership, authority, mentorship, or team scope not
supported by the profile; do not hide a specific contribution behind “contributed to.”

━━━ CLAUSE CONTROL ━━━

Each bullet tells one coherent evidence story. Keep an extra clause only when it adds a
supported user/problem, replaced workflow, constraint, result, or required qualifier. Remove
restatement, generic purpose, repeated technology/metric/scope, or a second unrelated claim.
Words such as “which,” “allowing,” “to support,” and “resulting in” are allowed when they are
the clearest way to add information. When shortening, cut redundancy before context, rationale,
qualifiers, or results.

━━━ BULLET DENSITY AND WRITING STYLE ━━━

Write complete, natural, information-dense sentences: target 18-28 words, permit shorter
complete high-value bullets, never exceed 32, and never truncate needed context to hit a count.
One bullet may contain one product/result story, decision/constraint/result story, scoped
contribution, or related metric story. When long, remove filler, repetition, secondary tools,
or unrelated metrics before context, qualifiers, central reasoning, or outcome.

Use direct accurate verbs; avoid adjacent repetition when natural, but never use an inflated
synonym for variety. Do not open with “Worked on,” “Helped,” “Assisted,” “Participated in,”
“Was responsible for,” “Contributed to,” “Supported,” or “Collaborated on.” No first person or
contractions. Prefer clear technical language to fragments.

━━━ EXPERIENCE SECTION ━━━

Include every active technical experience entry in reverse chronological order; tailor bullets,
not employment order. Copy company, role, dates, and location exactly. Never make a product the
employer or invent title, seniority, employment type, or leadership; a product may appear in a
bullet. Use 2 bullets by default and a third only for distinct, high-value evidence.

Emphasize backend APIs/data/transactions/reliability; AI/data ingestion, retrieval, evaluation,
and quality; full-stack workflows, integration, validation, and persistence; infrastructure
asynchronous systems, deployment, security, observability, and recovery; and collaborative work
scoped ownership, process, testing, documentation, and stakeholders.

━━━ PROJECTS AND TECHNOLOGY LINES ━━━

Include selected_projects in order. Each has its exact CareerOS heading, exactly 2 approved
bullets, and a 3-6 technology line ordered by JD relevance. Include only technologies explicitly
connected to that project; do not assign a candidate-wide skill to a project. Mention a technology
in a bullet only when central to the evidence. Prefer a shorter line to irrelevant keywords.

━━━ SKILLS SECTION ━━━

Build Skills from the complete profile, including stored Skills, project and experience evidence,
and explicit education/coursework. A related framework, degree, or concept does not prove an exact
technology. Include supported required/repeated JD terms, relevant demonstrated support, and useful
architecture concepts; exclude unsupported tools, unrelated items, soft skills, generic concepts,
and needless aliases. Use exact truthful JD terms and order categories/items by relevance. Use
recruiter-legible existing categories rather than creating one for an isolated term. Skills are ATS
evidence, not leftover space: preserve any category containing a supported required/repeated term.

━━━ ATS KEYWORD ALIGNMENT ━━━

Rank JD terms: required tools/platforms, repeated responsibilities, required architecture/testing/
security/delivery concepts, then preferred terms. Mirror every supported required or repeated term
that materially improves the match; do not target a count. Put explicit skills in Skills, project
tools in technology lines, and central responsibilities/tools in bullets. Do not force a term that
is already clear elsewhere. For a missing exact requirement, surface the closest supported evidence
but do not present it as the requested tool; preserve the exact gap for analysis. Never turn bullets
into keyword lists.

━━━ ONE-PAGE CONTENT BUDGET ━━━

Write to one page, then let PDF compilation determine actual fit. Default: every technical
experience entry with 2 bullets; 2-3 selected projects with 2 bullets; every materially relevant
Skills category. Add a third experience bullet only for distinct, otherwise unavailable evidence.
Do not preemptively omit strong evidence or fill space with filler.

Preserve, in order: current/relevant experience, higher-ranked projects, required/repeated Skills,
distinct engineering evidence, optional third bullets, then lower-relevance details. Reduce in order:
filler/redundancy; overlong bullets without losing core evidence; optional third bullets; the lowest-
ranked third project if core coverage remains; then Skills neither requested nor demonstrated by selected
evidence. Never remove relevant Skills to preserve a lower-ranked project.

━━━ RÉSUMÉ LANGUAGE RULES ━━━

Use direct, specific language naming the product, component, workflow, decision, scope, or
verified property. Avoid vague/promo filler: “various technologies,” unexplained improvement,
“demonstrated,” “showcased,” “leveraging,” “harnessing,” “spearheading,” “passionate about,”
“strong foundation,” “proven track record,” empty intensifiers, or unsupported “robust,”
“scalable,” and “production-grade.” Scope terms such as “end-to-end,” “modular,” “reusable,”
“full stack,” and “across” are allowed only when concrete and supported.

Non-numeric verified properties are valid evidence: prevented invalid state, atomic rollback,
authorization/isolation enforcement, documented recovery, preserved history, or a documented
manual/synchronous replacement. When using “support,” name the real output or operation. “Owned”
or “led” requires ownership; “Architected” requires an architecture decision. Never inflate status,
adoption, ownership, or evidence.

━━━ COVER LETTER ━━━

MINDSET AND VOICE

Apply stored cover_letter_voice; otherwise write direct, conversational, professional first-person
prose: specific over persuasive, confident but grounded. Write like an engineer discussing real
work, not a résumé inventory.

Write exactly 3 paragraphs, about 160-220 words:
  1. 2-3 sentences: a concrete JD responsibility, technology, product area, or problem and its
     connection to the candidate's direction. Do not open with “I,” name a project, or invent
     company architecture, scale, customers, or priorities.
  2. 4-5 sentences: exactly one project, named once; tell its documented problem/constraint,
     decision, why it fit, supported result/property, and transfer to this role. Use at most two
     related metrics. No other project, test inventory, invented prior approach/failure, or stack list.
  3. 1-2 sentences: current availability and a technical-conversation invitation, without generic
     enthusiasm, gratitude, or repeated fit summary.

Prefer active voice when the candidate acted; passive is allowed when the result matters more.
Vary rhythm naturally, never mechanically or with fragments. Do not start consecutive sentences with
“I,” or begin one “As a,” “In my,” “With my,” or “Having worked on.” Avoid “Additionally,”
“Furthermore,” “Moreover,” and “In conclusion.” Contractions may follow the stored voice.

Avoid stock openings/enthusiasm, generic company praise, unsupported self-assessment, corporate
phrasing, and empty intensifiers. Specifically avoid “I am excited/thrilled/passionate/eager,”
“I am writing to express my interest,” “great fit/ideal candidate,” “I am confident,” “proven track
record,” “team player/fast learner/self-starter,” “leverage/utilize/apply,” “make an impact,”
“contribute to the team,” “hit the ground running,” “demonstrated/showcased/spearheaded,” and generic
closes such as “I look forward to hearing from you” or “Thank you for your consideration.” Never use
an em dash. Every substantive sentence must be role-, evidence-, or proof-story-specific; the close is
exempt.

━━━ FIT SCORE ━━━

Score current interview readiness, not prestige, enthusiasm, or application quality. Weight, in
order: primary responsibilities; required tools/domains; credible transferable evidence; eligibility
(level, education, location, work authorization); then preferred qualifications. Transferable proof
is not exact-tool experience. Do not materially penalize a nice-to-have, a tool difference with strong
underlying evidence, or inflated years language for an otherwise early-career role. Penalize missing
eligibility, a primary responsibility with no evidence, high-risk required-domain absence, or unsupported
seniority.

1-3: essential responsibility/eligibility absent. 4-5: meaningful core gaps despite transferability.
6-7: credible for much of the role with screening-relevant gaps. 8-9: nearly all core responsibilities
directly supported; only secondary/preferred/learnable gaps. 10: exceptional direct match with no
meaningful gap, used rarely. Keep analysis consistent with the score.

━━━ STRATEGIC ANALYSIS ━━━

Generate in exactly this format. No introductory or concluding prose.

GOOD FIT
• [concise, specific match between the JD and the strongest profile evidence]
• [second genuinely distinct match]

GAPS
• [exact missing technology, domain, workflow, or experience required by the JD]
• [second genuinely distinct gap]
• [third only when materially important]

IMPROVEMENT PLAN
• [one concrete and realistic action addressing the most important gap]
• [second action only when it addresses a different meaningful gap]

VISIBLE WRITING RULES:

Use 1-2 GOOD FIT, 1-3 GAPS, and 1-2 IMPROVEMENT PLAN bullets. Each is one natural,
plain-language sentence, normally 8-18 words and never over 24, naming one relevant
technology, project, experience, or domain. No citations, source labels, audit language, or
“Strong match,” “Great fit,” or “Consider improving.”

Before declaring a gap, search the complete profile. Every fit maps one real JD requirement to
the strongest single supported source; preserve local/deployed/production/intended/verified/
controlled status. Gaps are genuine missing requirements, not an entire area with evidence or a
nice-to-have presented as critical; group related missing tools. Improvements are concise, specific,
realistic, and not already demonstrated. For a fundamentally misaligned role, concise application
strategy may replace an artificial side project.

━━━ FINAL SELF-REVIEW ━━━

Silently verify and fix only material failures; do not output review notes. Confirm: every claim,
status qualifier, heading, date, location, project order, and required term is accurate; project
selection is complementary; Bullet 1 provides recruiter clarity and Bullet 2 interviewable proof;
each experience entry establishes accurate personal scope; bullets are complete, non-generic,
grounded, and within the approved density; and relevant Skills are retained.

Confirm the cover letter is 3 paragraphs/160-220 words, JD-specific in paragraph 1, one named
project/one grounded story/two metrics maximum in paragraph 2, and free of a second project,
test inventory, unsupported company detail, banned language, or em dashes. Confirm analysis has
grounded concise fit/gap/action bullets in the required counts and lengths.

RESUME BODY TEMPLATE (output only these variable sections — do not include \\documentclass,
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
                    "Exact project identifiers from the supplied profile, ordered from "
                    "strongest overall job match to weakest. Select exactly 3 by default. "
                    "Select 2 only when a third project would add no distinct evidence for "
                    "a required or repeatedly emphasized job responsibility."
                ),
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 3,
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
        "=== CANDIDATE PROFILE — FACTUAL SOURCE ===",
        "Use this profile as factual evidence, not as prewritten résumé prose.",
        "Select evidence by job relevance and the approved evidence-priority rules. You may combine",
        "multiple supported facts into clearer, stronger language, but must not invent, inflate, or",
        "copy raw profile sentences merely because they exist.",
        "Project and experience descriptions may contain useful product context, technical decisions,",
        "constraints, metrics, status qualifiers, and ownership boundaries. Extract only the evidence",
        "that materially strengthens this application.\n",
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
                lines.append("  SOURCE MATERIAL — factual evidence, not copy-ready résumé prose:")
                lines.append(f"  {exp.description}")
        lines.append("")

    if projects:
        lines.append("PROJECTS")
        for i, proj in enumerate(projects, 1):
            end = proj.end_date or "Present"
            gh = f" — GitHub: {proj.github_url}" if getattr(proj, "github_url", None) else ""
            lines.append(f"[{i}] {proj.name} ({proj.start_date} – {end}){gh}")
            lines.append(
                f"  REQUIRED RESUME HEADING — copy exactly: {_project_heading(proj)}"
            )
            if proj.description:
                lines.append("  SOURCE MATERIAL — factual evidence, not copy-ready résumé prose:")
                lines.append(f"  {proj.description}")
        lines.append("")

    if skills:
        lines.append("SKILLS")
        for s in skills:
            lines.append(f"{s.category}: {', '.join(s.items or [])}")

    return "\n".join(lines)


def _project_brand(project) -> str | None:
    """Return the explicit brand stored as the description's first standalone line."""
    description = str(getattr(project, "description", "") or "")
    first_line = next(
        (line.strip().strip("#*") for line in description.splitlines() if line.strip()),
        "",
    )
    if not first_line or len(first_line) > 50 or len(first_line.split()) > 5:
        return None
    if first_line.casefold() in {
        "description",
        "project summary",
        "status and users",
        "what it is",
    }:
        return None
    if re.search(r"[.!?:;]$", first_line):
        return None
    return first_line


def _project_heading(project) -> str:
    """Build the stable project heading owned by CareerOS, not the model."""
    name = str(getattr(project, "name", "") or "").strip()
    brand = _project_brand(project)
    if not brand or brand.casefold() == name.casefold():
        return name
    return f"{brand} | {name}"


def _project_key(value: str) -> str:
    plain = _latex_to_plain(str(value or "")).split("|", 1)[0]
    return re.sub(r"[^a-z0-9]+", "", plain.casefold())


def _resolve_selected_projects(selected_projects: list[str], projects: list) -> list:
    """Resolve model-selected identifiers against profile names, brands, or headings."""
    aliases: dict[str, object] = {}
    for project in projects:
        for value in (
            str(getattr(project, "name", "") or ""),
            _project_brand(project) or "",
            _project_heading(project),
        ):
            key = _project_key(value)
            if key:
                aliases[key] = project

    resolved: list = []
    seen: set[int] = set()
    for identifier in selected_projects:
        project = aliases.get(_project_key(identifier))
        if project is None:
            raise ValueError(f"Selected project is not present in the profile: {identifier}")
        marker = id(project)
        if marker in seen:
            raise ValueError(f"Selected project was repeated: {identifier}")
        seen.add(marker)
        resolved.append(project)
    return resolved


def _project_heading_spans(body_latex: str) -> list[tuple[int, int]]:
    """Return first-argument spans for every project heading in the resume body."""
    body = _extract_resume_body(body_latex)
    marker = r"\projectSubheading{"
    spans: list[tuple[int, int]] = []
    cursor = 0
    while True:
        marker_start = body.find(marker, cursor)
        if marker_start == -1:
            return spans
        content_start = marker_start + len(marker)
        depth = 1
        index = content_start
        while index < len(body) and depth:
            if body[index] == "{" and (index == 0 or body[index - 1] != "\\"):
                depth += 1
            elif body[index] == "}" and (index == 0 or body[index - 1] != "\\"):
                depth -= 1
            index += 1
        if depth:
            return spans
        spans.append((content_start, index - 1))
        cursor = index


def _apply_project_headings(
    body_latex: str,
    selected_projects: list[str],
    projects: list,
) -> str:
    """Replace model-written project headings with profile-owned canonical headings."""
    body = _extract_resume_body(body_latex)
    spans = _project_heading_spans(body)
    resolved = _resolve_selected_projects(selected_projects, projects)
    if len(spans) > len(resolved):
        raise ValueError("Resume contains more project entries than selected projects")

    replacements = [
        _escape_latex_bullet(_project_heading(project))
        for project in resolved[:len(spans)]
    ]
    for (start, end), replacement in reversed(list(zip(spans, replacements))):
        body = body[:start] + replacement + body[end:]
    return body


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


# ── Editorial acceptance gate ────────────────────────────────────────────────

_PASSIVE_INVENTORY_PATTERNS = (
    re.compile(r"^(?:the\s+)?(?:application|platform|project|solution|system)\s+(?:is|was)\b", re.IGNORECASE),
    re.compile(r"\b(?:is|was)\s+(?:built|developed|implemented)\s+using\b", re.IGNORECASE),
    re.compile(r"\bserving\s+as\s+the\s+authoritative\s+source\s+of\s+truth\b", re.IGNORECASE),
)

_BULLET_STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "using", "that", "this", "through",
}


def _balanced_brace_contents(text: str, marker: str) -> list[str]:
    """Extract the balanced final argument following a literal LaTeX marker."""
    values: list[str] = []
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start == -1:
            return values
        start += len(marker)
        depth = 1
        index = start
        while index < len(text) and depth:
            if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
                depth += 1
            elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
                depth -= 1
            index += 1
        if depth == 0:
            values.append(text[start:index - 1].strip())
            cursor = index
        else:
            return values


def _latex_to_plain(text: str) -> str:
    """Collapse the small LaTeX subset permitted inside generated bullets."""
    plain = str(text or "")
    plain = re.sub(r"\\href\{[^{}]*\}\{([^{}]*)\}", r"\1", plain)
    # Unwrap simple formatting commands repeatedly so nested text survives.
    for _ in range(4):
        updated = re.sub(r"\\(?:textbf|textit|emph|small)\{([^{}]*)\}", r"\1", plain)
        if updated == plain:
            break
        plain = updated
    plain = (
        plain.replace(r"\&", "&")
        .replace(r"\%", "%")
        .replace(r"\#", "#")
        .replace(r"\_", "_")
        .replace(r"\$", "$")
    )
    plain = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", plain)
    plain = plain.replace("{", " ").replace("}", " ").replace("~", " ")
    return re.sub(r"\s+", " ", plain).strip()


def _resume_item_blocks(body: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    cursor = 0
    start_marker = r"\resumeItemListStart"
    end_marker = r"\resumeItemListEnd"
    while True:
        start = body.find(start_marker, cursor)
        if start == -1:
            return blocks
        end = body.find(end_marker, start + len(start_marker))
        if end == -1:
            return blocks
        blocks.append(_balanced_brace_contents(body[start:end], r"\item \small{"))
        cursor = end + len(end_marker)


def _resume_item_spans(body: str) -> list[tuple[int, int, str]]:
    """Return the source spans and contents of every generated resume bullet."""
    marker = r"\item \small{"
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        marker_start = body.find(marker, cursor)
        if marker_start == -1:
            return spans
        content_start = marker_start + len(marker)
        depth = 1
        index = content_start
        while index < len(body) and depth:
            if body[index] == "{" and (index == 0 or body[index - 1] != "\\"):
                depth += 1
            elif body[index] == "}" and (index == 0 or body[index - 1] != "\\"):
                depth -= 1
            index += 1
        if depth:
            return spans
        content_end = index - 1
        spans.append((content_start, content_end, body[content_start:content_end]))
        cursor = index


_BULLET_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./'-]*")
_INCOMPLETE_ENDINGS = {
    "a", "an", "and", "as", "at", "because", "by", "for", "from", "in",
    "into", "of", "on", "or", "the", "to", "using", "via", "with", "without",
}
_LOW_VALUE_BULLET_TERM = r"(?:comprehensive|robust|scalable|modular|reusable|successfully)"
_SAFE_TRAILING_CLAUSE = re.compile(
    r"[,;]\s+(?=(?:which|while|because|after|before|using|enabling|allowing|"
    r"reducing|replacing|supporting|providing|ensuring|preserving|preventing|"
    r"improving|eliminating|resulting)\b)",
    re.IGNORECASE,
)


def _bullet_word_count(text: str) -> int:
    return len(_BULLET_WORD_RE.findall(_latex_to_plain(text)))


def _escape_latex_bullet(text: str) -> str:
    """Escape locally recovered plain text for safe insertion into a bullet."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _remove_low_value_bullet_words(text: str) -> str:
    """Remove prompt-banned filler without leaving broken lists or conjunctions."""
    cleaned = re.sub(
        rf"\b{_LOW_VALUE_BULLET_TERM}\b\s*,\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        rf",\s*\b{_LOW_VALUE_BULLET_TERM}\b(?=\s+[A-Za-z0-9])",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        rf"\b{_LOW_VALUE_BULLET_TERM}\b\s+(?:and|or)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        rf"\b(?:and|or)\s+{_LOW_VALUE_BULLET_TERM}\b\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        rf"\b{_LOW_VALUE_BULLET_TERM}\b\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def _complete_bullet_candidate(text: str, *, max_words: int = 36) -> str | None:
    candidate = re.sub(r"\s+", " ", text).strip().rstrip(" ,;:-")
    words = _BULLET_WORD_RE.findall(candidate)
    if not 12 <= len(words) <= max_words:
        return None
    if words[-1].casefold() in _INCOMPLETE_ENDINGS:
        return None
    return candidate if re.search(r"[.!?]$", candidate) else candidate + "."


def _shorten_overlong_bullet(raw_latex: str, *, max_words: int = 36) -> str | None:
    """Shorten one bullet without inventing or slicing through an arbitrary phrase.

    Prefer removing prompt-banned filler while preserving the complete sentence. If
    that is insufficient, retain a complete sentence or the longest complete leading
    clause. Returning ``None`` is intentional: unsafe prose is left for the existing
    acceptance failure rather than being truncated into a fragment.
    """
    plain = _latex_to_plain(raw_latex)
    if _bullet_word_count(plain) <= max_words:
        return None

    without_filler = _remove_low_value_bullet_words(plain)
    without_filler = re.sub(r"\bin order to\b", "to", without_filler, flags=re.IGNORECASE)
    filler_candidate = _complete_bullet_candidate(without_filler, max_words=max_words)
    if filler_candidate:
        return _escape_latex_bullet(filler_candidate)

    prefixes: list[str] = []
    for match in re.finditer(r"(?<=[.!?])\s+", without_filler):
        prefixes.append(without_filler[:match.start()])
    for match in _SAFE_TRAILING_CLAUSE.finditer(without_filler):
        prefixes.append(without_filler[:match.start()])

    candidates = [
        candidate
        for prefix in prefixes
        if (candidate := _complete_bullet_candidate(prefix, max_words=max_words))
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda item: len(_BULLET_WORD_RE.findall(item)))
    return _escape_latex_bullet(best)


def _recover_overlong_bullets(body_latex: str) -> tuple[str, list[str]]:
    """Apply free, deterministic recovery to overlong bullets and report actions."""
    body = _extract_resume_body(body_latex)
    replacements: list[tuple[int, int, str]] = []
    actions: list[str] = []
    for index, (start, end, raw) in enumerate(_resume_item_spans(body), start=1):
        before = _bullet_word_count(raw)
        if before <= 36:
            continue
        replacement = _shorten_overlong_bullet(raw)
        if replacement is None:
            continue
        after = _bullet_word_count(replacement)
        replacements.append((start, end, replacement))
        actions.append(f"shortened_bullet:{index}:{before}->{after}")

    for start, end, replacement in reversed(replacements):
        body = body[:start] + replacement + body[end:]
    return body, actions


def _recover_local_quality_defects(body_latex: str) -> tuple[str, list[str]]:
    """Fix harmless visible defects before considering any paid editorial repair."""
    body = _extract_resume_body(body_latex)
    replacements: list[tuple[int, int, str]] = []
    actions: list[str] = []

    for index, (start, end, raw) in enumerate(_resume_item_spans(body), start=1):
        replacement = raw.strip()
        plain = _latex_to_plain(replacement)
        words = _BULLET_WORD_RE.findall(plain)

        if (
            words
            and not re.search(r"[.!?]$", plain)
            and words[-1].casefold() not in _INCOMPLETE_ENDINGS
        ):
            replacement += "."
            plain += "."
            actions.append(f"added_punctuation:{index}")

        before = _bullet_word_count(replacement)
        if before > 36:
            shortened = _shorten_overlong_bullet(replacement, max_words=36)
            if shortened is not None:
                replacement = shortened
                after = _bullet_word_count(replacement)
                actions.append(f"shortened_bullet:{index}:{before}->{after}")

        if replacement != raw:
            replacements.append((start, end, replacement))

    for start, end, replacement in reversed(replacements):
        body = body[:start] + replacement + body[end:]
    return body, actions


_PROFILE_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20",
}


def _numeric_claims(text: str, *, include_written_counts: bool = False) -> set[str]:
    """Return normalized numeric claims, accepting common equivalent spellings."""
    plain = _latex_to_plain(text).casefold()
    claims: set[str] = set()
    pattern = re.compile(
        r"(?:(?P<qualifier>more\s+than|over|at\s+least)\s+)?"
        r"(?P<number>\d+(?:[.,]\d+)?)"
        r"(?P<suffix>%|\+)?"
    )
    for match in pattern.finditer(plain):
        number = match.group("number").replace(",", "")
        suffix = match.group("suffix") or ""
        if match.group("qualifier") and suffix != "%":
            suffix = "+"
        claims.add(number + suffix)

    if include_written_counts:
        count_noun = (
            r"person|people|member|employee|user|event|workflow|application|project|"
            r"service|function|table|queue|bucket|endpoint|test|trial|row|record|"
            r"state|transition|role|permission|developer|engineer"
        )
        for word, number in _PROFILE_NUMBER_WORDS.items():
            if re.search(rf"\b{word}(?:-|\s)+(?:{count_noun})s?\b", plain):
                claims.add(number)
    return claims


def _bullet_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.-]+", text.casefold())
        if token not in _BULLET_STOPWORDS and len(token) > 1
    }


def _bullet_similarity(left: str, right: str) -> tuple[float, float]:
    left_terms, right_terms = _bullet_terms(left), _bullet_terms(right)
    token_overlap = (
        len(left_terms & right_terms) / len(left_terms | right_terms)
        if left_terms and right_terms else 0.0
    )
    sequence_overlap = SequenceMatcher(None, left.casefold(), right.casefold()).ratio()
    return token_overlap, sequence_overlap


def _resume_quality_errors(body_latex: str, profile_text: str) -> list[str]:
    """Reject visible editorial defects before a resume can be stored as generated.

    This deliberately checks only high-confidence failure modes. Nuanced editorial
    judgment stays with the model; fragments, passive stack inventories, fabricated
    numbers, duplicate bullets, and malformed section structure do not.
    """
    body = _extract_resume_body(body_latex)
    errors: list[str] = []
    blocks = _resume_item_blocks(body)
    bullets = [_latex_to_plain(item) for block in blocks for item in block]

    if not blocks:
        errors.append("no resume bullet lists were found")
        return errors
    if not bullets:
        errors.append("no resume bullets were found")
        return errors

    profile_numbers = _numeric_claims(profile_text, include_written_counts=True)
    for index, bullet in enumerate(bullets, start=1):
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+#./'-]*", bullet)
        if not 8 <= len(words) <= 36:
            errors.append(f"bullet {index} has {len(words)} words; expected 8-36")
        if bullet and not re.search(r"[.!?]$", bullet):
            errors.append(f"bullet {index} does not end with sentence punctuation")
        if any(pattern.search(bullet) for pattern in _PASSIVE_INVENTORY_PATTERNS):
            errors.append(f"bullet {index} is a passive project or technology inventory")
        unsupported_numbers = sorted(_numeric_claims(bullet) - profile_numbers)
        if unsupported_numbers:
            errors.append(
                f"bullet {index} contains numbers absent from the profile: {', '.join(unsupported_numbers)}"
            )

    bullet_offset = 0
    for block_index, block in enumerate(blocks, start=1):
        plain_block = [_latex_to_plain(item) for item in block]
        for left_index, left in enumerate(plain_block):
            for right_index, right in enumerate(plain_block[left_index + 1:], start=left_index + 1):
                token_overlap, sequence_overlap = _bullet_similarity(left, right)
                if token_overlap >= 0.45 and sequence_overlap >= 0.72:
                    errors.append(
                        f"entry {block_index} global bullets {bullet_offset + left_index + 1} "
                        f"and {bullet_offset + right_index + 1} are semantically repetitive"
                    )
        bullet_offset += len(block)

    experience = body.partition(r"\section{Experience}")[2].partition(r"\section{Projects}")[0]
    projects = body.partition(r"\section{Projects}")[2].partition(r"\section{Skills}")[0]
    experience_blocks = _resume_item_blocks(experience)
    project_blocks = _resume_item_blocks(projects)
    if not experience_blocks:
        errors.append("experience section contains no entries")
    if len(project_blocks) < 2:
        errors.append("projects section contains fewer than two entries")
    for index, block in enumerate(experience_blocks, start=1):
        if not 2 <= len(block) <= 3:
            errors.append(f"experience entry {index} has {len(block)} bullets; expected 2-3")
    for index, block in enumerate(project_blocks, start=1):
        if len(block) != 2:
            errors.append(f"project entry {index} has {len(block)} bullets; exactly 2 required")
    return errors


_QUALITY_REPAIR_SYSTEM = r"""You are repairing only the variable LaTeX body of a one-page
software-engineering resume. The supplied candidate profile is the sole source of atomic facts.
Preserve strong content and the selected project set, but rewrite every defect listed by the
quality gate. Never copy a raw profile sentence verbatim merely to fill a bullet.

Every experience and project bullet must be a complete, polished resume sentence ending in
punctuation. Experience entries require 2-3 distinct bullets. Every project requires exactly
2 complementary bullets: first, a recruiter-legible product or outcome statement; second, a
specific engineering decision, constraint, failure boundary, or implementation that invites
technical discussion. Target 16-24 words per bullet and keep every bullet at 30 words or fewer;
the validator's ceiling is 32, not a writing target. Count the visible words before
returning the document. Never output a project name alone, a passive technology inventory, two
paraphrases of the same fact, an unsupported number, or a generic README description. Use only
supported technologies, metrics, ownership, and outcomes.

Return only Experience, Projects, and Skills sections using the supplied LaTeX command structure.
Do not output a preamble, heading, education section, document wrapper, or explanation.""" + LATEX_TEMPLATE

_QUALITY_REPAIR_TOOL = {
    "name": "repair_resume_body",
    "description": "A corrected, evidence-backed LaTeX resume body.",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume_latex": {
                "type": "string",
                "description": "Corrected Experience, Projects, and Skills LaTeX sections only.",
            }
        },
        "required": ["resume_latex"],
    },
}

_TARGETED_QUALITY_REPAIR_SYSTEM = r"""You are repairing only the defective bullets in a
software-engineering resume. The candidate profile is the sole source of facts. Return a
replacement only for a bullet that must change to resolve a listed quality-gate defect.
Preserve every passing bullet exactly as written.

Each replacement must be the LaTeX-safe content inside \item \small{...}, not the surrounding
item command. It must be one complete sentence, normally 18-28 words and never more than
32 words. Use only supported technologies, metrics, ownership, outcomes, and operational
status. Do not introduce a new project, heading, technology line, or section. For a duplicate
pair, replace only the weaker bullet and preserve the stronger one.

Return no full resume, explanation, or unchanged bullets."""

_TARGETED_QUALITY_REPAIR_TOOL = {
    "name": "repair_resume_bullets",
    "description": "Targeted replacements for defective resume bullets only.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "bullet_index": {
                            "type": "integer",
                            "description": "One-based global bullet index in the supplied resume body.",
                            "minimum": 1,
                        },
                        "replacement_latex": {
                            "type": "string",
                            "description": "Replacement content inside the bullet's LaTeX braces.",
                        },
                    },
                    "required": ["bullet_index", "replacement_latex"],
                },
            },
        },
        "required": ["repairs"],
    },
}


def _quality_errors_require_full_body_repair(errors: list[str]) -> bool:
    """Reserve whole-body rewriting for malformed section or entry structure."""
    return any(
        not (error.startswith("bullet ") or "global bullets" in error)
        for error in errors
    )


def _apply_targeted_bullet_repairs(body_latex: str, repairs: list[dict]) -> str:
    """Apply model replacements without allowing passing bullets to change."""
    body = _extract_resume_body(body_latex)
    spans = _resume_item_spans(body)
    replacements: list[tuple[int, int, str]] = []
    seen: set[int] = set()

    for repair in repairs:
        index = int(repair.get("bullet_index", 0))
        replacement = str(repair.get("replacement_latex", "") or "").strip()
        if index < 1 or index > len(spans):
            raise ValueError(f"Targeted quality repair referenced invalid bullet {index}")
        if index in seen:
            raise ValueError(f"Targeted quality repair repeated bullet {index}")
        if not replacement or r"\item" in replacement:
            raise ValueError(f"Targeted quality repair returned invalid content for bullet {index}")
        seen.add(index)
        start, end, _ = spans[index - 1]
        replacements.append((start, end, replacement))

    for start, end, replacement in sorted(replacements, reverse=True):
        body = body[:start] + replacement + body[end:]
    return body


async def _repair_resume_quality(
    body_latex: str,
    errors: list[str],
    profile_text: str,
    jd_text: str,
    selected_projects: list[str],
    api_key: str,
):
    llm = get_llm_client(api_key)
    full_body_repair = _quality_errors_require_full_body_repair(errors)
    result = await llm.call_tool(
        model=CLAUDE_MODEL,
        max_tokens=4000 if full_body_repair else 1800,
        system=_QUALITY_REPAIR_SYSTEM if full_body_repair else _TARGETED_QUALITY_REPAIR_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"<candidate_profile>\n{profile_text}\n</candidate_profile>\n\n"
                f"<job_description>\n{jd_text}\n</job_description>\n\n"
                f"<selected_projects>{selected_projects}</selected_projects>\n\n"
                f"<quality_gate_errors>\n- " + "\n- ".join(errors) + "\n</quality_gate_errors>\n\n"
                f"<draft_resume_body>\n{_extract_resume_body(body_latex)}\n</draft_resume_body>"
            ),
        }],
        tool=_QUALITY_REPAIR_TOOL if full_body_repair else _TARGETED_QUALITY_REPAIR_TOOL,
        timeout=90.0,
    )
    return result


# ── Page-overflow compression ─────────────────────────────────────────────────

_COMPRESS_SYSTEM = (
    "You are compressing a LaTeX resume body to fit exactly one page. "
    "You will receive the current Experience, Projects, and Skills sections. "
    "Preserve every passing claim and heading. Apply one minimal compression pass in this order:\n"
    "1. Remove repetition and redundant clauses without turning a bullet into a fragment\n"
    "2. Shorten only overlong bullets while preserving their product context, decision, qualifiers, and result\n"
    "3. Remove an optional third experience bullet when it adds less value than the surrounding evidence\n"
    "4. Remove the lowest-ranked third project when it adds less value than the Skills evidence it displaces\n\n"
    "Do not target 16-word bullets. Do not remove a relevant Skills category. Do not alter "
    "CareerOS-supplied project headings. Never invent, substitute, or weaken technical specifics, "
    "numbers, or proper nouns. "
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


def _pdf_layout(pdf_bytes: bytes) -> tuple[int, str]:
    """Return page count plus best-effort text that overflowed past page one."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    overflow_parts: list[str] = []
    for page in reader.pages[1:]:
        try:
            text = page.extract_text()
        except Exception:
            text = ""
        if isinstance(text, str) and text.strip():
            overflow_parts.append(text.strip())
    return len(reader.pages), "\n".join(overflow_parts)


def _skill_row_contains_jd_term(row_latex: str, jd_text: str | None) -> bool:
    """Protect a Skills row when it contains an exact capability named in the JD."""
    if not jd_text:
        return False
    row_plain = _latex_to_plain(row_latex)
    _, separator, values = row_plain.partition(":")
    if not separator:
        return False
    jd = jd_text.casefold()
    for skill in values.split(","):
        normalized = re.sub(r"\s+", " ", skill).strip().casefold()
        if len(normalized) >= 2 and normalized in jd:
            return True
    return False


def _reduce_skills_once(
    body_latex: str,
    jd_text: str | None = None,
) -> tuple[str, str] | None:
    """Remove the lowest-ranked Skills row not protected by an exact JD term."""
    body = _extract_resume_body(body_latex)
    section_start = body.find(r"\section{Skills}")
    if section_start == -1:
        return None

    section = body[section_start:]
    item_starts = [
        match.start()
        for match in re.finditer(r"(?m)^[ \t]*\\item(?:\s|$)", section)
    ]
    itemize_end = section.find(r"\end{itemize}")
    if itemize_end == -1:
        return None

    row_bounds = [
        (start, item_starts[index + 1] if index + 1 < len(item_starts) else itemize_end)
        for index, start in enumerate(item_starts)
    ]
    removable = [
        bounds for bounds in row_bounds
        if not _skill_row_contains_jd_term(section[bounds[0]:bounds[1]], jd_text)
    ]
    if not removable:
        return None

    last_start, removal_end = removable[-1]
    if len(item_starts) == 1:
        trimmed = body[:section_start].rstrip() + "\n"
        return trimmed, "removed_skills_section"

    removed_item = section[last_start:removal_end]
    label_match = re.search(r"\\textbf\{([^{}]+)\}", removed_item)
    label = _latex_to_plain(label_match.group(1)).rstrip(":") if label_match else "last"
    reduced_section = section[:last_start].rstrip() + "\n" + section[removal_end:]
    return body[:section_start] + reduced_section, f"removed_skill_row:{label}"


def _remove_optional_experience_bullet_once(body_latex: str) -> tuple[str, str] | None:
    """Remove the optional third bullet from the lowest-priority experience entry."""
    body = _extract_resume_body(body_latex)
    experience_start = body.find(r"\section{Experience}")
    projects_start = body.find(r"\section{Projects}", experience_start)
    if experience_start == -1 or projects_start == -1:
        return None
    section = body[experience_start:projects_start]
    start_marker = r"\resumeItemListStart"
    end_marker = r"\resumeItemListEnd"
    blocks: list[tuple[int, list[tuple[int, int, str]]]] = []
    cursor = 0
    while True:
        list_start = section.find(start_marker, cursor)
        if list_start == -1:
            break
        list_end = section.find(end_marker, list_start + len(start_marker))
        if list_end == -1:
            break
        items = _resume_item_spans(section[list_start:list_end])
        blocks.append((list_start, items))
        cursor = list_end + len(end_marker)

    for entry_index, (list_start, items) in reversed(list(enumerate(blocks, start=1))):
        if len(items) != 3:
            continue
        item_start, item_end, _ = items[2]
        marker_start = item_start - len(r"\item \small{")
        line_start = section.rfind("\n", 0, marker_start) + 1
        removal_end = item_end + 1
        if removal_end < len(section) and section[removal_end] == "\n":
            removal_end += 1
        absolute_start = experience_start + list_start + line_start
        absolute_end = experience_start + list_start + removal_end
        return (
            body[:absolute_start] + body[absolute_end:],
            f"removed_optional_experience_bullet:{entry_index}",
        )
    return None


def _remove_last_project(body_latex: str) -> tuple[str, str] | None:
    """Remove the lowest-ranked project while preserving at least two projects."""
    body = _extract_resume_body(body_latex)
    projects_start = body.find(r"\section{Projects}")
    if projects_start == -1:
        return None
    skills_start = body.find(r"\section{Skills}", projects_start)
    projects_end = skills_start if skills_start != -1 else len(body)
    section = body[projects_start:projects_end]

    project_starts = [
        match.start()
        for match in re.finditer(r"(?m)^[ \t]*\\projectSubheading\b", section)
    ]
    if len(project_starts) <= 2:
        return None

    last_start = project_starts[-1]
    item_list_end = section.find(r"\resumeItemListEnd", last_start)
    if item_list_end == -1:
        return None
    removal_end = item_list_end + len(r"\resumeItemListEnd")
    if removal_end < len(section) and section[removal_end] == "\n":
        removal_end += 1

    removed_block = section[last_start:removal_end]
    name_match = re.search(r"\\projectSubheading\s*\{([^{}]+)\}", removed_block)
    project_name = (
        _latex_to_plain(name_match.group(1)).split("|", 1)[0].strip()
        if name_match else "last"
    )
    reduced_section = section[:last_start] + section[removal_end:]
    return (
        body[:projects_start] + reduced_section + body[projects_end:],
        f"removed_project:{project_name}",
    )


def _rendered_project_names(body_latex: str) -> list[str]:
    """Return descriptor-free project names in their final rendered order."""
    body = _extract_resume_body(body_latex)
    projects_start = body.find(r"\section{Projects}")
    if projects_start == -1:
        return []
    skills_start = body.find(r"\section{Skills}", projects_start)
    projects_end = skills_start if skills_start != -1 else len(body)
    section = body[projects_start:projects_end]
    return [
        _latex_to_plain(match.group(1)).split("|", 1)[0].strip()
        for match in re.finditer(r"\\projectSubheading\s*\{([^{}]+)\}", section)
    ]


async def _deterministic_layout_rescue(
    assembled_latex: str,
    preamble: str | None,
    overflow_text: str,
    page_count: int,
    jd_text: str | None = None,
) -> tuple[str | None, list[str], int]:
    """Try free, deterministic reductions after paid compression is exhausted."""
    current_body = _extract_resume_body(assembled_latex)
    current_pages = page_count
    actions: list[str] = []

    if overflow_text:
        excerpt = re.sub(r"\s+", " ", overflow_text).strip()[:300]
        logger.warning("One-page overflow begins with: %s", excerpt)

    # Optional third bullets are lower-value than the core experience evidence.
    while True:
        reduction = _remove_optional_experience_bullet_once(current_body)
        if reduction is None:
            break
        candidate_body, action = reduction
        candidate = _assemble_resume_latex(candidate_body, preamble)
        try:
            pdf_bytes = await compile_latex_to_pdf(candidate)
        except Exception as exc:
            raise ValueError("Deterministic experience layout rescue produced invalid LaTeX") from exc
        current_pages, overflow_text = _pdf_layout(pdf_bytes)
        current_body = candidate_body
        actions.append(action)
        logger.info("Layout rescue %s compiled to %d page(s)", action, current_pages)
        if current_pages <= 1:
            return candidate, actions, current_pages

    while True:
        reduction = _remove_last_project(current_body)
        if reduction is None:
            break
        candidate_body, action = reduction
        candidate = _assemble_resume_latex(candidate_body, preamble)
        try:
            pdf_bytes = await compile_latex_to_pdf(candidate)
        except Exception as exc:
            raise ValueError("Deterministic project layout rescue produced invalid LaTeX") from exc
        current_pages, overflow_text = _pdf_layout(pdf_bytes)
        current_body = candidate_body
        actions.append(action)
        logger.info("Layout rescue %s compiled to %d page(s)", action, current_pages)
        if current_pages <= 1:
            return candidate, actions, current_pages

    # Once only two projects remain, remove only Skills rows with no exact JD term.
    while True:
        reduction = _reduce_skills_once(current_body, jd_text)
        if reduction is None:
            break
        candidate_body, action = reduction
        candidate = _assemble_resume_latex(candidate_body, preamble)
        try:
            pdf_bytes = await compile_latex_to_pdf(candidate)
        except Exception as exc:
            raise ValueError("Deterministic Skills layout rescue produced invalid LaTeX") from exc
        current_pages, overflow_text = _pdf_layout(pdf_bytes)
        current_body = candidate_body
        actions.append(action)
        logger.info("Layout rescue %s compiled to %d page(s)", action, current_pages)
        if current_pages <= 1:
            return candidate, actions, current_pages

    return None, actions, current_pages


async def _compress_if_needed(
    assembled_latex: str,
    api_key: str,
    preamble: str | None = None,
    max_attempts: int = 1,
    jd_text: str | None = None,
) -> tuple[str, int, list[str]]:
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

    Returns (final_latex, paid_compression_attempts, deterministic_rescue_actions).
    """
    attempts = 0
    current = assembled_latex
    last_known_good: str | None = None

    # max_attempts counts paid rewrite calls, so validation needs one additional
    # compile after the final rewrite. The old loop skipped that last validation
    # and could return the previous known-good two-page document.
    for check in range(max_attempts + 1):
        try:
            pdf_bytes = await compile_latex_to_pdf(current)
        except Exception:
            if last_known_good is None:
                raise
            raise ValueError("Compressed resume failed compilation; refusing an unverified or multi-page result")

        last_known_good = current
        page_count, overflow_text = _pdf_layout(pdf_bytes)
        if page_count <= 1:
            return current, attempts, []

        if check == max_attempts:
            rescued, rescue_actions, rescued_pages = await _deterministic_layout_rescue(
                current,
                preamble,
                overflow_text,
                page_count,
                jd_text,
            )
            if rescued is not None:
                return rescued, attempts, rescue_actions
            raise ValueError(
                f"Resume still renders to {rescued_pages} pages after {attempts} "
                f"compression attempts and deterministic layout rescue"
            )

        logger.info("Resume compiled to %d pages — compressing (attempt %d)", page_count, attempts + 1)
        attempts += 1

        try:
            compressed_body = await _call_compression(_extract_resume_body(current), api_key)
        except Exception:
            logger.exception("Compression call failed")
            raise ValueError("Resume compression failed; refusing a multi-page result")

        current = _assemble_resume_latex(compressed_body, preamble)

    raise ValueError("Resume one-page validation ended unexpectedly")


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

    quality_repairs = 0
    local_editorial_rescue_actions: list[str] = []
    initial_quality_errors: list[str] = []
    if result.get("resume_latex"):
        if projects:
            result["resume_latex"] = _apply_project_headings(
                result["resume_latex"],
                result.get("selected_projects") or [],
                list(projects),
            )
        result["resume_latex"], local_editorial_rescue_actions = (
            _recover_local_quality_defects(result["resume_latex"])
        )
        initial_quality_errors = _resume_quality_errors(result["resume_latex"], profile_text)
        if initial_quality_errors:
            logger.warning(
                "Generated resume has %d material quality defects after local recovery; "
                "requesting one evidence-backed repair",
                len(initial_quality_errors),
            )
            repaired = await _repair_resume_quality(
                result["resume_latex"],
                initial_quality_errors,
                profile_text,
                jd_text,
                result.get("selected_projects") or [],
                api_key,
            )
            if "repairs" in repaired.tool_input:
                repaired_body = _apply_targeted_bullet_repairs(
                    result["resume_latex"],
                    repaired.tool_input["repairs"],
                )
            else:
                repaired_body = repaired.tool_input["resume_latex"]

            repaired_body, post_repair_actions = _recover_local_quality_defects(repaired_body)
            local_editorial_rescue_actions.extend(post_repair_actions)
            if projects:
                repaired_body = _apply_project_headings(
                    repaired_body,
                    result.get("selected_projects") or [],
                    list(projects),
                )
            remaining_errors = _resume_quality_errors(repaired_body, profile_text)
            if remaining_errors:
                logger.error(
                    "Resume quality repair failed acceptance gate: %s",
                    " | ".join(remaining_errors),
                )
                raise ValueError(
                    "Generated resume did not meet the editorial quality gate after repair."
                )
            result["resume_latex"] = repaired_body
            result["input_tokens"] += repaired.input_tokens
            result["output_tokens"] += repaired.output_tokens
            result["cache_read_tokens"] += repaired.cache_read_tokens
            result["cache_write_tokens"] += repaired.cache_write_tokens
            quality_repairs = 1

    # Assemble full document, then compress if it spills past one page
    if result.get("resume_latex"):
        assembled = _assemble_resume_latex(result["resume_latex"], preamble)
        final_latex, compression_attempts, layout_rescue_actions = await _compress_if_needed(
            assembled,
            api_key,
            preamble,
            jd_text=jd_text,
        )
        if projects:
            canonical_body = _apply_project_headings(
                final_latex,
                result.get("selected_projects") or [],
                list(projects),
            )
            canonical_latex = _assemble_resume_latex(canonical_body, preamble)
            if canonical_latex != final_latex:
                canonical_pdf = await compile_latex_to_pdf(canonical_latex)
                canonical_pages, _ = _pdf_layout(canonical_pdf)
                if canonical_pages > 1:
                    raise ValueError(
                        "Canonical project headings caused the compressed resume to exceed one page."
                    )
                final_latex = canonical_latex
        post_compression_errors = _resume_quality_errors(final_latex, profile_text)
        if post_compression_errors:
            logger.error(
                "One-page compression damaged resume quality: %s",
                " | ".join(post_compression_errors),
            )
            raise ValueError("One-page compression produced an editorially invalid resume.")
        result["resume_latex"] = final_latex
        result["compression_attempts"] = compression_attempts
        result["layout_rescue_actions"] = layout_rescue_actions
        rendered_projects = _rendered_project_names(final_latex)
        if rendered_projects:
            result["selected_projects"] = rendered_projects

    result["generation_metadata"] = {
        "pipeline": "full_context_quality_gated",
        "quality_gate_version": 2,
        "quality_repair_attempts": quality_repairs,
        "initial_quality_errors": initial_quality_errors,
        "local_editorial_rescue_actions": local_editorial_rescue_actions,
        "layout_rescue_actions": result.get("layout_rescue_actions", []),
    }

    return result


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
