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
                    "Built a TA matching platform that automated course assistant allocation across UBC's Science faculty "
                    "using Next.js, React, and Node.js. The system replaced a manual spreadsheet process that consumed "
                    "120+ hours of coordination work per academic term. Designed a multi-step form workflow with "
                    "schema-based validation to capture preferences from both students and coordinators. Implemented the "
                    "allocation logic server-side, triggered from an admin interface that gave coordinators visibility "
                    "into the matching results before finalizing. Dockerized the PostgreSQL database with many-to-many "
                    "relationship tables linking courses, teaching assistants, and assignment records."
                ),
                sort_order=0,
            ),
            Experience(
                company="UBC SIMLAB",
                role="Research Assistant",
                start_date="May 2024",
                end_date="Aug 2024",
                description=(
                    "Built spatial graph models to simulate wildfire spread across terrain with varying vegetation types, "
                    "powerline corridor networks, and infrastructure assets. Each node in the graph represents a geographic "
                    "unit with associated fire risk properties; edges encode adjacency and wind-driven spread probabilities. "
                    "Implemented probabilistic fire propagation algorithms that traverse the graph and accumulate risk "
                    "scores for downstream infrastructure nodes. Used the outputs to quantify which powerline segments "
                    "face the highest ignition exposure under different wind scenarios, producing a ranked list of "
                    "at-risk infrastructure for utility operators."
                ),
                sort_order=1,
            ),
        ]:
            db.add(exp)

        for project in [
            Project(
                name="MarketMind AI",
                start_date="Dec 2025",
                end_date=None,
                description=(
                    "Investment intelligence platform built on a multi-agent pipeline that ingests SEC filings, "
                    "earnings releases, and market data on a daily schedule. Architecture separates signal extraction "
                    "from presentation: ingestion agents fetch and parse filings, analysis agents score thesis confidence "
                    "and track drift over time, and a retrieval layer (Qdrant vector search plus Redis caching) serves "
                    "queries to the Next.js frontend. Backend built with FastAPI and PostgreSQL for persistent state, "
                    "with Ollama running local LLMs for on-premise analysis tasks. The design tracks signals temporally "
                    "rather than giving one-shot answers: confidence scores strengthen or decay as new filings arrive, "
                    "giving the portfolio view a time dimension that retrieval-only systems lack. Deployed with Docker Compose."
                ),
                sort_order=0,
            ),
            Project(
                name="Agentic Market Sentiment System",
                start_date="Dec 2025",
                end_date="Dec 2025",
                description=(
                    "Multi-agent research system that compresses manual stock research from hours to minutes per query. "
                    "Specialist agents handle market data (YFinance API), news aggregation (DuckDuckGo search), and "
                    "sentiment scoring independently. A coordinator agent synthesizes their outputs into a structured "
                    "report with 100+ data points per query: price history, momentum indicators, news volume, sentiment "
                    "trend, and sector context. Built on Python with Groq AI for fast inference and a FastAPI interface "
                    "for programmatic access. Reduced manual research time by 70% compared to checking each data source "
                    "individually."
                ),
                sort_order=1,
            ),
            Project(
                name="FDA Cancer Drug-Protein Network Analysis",
                start_date="Nov 2025",
                end_date="Nov 2025",
                description=(
                    "Built a bipartite drug-protein interaction network by joining FDA oncology approval datasets with "
                    "BioGRID protein-protein interaction (PPI) data. The resulting graph connects approved cancer drugs "
                    "to their protein targets, then links those targets into the broader interaction network. Applied "
                    "centrality analysis (degree, betweenness, eigenvector) using the igraph library in R to identify "
                    "hub proteins appearing across multiple drug-sensitivity pathways. The analysis surfaced proteins "
                    "with high betweenness centrality across oncology drug classes, flagging them as candidate "
                    "cross-drug resistance mechanisms worth further investigation."
                ),
                sort_order=2,
            ),
        ]:
            db.add(project)

        for skill in [
            SkillCategory(category="Languages", items=["Python", "JavaScript", "Java", "C++", "R"], sort_order=0),
            SkillCategory(category="Frameworks", items=["React", "Next.js", "Node.js", "Express.js", "FastAPI", "Docker"], sort_order=1),
            SkillCategory(category="Databases", items=["PostgreSQL", "MongoDB", "MySQL"], sort_order=2),
            SkillCategory(category="Tools", items=["Git", "Jupyter", "Pandas", "NumPy", "Matplotlib", "TensorFlow", "PyTorch"], sort_order=3),
        ]:
            db.add(skill)

        await db.commit()
        print("Seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
