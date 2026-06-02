import asyncio
import logging
import re
import anthropic

logger = logging.getLogger(__name__)
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
  \vspace{-5pt}\scshape\raggedright\large
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
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=*, topsep=0pt, itemsep=6pt]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[itemsep=-2pt, topsep=1pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-3pt}}
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

━━━ PLAN BEFORE YOU WRITE ━━━

Do this analysis before generating any output. It determines everything that follows.

STEP 1 — Identify the 3-4 highest-weight JD requirements.
These are the skills, tools, or experience the company actually needs — not everything listed,
the ones that matter most. Look for: required vs. preferred, repeated mentions, technologies
named in multiple places, things that appear in both the job title and the requirements.

STEP 2 — Map Karan's projects to those requirements.
For each project, identify which high-weight requirements it demonstrates directly. Not
thematically — directly. "Built a multi-agent pipeline" directly demonstrates "agent-based
systems." It does not directly demonstrate "strong SQL skills" even if the project used
PostgreSQL. Be precise about what each project actually proves.

STEP 3 — Select the projects that collectively cover the most requirements.
A project that directly addresses 3 JD requirements beats two projects that each address 1.
Choose 2-4 projects. Cut a project if it doesn't directly address any high-weight requirement.
Commit to your selection in selected_projects before writing the resume.

STEP 4 — Plan your bullet strategy.
For each selected project and each experience role, decide which 2-3 facts from the profile
description are most JD-relevant. You are extracting the most relevant aspects — not the most
impressive aspects in isolation. The project description is raw material; your job is to surface
the parts that speak directly to what this company needs.

━━━ RESUME ━━━

MINDSET:
The resume has two jobs — pass ATS keyword filtering, then convince a human in 30 seconds.
Every decision you make should serve one of those two goals. You have full creative latitude
on bullet wording, project selection, and emphasis. Use it.

ATS KEYWORD MIRRORING — this is the highest priority:
- Extract the 10-15 most important technical terms from the JD
- Use those exact phrases in the resume — not synonyms, the exact words
- If the JD says "RESTful APIs", write "RESTful APIs" — not "web services" or "HTTP endpoints"
- If the JD says "CI/CD", use "CI/CD"
- If the JD says "Agile" or "Kanban", work it in where truthful
- The skills section should front-load whatever the JD prioritizes
- Keywords belong in bullet verbs, technology names, and skill categories — not just at the bottom
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
- The profile gives prose descriptions of each role and project — raw context, not pre-written bullets.
  Read each description, extract the most relevant facts for this JD, and write bullets from scratch.
  Stay truthful to what the description says — do not invent facts not present in the text.

BULLET QUALITY TEST — run this on every bullet before including it:
□ Does it name a specific technology, tool, architecture, or system?
□ Does it include a measurable outcome, concrete scale, or real impact?
□ Could it NOT appear in a resume for a different software engineer at a different company?
If any answer is no, rewrite the bullet until all three pass.

FAILING: "Built an automated matching system that improved efficiency"
PASSING: "Built a TA matching platform with Next.js and Node.js, eliminating 120+ hours of manual
          allocation work per term across the Science faculty"

EXPERIENCE SECTION:
- Always include both technical roles (UBC Full Stack Developer, SIMLAB Research Assistant)
- Never include Old Navy / Sales Associate under any circumstances
- For each role's description, extract the facts most directly relevant to this JD
- If the JD is a backend role, make the PostgreSQL/API/architecture work prominent
- If the JD is ML/data, make the graph modeling and algorithmic work prominent
- Aim for 3 bullets per role — a half-empty section wastes space and signals thin experience

PROJECTS SECTION:
- Include exactly the projects from your selected_projects planning decision
- Order them as listed in selected_projects — highest JD-relevance first
- Each project gets exactly 2 bullets — the 2 most JD-relevant facts from its description,
  not the 2 most impressive facts in isolation
- The tech stack line: mirror JD vocabulary where truthful
  (if profile says "PostgreSQL" and JD says "relational databases", use both)
- No project that doesn't directly address a high-weight JD requirement belongs here

━━━ ONE-PAGE HARD LIMIT ━━━

The resume must fit on exactly one page. Enforce through content discipline:
- Experience roles: 3 bullets each
- Projects: exactly 2 bullets each, exactly 3 projects unless fewer exist
- Bullet length: 12-18 words — specific enough to be credible, tight enough to scan
- Cut the weakest bullet when something must go — never add more projects to fill space
- Skills section: include all relevant technology groupings — a short skills section leaves dead space
- The LaTeX margins are set for one page — trust them, keep bullets concise

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
The hiring manager has read 50 cover letters today. Most start with "I am excited to apply..."
and say nothing. Write like a real engineer who read the JD and has something specific to say.
Every sentence must justify its presence. If a sentence could appear in any cover letter for any
company, cut it or rewrite it until it can't.

