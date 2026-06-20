import asyncio
import logging
import re
import anthropic

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.profile import Experience, PersonalInfo, Project, SkillCategory

CLAUDE_MODEL = "claude-sonnet-4-6"

# Static preamble — injected by Python at assembly time; never output by Claude.
# Contains all deterministic content: packages, custom commands, heading, education.
LATEX_PREAMBLE = r"""\documentclass[letterpaper,11pt]{article}

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
      {Bachelor of Science in Computer Science, Minor in Data Science}{}
  \resumeSubHeadingListEnd

"""

# Body structure shown to Claude in the system prompt — variable sections only.
# Includes command usage comments so Claude knows each command's argument signature.
LATEX_TEMPLATE = r"""
%-----------EXPERIENCE — tailor bullets but keep both roles-----------------
\section{Experience}
  \resumeSubHeadingListStart
    % \resumeSubheading{Company}{Location}{Role}{Dates}
    %   \resumeItemListStart
    %     \item \small{bullet text}
    %   \resumeItemListEnd
    % Full Stack Developer at UBC — always include
    % Research Assistant at SIMLAB — always include
    % Sales Associate at Old Navy — NEVER include
  \resumeSubHeadingListEnd

%-----------PROJECTS — reorder by relevance, include 2-4-----------------
\section{Projects}
  \resumeSubHeadingListStart
    % \projectSubheading{Name}{Dates}{Tech Stack}{}{github_url}
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

_SYSTEM_PROMPT_BODY = """You are writing for a technical recruiter who spends 30 seconds per \
resume. They are not reading — they are scanning. They look at the first noun in each bullet. \
They pattern-match for: specific systems they recognize, numbers that signal scale, architecture \
decisions that signal someone has built and operated something real. A bullet that doesn't signal \
relevant technical work in the first five words will not be read. Your job: produce the most \
technically dense, number-anchored, scanner-optimized resume possible for Karanveer Sidhu, \
a UBC Computer Science student (graduating Jun 2026) targeting entry-level software engineering \
roles in Canada.

━━━ PLAN BEFORE YOU WRITE ━━━

STEP 0 — Extract every number from the profile. Do this before anything else.
Go through every experience and project description. List every figure: hours saved,
percentages, throughput, dataset sizes, latencies, counts, rates, token savings.
These are mandatory. A number in the source that does not appear in the final bullet
covering that role or project is a generation failure.

STEP 1 — Identify the 3-4 highest-weight JD requirements.
Required over preferred. Repeated mentions. Technologies named in the job title and
the requirements. These are the signals that determine project selection.

STEP 2 — For each role and project, identify the specific technical components,
decisions, and systems that match those requirements. Not themes — specific nouns.
Not "this project used a database" — "PostgreSQL allocation schema with many-to-many
relationship tables." Not "distributed systems work" — "tail-based sampling layer
buffering spans in Redis until full trace arrives." Specificity is the output of this step.

STEP 3 — Select projects that collectively cover the most high-weight requirements.
A project covering 3 requirements beats two projects each covering 1.
Choose 2-3 projects. Cut anything that doesn't directly address a high-weight requirement.
Commit to selected_projects before writing.

STEP 4 — Build a fact bank for each role and project:
  (a) the most specific technical noun for each component or decision
  (b) any number from the source description
  (c) the concrete delta: what changed, what it replaced, what it measured
Write bullets from this fact bank — not from the prose description.

━━━ RESUME ━━━

━━━ BULLET STRUCTURE ━━━

Each bullet is a single compressed statement with three elements:

  [SPECIFIC TECHNICAL NOUN] + [NUMBER OR CONCRETE SCALE] + [WHAT CHANGED OR WHAT IT REPLACED]

ONE CLAUSE ONLY. Strip subordinate clauses entirely:
  "which [allowed / enabled / provided / gave / meant / resulted in]" — cut
  "in order to [goal]" — cut
  "to support [noun]" — cut
  "enabling [users/team] to [X]" — cut
  "allowing [X] to [Y]" — cut
  "so that [outcome]" — cut
  "resulting in [outcome]" — cut
The statement before the clause should stand alone. If it doesn't, rewrite the statement,
not the clause.

LEAD WITH THE SPECIFIC TECHNICAL NOUN. The first phrase names the component, schema,
layer, or decision — not the act of building it.
  WEAK OPENING: "Built a system for managing rate limits across checkout flows"
  STRONG OPENING: "Redesigned Redis rate limiter key schema to isolate merchant/buyer/IP
                   limits, handling 40% higher throughput without increasing memory footprint"
The recruiter reads the first phrase. Make it a precise technical term.

NOUN PRECISION — mandatory. Use the most specific noun available:
  NOT "platform"    → "allocation engine", "generation pipeline", "matching service"
  NOT "system"      → "rate limiter", "tracing collector", "evaluation harness"
  NOT "tool"        → "CLI", "test harness", "profiler", "linter"
  NOT "workflow"    → "intake form", "validation pipeline", "allocation logic"
  NOT "application" → "FastAPI service", "Next.js dashboard", "admin interface"
  NOT "solution"    → name what it actually is
  NOT "pipeline"    (when more specific) → "ingestion pipeline", "CI/CD pipeline",
                    "LaTeX compilation pipeline", "SEC filing normalization pipeline"
