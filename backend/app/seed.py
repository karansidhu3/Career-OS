import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, engine
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(PersonalInfo).limit(1))).scalar_one_or_none()
        if existing:
            print("Already seeded, skipping.")
            return

        db.add(PersonalInfo(
            name="Karanveer Sidhu",
            email="karansidhu5550@gmail.com",
            phone="+1 (250) 509-2500",
            linkedin="linkedin.com/in/karan-sidhu3",
            github="github.com/karansidhu3",
            location="Kelowna, BC, Canada",
            target_roles=[
                "software engineer",
                "full stack engineer",
                "backend engineer",
                "data engineer",
                "ai engineer",
            ],
            target_locations=["Canada", "Remote", "British Columbia"],
        ))

        db.add(Education(
            school="University of British Columbia",
            degree="BSc Computer Science",
            field="Computer Science",
            minor="Data Science",
            start_date="Sep 2022",
            end_date="Jun 2026",
        ))

        for exp in [
            Experience(
                company="UBC",
                role="Full Stack Developer",
                start_date="May 2025",
                end_date="Aug 2025",
                description=(
                    "Built a TA matching and allocation platform for UBC's Science faculty that replaced a manual "
                    "spreadsheet process coordinators ran every term. The old process required emailing students, "
                    "collecting preferences by hand, and manually slotting TAs into courses — consuming 120+ hours "
                    "of coordinator time per academic term. Built the frontend in React and Next.js with TypeScript: "
                    "a multi-step application form with schema-based validation that captured student preferences, "
                    "availability, and course priorities, then routed submissions into a PostgreSQL database. The "
                    "allocation logic ran server-side on Node.js and matched TAs to courses based on preferences and "
                    "enrollment constraints, surfacing results in an admin dashboard before coordinators finalized "
                    "assignments. Designed the database schema with normalized many-to-many relationship tables "
                    "linking students, courses, preferences, and assignment records. Dockerized the PostgreSQL "
                    "instance and wrote the schema migrations. The system was deployed and used for actual TA "
                    "allocation in the Science faculty."
                ),
                sort_order=0,
            ),
            Experience(
                company="UBC SIMLAB",
                role="Research Assistant",
                start_date="May 2024",
                end_date="Aug 2024",
                description=(
                    "Worked on a wildfire spread simulation project for a research group studying infrastructure "
                    "risk from fire. The problem: model how fire moves through real terrain and quantify which "
                    "powerline segments and utility assets are most exposed under different ignition scenarios. "
                    "Built spatial graph representations of the study area where each node encodes a geographic "
                    "unit with terrain type, vegetation density, and fuel load properties, and each edge encodes "
                    "adjacency weighted by wind-driven spread probability. Implemented probabilistic propagation "
                    "algorithms that traverse the graph and accumulate ignition exposure scores at each node, "
                    "accounting for multiple wind direction scenarios in parallel. The outputs ranked powerline "
                    "segments and infrastructure assets by expected fire exposure, giving utility operators a "
                    "prioritized list for hardening decisions. Translated raw GIS datasets (terrain, vegetation "
                    "classification, grid topology) into the graph format and validated the model outputs against "
                    "known historical fire behavior in the study region."
                ),
                sort_order=1,
            ),
        ]:
            db.add(exp)

        for project in [
            Project(
                name="CareerOS",
                start_date="Jun 2026",
                end_date=None,
                github_url="https://github.com/karansidhu3/Career-OS",
                description=(
                    "Built a job application generation system that takes a pasted job description and produces a "
                    "tailored resume and cover letter in about 20 seconds. The problem it solves: manually rewriting "
                    "a resume for each application in ChatGPT takes 12+ steps and produces inconsistent results. "
                    "CareerOS compresses that to a single paste and a keypress. The backend is a Python FastAPI "
                    "service that stores a persistent candidate profile in PostgreSQL (experience, projects, skills) "
                    "and sends it alongside the job description to Claude (claude-sonnet-4-6) on each generation. "
                    "The prompt engineering layer extracts the 10-15 highest-weight JD requirements, maps them to "
                    "the stored profile, selects the 2-3 most relevant projects, mirrors ATS keywords exactly, and "
                    "outputs a complete compilable LaTeX document. LaTeX is compiled server-side via Tectonic and "
                    "served as a PDF. Generation runs as a background task so the HTTP response returns immediately "
                    "and the frontend polls — this was necessary to stay inside Railway's proxy timeout while "
                    "allowing 30-90 second generation times. Prompt caching on the system prompt and profile reduces "
                    "token costs by approximately 80% on repeat generations. Frontend is Next.js 16 with React 19 "
                    "and Framer Motion. Deployed on Railway with a Docker-based build that installs Tectonic at "
                    "image build time."
                ),
                sort_order=0,
            ),
            Project(
                name="MarketMind AI",
                start_date="Dec 2025",
                end_date=None,
                description=(
                    "Investment intelligence platform that ingests SEC filings, earnings releases, and trade "
                    "publications on a daily automated schedule and extracts structured signals for portfolio "
                    "tracking. The core design decision: treat signals temporally rather than giving one-shot "
                    "answers. Each company gets a thesis confidence score that strengthens or decays as new "
                    "filings arrive, so the portfolio view shows direction of evidence, not just current state. "
                    "Architecture uses a multi-agent Python pipeline: ingestion agents fetch and normalize "
                    "filings, analysis agents score confidence and detect drift, and a retrieval layer using "
                    "Qdrant vector search and Redis caching serves queries to the Next.js frontend. Backend "
                    "built with FastAPI and PostgreSQL for persistent signal state. Local LLM inference runs "
                    "on Ollama to keep analysis on-premise. Deployed with Docker Compose. The platform handles "
                    "daily ingestion without manual intervention and surfaces thesis changes as new disclosures "
                    "arrive."
                ),
                sort_order=1,
            ),
            Project(
                name="Agentic Market Sentiment System",
                start_date="Dec 2025",
                end_date="Dec 2025",
                description=(
                    "Multi-agent research system that compresses manual stock research from hours to minutes. "
                    "The problem: getting a complete picture of a single stock requires checking price data, "
                    "recent news, and sentiment signals from separate sources and synthesizing them manually. "
                    "Built four specialist agents that work in parallel: one queries YFinance for price history "
                    "and momentum indicators, one runs DuckDuckGo news searches and extracts headlines, one "
                    "scores sentiment trend from news volume and tone, and a coordinator agent synthesizes all "
                    "three into a structured report. Each report contains 100+ data points: price history, "
                    "momentum indicators, news volume by week, sentiment trend, and sector context. Built on "
                    "Python with Groq AI for fast inference and a FastAPI interface for programmatic access. "
                    "Reduced manual research time by 70% compared to checking each source individually."
                ),
                sort_order=2,
            ),
            Project(
                name="FDA Cancer Drug-Protein Network Analysis",
                start_date="Nov 2025",
                end_date="Nov 2025",
                description=(
                    "Built a bipartite drug-protein interaction network by joining FDA oncology drug approval "
                    "records with BioGRID protein-protein interaction (PPI) data. The network connects approved "
                    "cancer drugs to their known protein targets, then links those targets into the broader "
                    "protein interaction graph. The analysis question: which proteins sit at structural "
                    "bottlenecks across multiple drug-sensitivity pathways, making them candidates for "
                    "cross-drug resistance mechanisms? Applied degree, betweenness, and eigenvector centrality "
                    "analysis using the igraph library in R to identify hub proteins that appear in pathways "
                    "targeted by multiple distinct drug classes. High-betweenness proteins in this network are "
                    "candidates for resistance mechanisms that span drug classes — clinically relevant because "
                    "resistance to one drug that operates through a hub protein may confer partial resistance "
                    "to others targeting the same pathway. Built in R with igraph and tidyverse; network data "
                    "assembled from FDA oncology datasets and BioGRID PPI records."
                ),
                sort_order=3,
            ),
        ]:
            db.add(project)

        for skill in [
            SkillCategory(category="Languages", items=["Python", "TypeScript", "JavaScript", "Java", "C++", "R", "SQL"], sort_order=0),
            SkillCategory(category="Frontend", items=["React", "Next.js", "Tailwind CSS", "Framer Motion"], sort_order=1),
            SkillCategory(category="Backend", items=["FastAPI", "Node.js", "RESTful APIs", "SQLAlchemy", "Docker"], sort_order=2),
            SkillCategory(category="Databases", items=["PostgreSQL", "Redis", "Qdrant", "MongoDB"], sort_order=3),
            SkillCategory(category="ML / Data", items=["PyTorch", "scikit-learn", "Pandas", "NumPy", "Ollama", "Claude API"], sort_order=4),
            SkillCategory(category="Tools", items=["Git", "GitHub Actions", "Docker Compose", "Jupyter", "Linux"], sort_order=5),
        ]:
            db.add(skill)

        await db.commit()
        print("Seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