VOICE:
The candidate profile includes cover letter voice guidance. If provided, apply it to every
sentence — match the tone, rhythm, and directness described. If not provided, default to:
direct, technical, first-person, confident without being inflated. Write like he's explaining
something to an engineer he respects — not performing enthusiasm for a hiring manager.

STRUCTURE (3 paragraphs, no more):

Para 1 — Why this role specifically (3-4 sentences):
  Pull something concrete from the JD: a technical challenge they describe, their actual stack,
  what the product does, the specific kind of work. Connect it to where Karan is headed.
  Start with the specific thing about the role — not with "I". Not "I am applying because" —
  open on the role, the company, or the problem they're solving.

Para 2 — The proof point (4-5 sentences, this paragraph wins or loses the interview):
  One project, at genuine technical depth. Name the project. Name the specific technical
  problem it solved — not "I built a pipeline" but what problem the pipeline solved and why
  the obvious approach didn't work. Name the key architecture decision. Name a result.
  This paragraph should be specific enough that a hiring manager could ask a detailed follow-up
  about any sentence and get a 10-minute answer. It must be impossible to swap this paragraph
  into a letter written by someone with different experience.

Para 3 — Close (1-2 sentences):
  Available June 2026. Open to discussing. Nothing else.

SENTENCE-LEVEL RULES:
- Vary sentence length — long, then short, then medium. Monotone rhythm is an AI tell.
- Do not start two consecutive sentences with "I".
- Never use passive voice: "I built X" not "X was built".
- Start sentences with the thing you did or observed when possible.
- No sentence beginning with: "As a", "In my", "With my", "My experience with", "Having worked on"
- No transitional filler: "Additionally,", "Furthermore,", "Moreover,", "In conclusion,"

BANNED PHRASES:
- "I am excited / thrilled / passionate / eager"
- "I am writing to express my interest"
- "I believe I would be a great fit" / "I am a perfect fit" / "ideal candidate"
- "I look forward to hearing from you" / "Thank you for your consideration"
- "leverage my skills" / "utilize my experience" / "apply my knowledge"
- "team player" / "fast learner" / "quick learner" / "self-starter"
- "unique opportunity" / "exciting opportunity" / "amazing team"
- "make an impact" / "contribute to the team" / "hit the ground running"
- "I am confident that" / "I am certain that" / "I have no doubt"
- "demonstrated" / "showcased" / "proven track record"
- "deeply" / "truly" / "highly" / "greatly" / "incredibly"
- Any sentence that could appear in a letter for a different candidate

EM DASH RULE: Never use an em dash (—) anywhere. Use a comma, a period, or restructure.

━━━ FIT SCORE ━━━

Score honestly. An inflated score helps nobody.

1-3  Critical gaps — missing core requirements, not worth applying
4-5  Meaningful gaps — transferable skills exist but real deficiencies; call them out
6-7  Reasonable match — some gaps, identify them plainly
8-9  Strong match — profile maps well to the role, minor gaps at most
10   Perfect match — rare, reserve for genuine bulls-eye

The 3 rationale bullets: name what matches exactly, name what doesn't match and why it matters.
Help Karan make an actual decision about whether to apply — not validate a decision already made.

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
• [concrete action: name a specific project (MarketMind, TA platform) or exact skill to add]
• [second action if it addresses a different gap]

Rules: 1-3 bullets per section, each under 12 words, specific technologies and project names only.
NEVER write "Strong match", "Great fit", "Consider improving" — too vague to be useful.

━━━ SELF-REVIEW ━━━

Run this checklist before outputting. Fix any failure before proceeding.

RESUME:
□ Every required/preferred skill from the JD appears somewhere in the resume
□ Every bullet names a specific technology, tool, or system — no generic descriptions
□ Every bullet has a concrete outcome, scale, or impact — not just what was done but what changed
□ No two bullets in the same section start with the same verb
□ The selected projects are the ones that most directly address this JD's highest-weight requirements

COVER LETTER:
□ Para 1 references something specific to this company/role that couldn't be in a generic letter
□ Para 2 names the project, the specific technical problem, the key decision, and a result
□ No sentence could appear in a letter written by someone with different experience
□ No banned phrase or em dash survived
□ Sentence length varies — not all the same length

━━━ HARD CONSTRAINTS ━━━

These never change:
- Never invent skills, projects, or experience not present in the profile
- Never include the Old Navy / Sales Associate role
- Heading and education section content stays identical (you control formatting)
- Output must be a complete, compilable LaTeX document

