import asyncio
import re
import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory

CLAUDE_MODEL = "claude-sonnet-4-6"

# Raw string so LaTeX backslashes are preserved; no f-string so LaTeX braces aren't misread
LATEX_TEMPLATE = r"""
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
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.7in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-6pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-4pt}]

\newcommand{\iconlink}[1]{#1}
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

\begin{document}

%----------HEADING (never change this)-----------------
\begin{tabular*}{\textwidth}{l@{\extracolsep{\fill}}r}
  \textbf{\href{https://www.linkedin.com/in/karan-sidhu3/}{\Large Karanveer Sidhu}} &
  \iconlink{\faEnvelope} \href{mailto:karansidhu5550@gmail.com}{karansidhu5550@gmail.com}\\
  \iconlink{\faLinkedin} \href{https://www.linkedin.com/in/karan-sidhu3/}{linkedin.com/in/karan-sidhu3} &
  \iconlink{\faPhone} +1 (250) 509-2500 \\
  \iconlink{\faGithub} \href{https://github.com/karansidhu3}{github.com/karansidhu3} & \\
\end{tabular*}

%-----------EDUCATION (never change this)-----------------
\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {University of British Columbia}{Sep. 2022 -- Jun. 2026}
      {Bachelor of Science in Computer Science, Minor in Data Science}{}
  \resumeSubHeadingListEnd

%-----------EXPERIENCE — tailor bullets but keep both roles-----------------
\section{Experience}
  \resumeSubHeadingListStart
    % Full Stack Developer at UBC — always include
    % Research Assistant at SIMLAB — always include
    % Sales Associate at Old Navy — NEVER include
  \resumeSubHeadingListEnd

%-----------PROJECTS — reorder by relevance, include 2-4-----------------
\section{Projects}
  \resumeSubHeadingListStart
    % Use \projectSubheading{Name}{Date}{Tech stack}{}{github_url}
  \resumeSubHeadingListEnd

%-----------SKILLS-----------------
\section{Skills}
\vspace{-2pt}
\begin{itemize}[leftmargin=*, itemsep=-2pt, topsep=2pt]
  % List skills grouped by category
\end{itemize}
\vspace{-6pt}

\end{document}
"""

_SYSTEM_PROMPT_BODY = """You generate tailored job application materials for Karanveer Sidhu, \
a UBC Computer Science student (graduating Jun 2026) seeking entry-level software engineering \
roles in Canada.

You receive his candidate profile and a job description, then produce all materials via the tool.

RESUME RULES:
- Use ONLY information from the profile — never fabricate skills, roles, or projects
- Always include both work experiences (Full Stack Developer at UBC, Research Assistant at SIMLAB)
- Never include the Sales Associate / Old Navy role — it is not technical
- Reorder projects so the most relevant appears first for this specific JD
- Include 2–4 projects; omit clearly irrelevant ones
- Rewrite bullet points to emphasize skills and outcomes that match the JD — stay truthful, just reframe
- MarketMind AI is the strongest project — lead with it for most tech roles
- Keep the heading and education section identical every time
- Output the complete compilable LaTeX document

COVER LETTER RULES:
- 3 paragraphs, no filler phrases ("I am excited to apply", "I am writing to")
- Para 1: What specifically caught attention about this role/company (from JD). One sentence on why it fits where Karan is headed.
- Para 2: The most relevant project with specific technical detail and results. Name the project.
- Para 3: Short close. Available to start June 2026. Open to discussion.
- Tone: direct, confident, not desperate. Read like a person wrote it.

LATEX TEMPLATE (generate a complete document following this structure):
"""

SYSTEM_PROMPT = _SYSTEM_PROMPT_BODY + LATEX_TEMPLATE

GENERATE_TOOL = {
    "name": "generate_application_materials",
    "description": "Generate all tailored application materials for the job posting",
    "input_schema": {
        "type": "object",
        "properties": {
            "fit_score": {
                "type": "integer",
                "description": "How well this role matches the candidate. 1=poor fit, 10=perfect fit.",
                "minimum": 1,
                "maximum": 10,
            },
            "fit_rationale": {
                "type": "array",
                "description": "Exactly 3 concise bullets explaining the score — what matches and what doesn't.",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "resume_latex": {
                "type": "string",
                "description": "Complete compilable LaTeX resume tailored to this job, from \\documentclass to \\end{document}.",
            },
            "cover_letter": {
                "type": "string",
                "description": "Cover letter tailored to this job. Plain text, 3 paragraphs.",
            },
            "job_title": {
                "type": "string",
                "description": "The job title extracted from the job description.",
            },
            "job_company": {
                "type": "string",
                "description": "The company name extracted from the job description.",
            },
        },
        "required": ["fit_score", "fit_rationale", "resume_latex", "cover_letter", "job_title", "job_company"],
    },
}


def _format_profile(
    personal: PersonalInfo | None,
    education: list,
    experience: list,
    projects: list,
    skills: list,
) -> str:
    lines = ["=== CANDIDATE PROFILE ===\n"]

    if personal:
        lines += [
            f"Name: {personal.name}",
            f"Email: {personal.email}",
            f"Phone: {personal.phone}",
            f"LinkedIn: {personal.linkedin}",
            f"GitHub: {personal.github}",
            f"Location: {personal.location}\n",
        ]

    if education:
        lines.append("EDUCATION")
        for e in education:
            minor = f", Minor in {e.minor}" if e.minor else ""
            lines.append(f"- {e.school} | {e.degree}{minor} | {e.start_date} – {e.end_date}")
        lines.append("")

    if experience:
        lines.append("EXPERIENCE")
        for i, exp in enumerate(experience, 1):
            end = exp.end_date or "Present"
            lines.append(f"[{i}] {exp.role} at {exp.company} ({exp.start_date} – {end})")
            for bullet in (exp.bullets or []):
                lines.append(f"  • {bullet}")
        lines.append("")

    if projects:
        lines.append("PROJECTS")
        for i, proj in enumerate(projects, 1):
            end = proj.end_date or "Present"
            tech = ", ".join(proj.tech or [])
            lines.append(f"[{i}] {proj.name} ({proj.start_date} – {end})")
            lines.append(f"  Tech: {tech}")
            for bullet in (proj.bullets or []):
                lines.append(f"  • {bullet}")
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


async def generate_materials(db: AsyncSession, jd_text: str) -> dict:
    personal = (await db.execute(select(PersonalInfo).limit(1))).scalar_one_or_none()
    education = (await db.execute(select(Education))).scalars().all()
    experience = (await db.execute(
        select(Experience).order_by(Experience.sort_order)
    )).scalars().all()
    projects = (await db.execute(
        select(Project).order_by(Project.sort_order)
    )).scalars().all()
    skills = (await db.execute(
        select(SkillCategory).order_by(SkillCategory.sort_order)
    )).scalars().all()

    profile_text = _format_profile(
        personal, list(education), list(experience), list(projects), list(skills)
    )

    jd_text = _preprocess_jd(jd_text)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await asyncio.wait_for(
            client.messages.create(
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
                                "text": f"\n\n=== JOB DESCRIPTION ===\n\n{jd_text}",
                            },
                        ],
                    }
                ],
                tools=[GENERATE_TOOL],
                tool_choice={"type": "tool", "name": "generate_application_materials"},
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        raise ValueError(
            "Generation timed out after 25s. Try a shorter job description."
        )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    usage = response.usage
    return {
        **tool_use.input,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }
