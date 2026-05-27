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

        for i, exp in enumerate([
            Experience(
                company="UBC",
                role="Full Stack Developer",
                start_date="May 2025",
                end_date="Aug 2025",
                bullets=[
                    "Built TA matching platform with Next.js, React, Node.js; automated allocation across Science faculty; reduced 120+ hours of manual work per term",
                    "Designed multi-step form workflow with schema-based validation",
                    "Dockerized PostgreSQL schema with many-to-many relationships",
                ],
                sort_order=0,
            ),
            Experience(
                company="UBC SIMLAB",
                role="Research Assistant",
                start_date="May 2024",
                end_date="Aug 2024",
                bullets=[
                    "Built spatial graph models for wildfire spread simulation (terrain, vegetation, powerline networks)",
                    "Implemented graph algorithms for probabilistic fire propagation and infrastructure risk quantification",
                ],
                sort_order=1,
            ),
        ]):
            db.add(exp)

        for project in [
            Project(
                name="MarketMind AI",
                tech=["Python", "FastAPI", "Next.js", "React", "PostgreSQL", "Redis", "Qdrant", "Ollama", "Docker"],
                start_date="Dec 2025",
                end_date=None,
                bullets=[
                    "Persistent investment intelligence platform; multi-agent pipeline ingesting SEC filings daily",
                    "Temporal signal tracking across months; emergence velocity not retrieval",
                    "Thesis confidence scoring, company radar, portfolio alignment layer",
                    "Production Docker Compose stack; local LLM pipeline at scale",
                ],
                sort_order=0,
            ),
            Project(
                name="Agentic Market Sentiment System",
                tech=["Python", "Groq AI", "YFinance API", "DuckDuckGo", "FastAPI"],
                start_date="Dec 2025",
                end_date="Dec 2025",
                bullets=[
                    "Multi-agent AI system; reduced manual research time by 70%",
                    "Agents for market data, news, sentiment; 100+ structured data points per query",
                ],
                sort_order=1,
            ),
            Project(
                name="FDA Cancer Drug–Protein Network Analysis",
                tech=["R", "igraph", "tidyverse"],
                start_date="Nov 2025",
                end_date="Nov 2025",
                bullets=[
                    "Bipartite drug–protein network from FDA oncology datasets + BioGRID PPI network",
                    "Centrality and hub analysis for drug sensitivity/resistance pathways",
                ],
                sort_order=2,
            ),
            # Movie Recommendation Engine removed — Karan will replace with a stronger project
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