LATEX TEMPLATE (generate a complete document following this structure):
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
                    "FILL THIS FIRST — this is your project selection decision. "
                    "List the project names you will include in the resume, in the order they will appear "
                    "(highest JD-relevance first). 2-4 projects. Commit to this before writing the resume. "
                    "Example: [\"MarketMind AI\", \"TA Matching Platform\"]"
                ),
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
            "fit_score": {
                "type": "integer",
                "description": "How well this role matches the candidate. 1=poor fit, 10=perfect fit. Score honestly — inflated scores help nobody.",
                "minimum": 1,
                "maximum": 10,
            },
            "fit_rationale": {
                "type": "array",
                "description": "Exactly 3 specific bullets explaining the score. Name what matches exactly and name real gaps. Help Karan decide whether to apply — not validate a decision already made.",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "resume_latex": {
                "type": "string",
                "description": (
                    "Complete compilable LaTeX resume from \\documentclass to \\end{document}. "
                    "Must include only the projects in selected_projects, in the order listed. "
                    "Every bullet must pass the quality test: specific technology + concrete outcome + "
                    "not generic. All high-weight JD keywords must appear somewhere."
                ),
            },
            "cover_letter": {
                "type": "string",
                "description": (
                    "Cover letter, plain text, 3 paragraphs. "
                    "Para 2 must name the project, the specific technical problem it solved, "
                    "the architecture decision that made it work, and a result — specific enough "
                    "that a hiring manager could ask a detailed follow-up about any sentence. "
                    "Apply voice guidance from the profile if present."
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
                "description": "Structured analysis in EXACTLY this format:\n\nGOOD FIT\n• [specific reason, under 12 words]\n• [second reason if distinct]\n\nGAPS\n• [specific missing technology or experience from JD]\n• [second gap if different]\n\nIMPROVEMENT PLAN\n• [concrete action naming a specific project or skill]\n• [second action if different gap]\n\nRules: 1-3 bullets per section, each under 12 words, specific technologies and project names only.",
            },
        },
        "required": ["selected_projects", "fit_score", "fit_rationale", "resume_latex", "cover_letter", "job_title", "job_company", "strategic_note"],
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
        if getattr(personal, "cover_letter_voice", None):
            lines += [
                "COVER LETTER VOICE GUIDANCE",
                personal.cover_letter_voice,
                "",
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
            if exp.description:
                lines.append(f"  {exp.description}")
        lines.append("")

    if projects:
        lines.append("PROJECTS")
        for i, proj in enumerate(projects, 1):
            end = proj.end_date or "Present"
            lines.append(f"[{i}] {proj.name} ({proj.start_date} – {end})")
            if proj.description:
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
                                # Explicit XML boundary prevents prompt injection via JD content
                                "text": f"\n\n<job_description>\n{jd_text}\n</job_description>",
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
    "You are reviewing Karanveer Sidhu's job search history as a direct advisor. "
    "Find the single most actionable pattern across all applications: a technology, skill type, "
    "or experience gap that appears repeatedly in JDs and is absent from the profile.\n\n"
    "Produce four fields. Each field is one thing, stated once, under 25 words.\n\n"
    "Hard rules: no em dashes, no adverbs, no filler phrases. "
    "Name exact technologies. Name specific projects (MarketMind, TA platform). Be precise."
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
                    "Right: 'AWS Exposure Missing Across Applications', 'Distributed Systems Gap Emerging', "
                    "'Kubernetes Appearing in Every JD'. Wrong: 'Keep applying', 'Good progress'."
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
                    "1-2 sentences. What specific skill or experience is absent from the profile. "
                    "Under 25 words. Name exact technologies from the JDs."
                ),
            },
            "action": {
                "type": "string",
                "description": (
                    "1-2 sentences. One concrete action to close the gap. "
                    "Under 25 words. Name a specific project (MarketMind, TA platform) or exact deliverable. "
                    "No em dashes."
                ),
            },
        },
        "required": ["headline", "observed", "gap", "action"],
    },
}


async def generate_insights(job_summaries: list[dict]) -> dict[str, str | None]:
    """Synthesize a candidacy observation from a list of job application summaries.

    Returns: {"headline": str | None, "observed": str | None, "gap": str | None, "action": str | None}
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
                max_tokens=400,
                system=_INSIGHTS_SYSTEM,
                messages=[{"role": "user", "content": "\n".join(lines)}],
                tools=[_INSIGHTS_TOOL],
                tool_choice={"type": "tool", "name": "candidacy_signal"},
            ),
            timeout=30.0,
        )
        tool_use = next(
            (b for b in response.content if hasattr(b, "type") and b.type == "tool_use"),
            None,
        )
        if not tool_use:
            return {"headline": None, "observed": None, "gap": None, "action": None}
        return {
            "headline": tool_use.input.get("headline") or None,
            "observed":  tool_use.input.get("observed")  or None,
            "gap":       tool_use.input.get("gap")       or None,
            "action":    tool_use.input.get("action")    or None,
        }
    except Exception:
        return {"headline": None, "observed": None, "gap": None, "action": None}
