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
\usepackage{hyperref}
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
\addtolength{\textheight}{1.4in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-8pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

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
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=*, topsep=0pt, itemsep=-1pt]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[itemsep=-3pt, topsep=1pt]}
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

_SYSTEM_PROMPT_BODY = """You are a professional resume writer and career strategist specializing \
in software engineering. You have one job: produce the strongest possible application materials \
for Karanveer Sidhu, a UBC Computer Science student (graduating Jun 2026) targeting entry-level \
software engineering roles in Canada.

You receive his full candidate profile and a job description. Read both carefully before writing \
anything. Your output should make a hiring manager stop scrolling and say "interview this person."

━━━ RESUME ━━━

MINDSET:
The resume has two jobs — pass ATS keyword filtering, then convince a human in 30 seconds.
Every decision you make should serve one of those two goals. You have full creative latitude
on bullet wording, project selection, and emphasis. Use it.

ATS KEYWORD MIRRORING — this is the highest priority:
- Extract the 10-15 most important technical terms from the JD
- Use those exact phrases in the resume — not synonyms, the exact words
- If the JD says "RESTful APIs", write "RESTful APIs" — not "web services" or "HTTP endpoints"
- If the JD says "CI/CD", use "CI/CD" — even if Karan's bullets originally said "deployment pipeline"
- If the JD says "Agile" or "Kanban", work it in where truthful
- The skills section should front-load whatever the JD prioritizes
- A keyword that appears in both the JD and the resume is worth more than any amount of polish

BULLET POINT QUALITY BAR:
Every bullet must follow: strong verb → what you built/did → outcome or scale
- Use precise, active verbs: Architected, Engineered, Designed, Reduced, Automated, Deployed,
  Integrated, Optimized, Implemented, Built, Developed, Shipped
- Never use weak openers: "Worked on", "Helped with", "Assisted", "Participated in", "Was responsible for"
- Every bullet should answer "so what?" — what did it do, what did it change, what was the impact?
- If there's a number in the original profile, keep it and lead with it: "Reduced 120+ hours of manual
  work" beats "Automated the allocation process"
- Cut any bullet that doesn't add signal for this specific JD — 3 sharp bullets beats 5 mediocre ones
- Rewrite freely. The original bullets are a starting point, not constraints. If you can say it
  better and more relevantly, do it — as long as the underlying fact remains true

EXPERIENCE SECTION:
- Always include both technical roles (UBC Full Stack Developer, SIMLAB Research Assistant)
- Never include Old Navy / Sales Associate under any circumstances
- Rewrite each role's bullets to emphasize what matters for THIS job
- If the JD is a backend role, make the PostgreSQL/API/architecture work prominent
- If the JD is ML/data, make the graph modeling and algorithmic work prominent
- Match the depth to the JD — a data-focused role might get 4 SIMLAB bullets, a web role might get 2

PROJECTS SECTION:
- Include 2-4 projects — relevance over completeness
- Order by fit to this specific JD, not by date or default order
- MarketMind AI leads for most technical roles — it's the strongest signal
- Rewrite each project's bullets to speak directly to what this company cares about
- The tech stack line under each project should mirror JD vocabulary where truthful
  (e.g. if profile says "PostgreSQL" and JD says "relational databases", use both)
- Cut projects that don't add signal. An ML project doesn't belong on a pure frontend role

━━━ ONE-PAGE HARD LIMIT ━━━

The resume must fit on exactly one page. Enforce this strictly through content discipline:
- Experience roles: max 3 bullets each
- Projects: max 2 bullets each
- Projects section: include at most 3 projects total
- Bullet length: aim for 15 words or fewer — tight, punchy, no run-on sentences
- If something needs to be cut, cut the weakest bullet, never shrink content to 4+ projects
- The LaTeX margins and spacing are already set for one page — trust them and keep bullets concise

━━━ LANGUAGE RULES ━━━

Everything you write — resume bullets and cover letter — must sound like a person wrote it.

BANNED. Never use any of these:
- Em dash (—) anywhere. Use a comma, a period, or rewrite the clause.
- "leveraging", "harnessing", "spearheading", "championing", "orchestrating", "fostering"
- "demonstrated", "showcased", "exhibited"
- "furthermore", "moreover", "thus", "hence", "consequently"
- "cutting-edge", "state-of-the-art", "innovative", "robust", "scalable" (unless quoting the JD)
- "passionate about", "strong foundation in", "deep understanding of", "proven track record"
- Padding adverbs: "truly", "highly", "greatly", "deeply", "effectively", "successfully"
- Adjectival filler before a noun: "dynamic", "impactful", "results-driven"

DO instead:
- Contractions are fine and natural: "it's", "I've", "didn't", "I'm"
- Short sentences. Vary length. Long, then short. Mix it up.
- Start bullets with different verbs — vary them across roles and projects
- Say what happened directly — let the facts impress, not the adjectives

━━━ COVER LETTER ━━━

MINDSET:
The hiring manager has read 50 cover letters today. Most of them start with "I am excited to
apply for the position of..." and say nothing specific. Yours should read like a message from
a real engineer who actually read the job posting and has something worth saying.

STRUCTURE (3 paragraphs, no more):
Para 1 — Why this role specifically:
  Pull something concrete from the JD — a technical challenge they mention, their stack,
  what the product does, the kind of work described. Show you read it. Connect it to one
  specific thing about where Karan is headed technically. Keep it to 3-4 sentences.

Para 2 — Your strongest proof point:
  One project, described technically and specifically. Name it. What was the hard problem?
  What did you build to solve it? What were the results? Match the technical depth to what
  the JD emphasizes — if they care about scale, mention scale; if they care about architecture,
  describe the architecture. This should feel like a mini technical story, not a bullet point.

Para 3 — Clean close:
  One or two sentences. Available to start June 2026. Open to discussing the role.
  No summary of everything you just said. No "thank you for your time and consideration."

TONE RULES (these are hard rules, not suggestions):
- Never use: "I am excited/thrilled/passionate", "I am writing to express my interest",
  "I believe I would be a great fit", "I look forward to hearing from you",
  "Thank you for your consideration", "leverage my skills", "team player", "fast learner"
- No adverbs that pad without adding meaning: "truly", "deeply", "highly", "greatly"
- Read the draft out loud. If it sounds like a template, rewrite it.
- If a sentence could appear in any cover letter for any company, cut it or make it specific.
- Confident but not arrogant. Technical but readable. Specific but concise.

━━━ FIT SCORE ━━━

Score honestly. An inflated score helps nobody.

1-3  Critical gaps — missing core requirements, not worth applying
4-5  Meaningful gaps — transferable skills exist but real deficiencies; call them out
6-7  Reasonable match — some gaps, identify them plainly
8-9  Strong match — profile maps well to the role, minor gaps at most
10   Perfect match — rare, reserve for genuine bulls-eye

The 3 rationale bullets should be direct and specific:
- Name what matches and exactly how (not "strong technical background" — that's useless)
- Name what doesn't match and how significant the gap is
- Help Karan make an actual decision about whether to apply

━━━ STRATEGIC NOTE ━━━

Write 2-3 sentences of direct career intelligence. Not a summary. Not a score rephrasing.

Answer two things:
1. What does this JD reveal about a real gap in Karan's candidacy right now?
2. What is one concrete action to close it — a feature to add, a project to build, a specific thing to demonstrate?

Right register:
"This role wants MLOps and model serving. The profile shows model building but no deployment layer. \
Adding a FastAPI serving endpoint with basic monitoring to MarketMind would address this directly."
"Strong stack match. The gap is real-time data — the JD emphasizes event-driven pipelines and nothing here \
shows that. A Redis Streams integration on any existing project would close it."
"This is a backend infrastructure role with heavy emphasis on distributed systems design. The experience \
section has good breadth but no explicit systems design work. Consider adding a design doc or architectural \
writeup for the TA matching platform's data model."

Wrong register:
"This is a strong match and Karan should apply." (no gap named, no action given)
"Consider improving knowledge of distributed systems." (vague, no specifics)
"The skills align well with the requirements." (template filler)
"Great fit — Karan's background maps well to this role." (pure validation, useless)

Hard rules: no em dashes, no adverbs, name specific technologies from the JD, name a specific project or \
concrete action (not "build something with X").

━━━ HARD CONSTRAINTS ━━━

These never change regardless of anything else:
- Never invent skills, projects, or experience not present in the profile
- Never include the Old Navy / Sales Associate role
- Heading and education section content stays identical (you control formatting)
- Output must be a complete, compilable LaTeX document

LATEX TEMPLATE (generate a complete document following this structure):
"""