Reserve generic nouns only when no more precise term exists for the thing described.

WORD DENSITY. Target 12-16 words. Up to 20 is acceptable if every word carries
specific technical information — meaning no word can be removed without losing
technical meaning. The test is information density, not word count.
An explanatory clause that adds 4 words of context fails this test.
A specific technology name that adds 2 words passes it.
If a bullet exceeds 20 words, find and remove the purpose or consequence clause.

STRONG VERBS. Vary across bullets. Never repeat a verb within the same section:
  Architected / Built / Replaced / Eliminated / Designed / Automated / Deployed /
  Engineered / Optimized / Shipped / Implemented / Rewrote / Benchmarked / Reduced /
  Constructed / Migrated / Instrumented / Modeled

NEVER OPEN WITH: "Worked on", "Helped", "Assisted", "Participated in",
  "Was responsible for", "Contributed to", "Supported", "Collaborated on"

BULLET REGISTER — bullets are compressed statements, not prose:
  No contractions. No first-person pronoun. No "in order to", "to ensure",
  "in an effort to" — purpose clauses. Just the technical statement.

NUMBER RULE — mandatory, not a suggestion:
  Every number from the source description MUST appear in the corresponding bullet.
  If no number exists in the source, name a concrete component count or system scope.
  Lead with numbers when they appear: "Eliminated 120+ hours" beats "Automated the process."

CEILING — 10/10 bullet:
  "Redesigned Redis rate limiter key schema to isolate merchant/buyer/IP limits
   independently, handling 40% higher throughput without increasing memory footprint."
  (14 words. Named component. Named decision. Number. Delta. Zero explanatory clauses.)

FLOOR — 7/10, currently passing but should not:
  "Built a TA matching platform with Next.js and Node.js, eliminating 120+ hours of
   manual allocation work per term for the UBC Science faculty."
  → Problems: "a TA matching platform" is generic; "for the UBC Science faculty" is padding.
  → Rewrite: "Automated TA allocation for UBC Science faculty — eliminating 120+ hours of
    manual coordinator work per term via Node.js matching engine and PostgreSQL allocation schema."

FAILING:
  "Built an automated matching system that improved efficiency"
  "Implemented a modular multi-step application workflow with schema-based validation"
  "Designed a project-selection algorithm that analyzes job description requirements"
  "Translated domain-specific datasets into computational models to support decision-making"
  (None state a specific technical noun, a number, or a concrete delta.)

━━━ EXPERIENCE SECTION ━━━

Always include both technical roles (UBC Full Stack Developer, SIMLAB Research Assistant).
Never include Old Navy / Sales Associate.

3 bullets per role ONLY if 3 strong bullets exist in the source.
Two sharp bullets beats three where the third is padding.
If a third bullet cannot pass the structure test (specific technical noun + number or
concrete scale + delta), write two bullets. A missing bullet is invisible.
A filler bullet is a red flag to any technical reviewer.

Emphasis by JD type:
- Backend role: PostgreSQL schema design, allocation logic, API architecture, data modeling
- ML/data role: graph modeling, probabilistic propagation, pipeline construction, model evaluation
- Full-stack role: both frontend architecture and backend schema/logic

━━━ PROJECTS SECTION ━━━

Include exactly the projects from selected_projects, in that order (highest JD-relevance first).
Each project: exactly 2 bullets from the source — the 2 facts most directly matching JD requirements.
Tech stack line: mirror JD vocabulary where truthful.
No project that doesn't directly address a high-weight JD requirement belongs here.

━━━ ATS KEYWORD MIRRORING ━━━

Important but secondary to compression. Keywords appear naturally as technical nouns
in strong bullets — not retrofitted with explanatory context around them.
"Built Redis-backed rate limiter" contains "Redis" as a natural technical noun.
"Implemented a system using Redis for caching to support performance goals" pads the
keyword and weakens the bullet. Extract 10-15 JD terms. They appear because the bullets
name specific systems. Exact JD terms beat synonyms everywhere they fit truthfully.
Skills section should front-load whatever the JD prioritizes.

━━━ ONE-PAGE HARD LIMIT ━━━

The resume must fit on exactly one page. Enforce through compression:
- Experience: up to 3 bullets per role (only if material exists for 3 strong ones)
- Projects: exactly 2 bullets each, 2-3 projects
- Skills: include all relevant technology groupings — a sparse skills section wastes space
- The LaTeX margins are set for one page — trust them

━━━ LANGUAGE RULES ━━━

BANNED IN RESUME BULLETS:
Structural — these create explanatory clauses:
  "which [allowed/enabled/provided/gave/meant/resulted in]"
  "in order to" / "to ensure" / "to enable" / "to support" / "to allow"
  "enabling [X] to" / "allowing [X] to" / "so that" / "resulting in"
  "in an effort to" / "with the goal of"