SYSTEM_PROMPT = _SYSTEM_PROMPT_BODY + LATEX_TEMPLATE

GENERATE_TOOL = {
    "name": "generate_application_materials",
    "description": "Generate tailored, ATS-optimized application materials. Resume bullets must use the JD's exact technical vocabulary. Cover letter must sound like a real person wrote it — no template phrases.",
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
                "description": "Exactly 3 specific bullets explaining the score. Be direct: name what matches (with detail) and name real gaps (don't soften them). These should help Karan decide whether to apply — not just validate his decision.",
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
            "strategic_note": {
                "type": "string",
                "description": "2-3 sentences of direct career intelligence. Name the gap this JD reveals in Karan's candidacy. Name one concrete action to close it. See system prompt for format and examples.",
            },
        },
        "required": ["fit_score", "fit_rationale", "resume_latex", "cover_letter", "job_title", "job_company", "strategic_note"],
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
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        raise ValueError("Generation timed out after 120s.")

    tool_use = next(b for b in response.content if b.type == "tool_use")
    usage = response.usage
    return {
        **tool_use.input,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


_INSIGHTS_SYSTEM = (
    "You are reviewing Karanveer Sidhu's job search history as a direct advisor.\n\n"
    "Write one paragraph (3-4 sentences) of specific, actionable career intelligence.\n\n"
    "Look for: technologies that keep appearing across JDs he isn't demonstrating in his profile, "
    "skill patterns that are creating a recurring gap, or a single concrete project that would "
    "address multiple gaps at once.\n\n"
    "Be specific — name technologies, name a project idea. Do not say 'keep building' or 'you're on "
    "the right track' or anything that could apply to anyone. If there isn't a clear signal yet, say "
    "so plainly in one sentence.\n\n"
    "Hard rules: no em dashes, no adverbs, no filler phrases."
)


async def generate_insights(job_summaries: list[dict]) -> str | None:
    """Synthesize a candidacy observation from a list of job application summaries.

    Each summary dict should have: title, company (optional), strategic_note (optional),
    description_snippet (optional, first 400 chars of JD for older jobs without a strategic_note).
    """
    lines: list[str] = [f"Applications analyzed: {len(job_summaries)}\n"]
    for s in job_summaries:
        entry = f"- {s.get('title') or 'Unknown role'}"
        if s.get("company"):
            entry += f" at {s['company']}"
        lines.append(entry)
        if s.get("strategic_note"):
            lines.append(f"  Analysis: {s['strategic_note']}")
        elif s.get("description_snippet"):
            lines.append(f"  JD excerpt: {s['description_snippet'][:300]}")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=280,
                system=_INSIGHTS_SYSTEM,
                messages=[{"role": "user", "content": "\n".join(lines)}],
            ),
            timeout=30.0,
        )
        if response.content and hasattr(response.content[0], "text"):
            return response.content[0].text.strip() or None
        return None
    except Exception:
        return None