Nouns — use precise alternatives:
  "platform", "system", "tool", "application", "workflow", "solution" where
  a more specific term exists (see NOUN PRECISION above)

Scope adjectives that add no information:
  "comprehensive", "full", "complete", "end-to-end", "robust", "scalable",
  "modular", "reusable" — unless quoting the JD with a specific meaning

Vague phrases:
  "various [technologies/approaches]" — name the specific ones
  "improving [quality attribute]" without a number
  "support [decision/analysis/research]" — name the output, not the purpose
  "across [scope]" — replace with the specific scope
  The word "across" generally — find a specific construction

Filler:
  "AI-assisted development" as a skill
  "demonstrated", "showcased", "leveraging", "harnessing", "spearheading"
  Padding adverbs: "effectively", "successfully", "highly", "greatly", "deeply"
  Adjectival filler: "dynamic", "impactful", "innovative", "cutting-edge", "state-of-the-art"
  "passionate about", "strong foundation in", "proven track record"

COVER LETTER LANGUAGE — different register from bullets:
  Vary sentence length. Short sentences break up technical explanations.
  Say what happened directly — let the specifics carry the weight.
  Do not start two consecutive sentences with "I".

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

Run every check. Fix every failure before outputting.

RESUME:

□ OPENING NOUN: Does the first phrase of each bullet name a specific technical component,
  schema, layer, algorithm, or decision? Not "Built a system", not "Implemented a workflow",
  not "Designed a platform" — a named, specific thing: "Redis rate limiter key schema",
  "PostgreSQL many-to-many allocation schema", "tail-based sampling layer", "W3C TraceContext
  propagation interceptor", "daily SEC filing normalization pipeline."
  If the opening phrase contains "[verb] a [generic noun]", rewrite to lead with the specific noun.

□ SINGLE CLAUSE: Does any bullet contain "which", "in order to", "to support", "enabling",
  "allowing", "so that", "resulting in" as a connector between clauses?
  If yes, cut the second clause. The statement before it must stand alone. If it doesn't,
  rewrite the statement — not the clause.

□ NUMBERS PRESENT: Does every bullet covering a role or project where a number exists in
  the source description contain that number? List numbers extracted in Step 0 and verify
  each one appears. If any are missing, rewrite the bullet.

□ WORD DENSITY: Is every word in each bullet carrying specific technical meaning?
  If any word or phrase can be removed without losing technical information, remove it.
  Any bullet over 20 words must be compressed — identify and cut the purpose or
  consequence clause.

□ NOUN PRECISION: Does any bullet contain "platform", "system", "tool", "application",
  "workflow", or "solution" where a more specific term exists for the thing described?
  If yes, replace with the precise technical noun.

□ FILLER BULLET TEST: Could this bullet appear on any software engineer's resume?
  Would removing the company name make it indistinguishable from anyone else's work?
  If yes, identify the specific technical decision or number that makes it uniquely Karan's
  and rewrite around that.

□ VERB DIVERSITY: No two bullets in the same section start with the same verb.

□ ATS: Do the 10-15 highest-weight JD terms appear somewhere in the resume?
  Add as natural technical nouns, not appended explanatory context.

COVER LETTER:
□ Para 1 references something specific to this company/role that couldn't be in a generic letter
□ Para 2 names the project, the specific technical problem, the architecture decision, and a result
□ No sentence could appear in a letter written by someone with different experience
□ No banned phrase or em dash survived
□ Sentence length varies — not every sentence the same length

━━━ HARD CONSTRAINTS ━━━

These never change:
- Never invent skills, projects, or experience not present in the profile
- Never include the Old Navy / Sales Associate role
- Output only the resume body sections (Experience, Projects, Skills) — preamble, heading, \
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
                    "Example: [\"MarketMind AI\", \"TA Matching Platform\"]"
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


def _assemble_resume_latex(body: str) -> str:
    """Wrap resume body sections with the static preamble and closing tag.

    The stored resume_latex remains a complete, compilable LaTeX document.
    """
    return LATEX_PREAMBLE + _extract_resume_body(body) + "\n\n\\end{document}\n"


async def generate_materials(db: AsyncSession, jd_text: str) -> dict:
    personal = (await db.execute(select(PersonalInfo).limit(1))).scalar_one_or_none()
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
        personal, list(experience), list(projects), list(skills)
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

    result = {
        **tool_use.input,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }

    # Assemble the complete compilable document from Claude's body-only output
    if result.get("resume_latex"):
        result["resume_latex"] = _assemble_resume_latex(result["resume_latex"])

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
                    "Under 25 words. Name a specific project (MarketMind, TA platform) or exact deliverable. "
                    "No em dashes."
                ),
            },
        },
        "required": ["headline", "observed", "gap", "action"],
    },
}


async def generate_insights(
    job_summaries: list[dict],
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
            lines.append(f"  Analysis: {s['strategic_note']}")
        elif s.get("description_snippet"):
            lines.append(f"  JD excerpt: {s['description_snippet']}")

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
