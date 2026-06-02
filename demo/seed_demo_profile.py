#!/usr/bin/env python3
"""
Demo profile seeder for CareerOS showcase.

Creates a fictional candidate (Jordan Park) with four projects spanning
different technical domains. Designed so the AI project selection logic
produces visibly different results when run against the three sample JDs
in demo/sample_jds/.

  Backend JD     →  Distributed Tracing + Shopify experience
  ML/AI JD       →  LLM Eval Framework + NLP research
  Full-stack JD  →  Collaborative Editor + Shopify experience

Usage
-----
Run against a fresh demo database — do NOT point this at your real
production DATABASE_URL, as --reset will wipe all profile tables.

  # Set up a local demo DB:
  createdb careeros_demo

  # Seed it:
  DATABASE_URL=postgresql+asyncpg://localhost/careeros_demo \\
      python demo/seed_demo_profile.py

  # Re-seed (wipes and starts fresh):
  DATABASE_URL=postgresql+asyncpg://localhost/careeros_demo \\
      python demo/seed_demo_profile.py --reset

Railway / hosted demo
---------------------
Provision a separate Railway Postgres service, set DATABASE_URL to
that service's connection string, and run this script once.
"""

import asyncio
import os
import sys

# Allow running from repo root or from demo/ directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal, Base, engine
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory


async def seed_demo(reset: bool = False) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(PersonalInfo).limit(1))).scalar_one_or_none()

        if existing and not reset:
            print(
                f"Database already has profile data ({existing.name}).\n"
                "Pass --reset to wipe and re-seed with demo data.\n"
                "WARNING: --reset deletes ALL profile data in this database."
            )
            return

        if reset and existing:
            print(f"Clearing existing profile ({existing.name}) …")
            for model in [SkillCategory, Project, Experience, Education, PersonalInfo]:
                await db.execute(delete(model))
            await db.commit()

        # ── Personal info ──────────────────────────────────────────────────────

        db.add(PersonalInfo(
            name="Jordan Park",
            email="jordan.park@example.com",
            phone="+1 (416) 555-0182",
            linkedin="linkedin.com/in/jordan-park-dev",
            github="github.com/jordanpark-dev",
            location="Waterloo, ON, Canada (open to remote)",
            target_roles=[
                "software engineer",
                "backend engineer",
                "ml engineer",
                "full stack engineer",
            ],
            target_locations=["Canada", "Remote", "United States"],
            cover_letter_voice=(
                "Direct and technical. I open on the role or the problem, not on myself. "
                "Short sentences. I don't soften claims — if I built something, I say what "
                "it does and what it changed. I avoid filler like 'passionate about' or "
                "'excited to contribute'. I write like I'm explaining the system to someone "
                "who will ask hard follow-up questions."
            ),
        ))

        # ── Education ──────────────────────────────────────────────────────────

        db.add(Education(
            school="University of Waterloo",
            degree="BSc Computer Science",
            field="Computer Science",
            minor="Statistics",
            start_date="Sep 2021",
            end_date="Apr 2025",
        ))

        # ── Experience ─────────────────────────────────────────────────────────

        for exp in [
            Experience(
                company="Shopify",
                role="Software Engineer Intern",
                start_date="May 2024",
                end_date="Aug 2024",
                location="Remote",
                description=(
                    "Worked on the payments infrastructure team, specifically on the rate limiting "
                    "and abuse prevention layer that sits in front of high-throughput checkout flows. "
                    "The existing rate limiter was a Redis-backed token bucket implementation that "
                    "couldn't differentiate between merchant-level, buyer-level, and IP-level limits "
                    "simultaneously — all limits shared the same key namespace and interfered with "
                    "each other during traffic spikes. Redesigned the key schema and sliding window "
                    "algorithm to support multi-dimensional limits independently without contention. "
                    "The new design handled 40% higher sustained throughput in load tests without "
                    "increasing Redis memory footprint. Built the change behind a feature flag, "
                    "rolled it out to 5% of traffic for two weeks, and promoted to full traffic after "
                    "no regression in false-positive rate. Service is written in Go; changes deployed "
                    "via Kubernetes with canary rollout tooling the team had already built."
                ),
                sort_order=0,
            ),
            Experience(
                company="Waterloo NLP Lab",
                role="Research Assistant",
                start_date="Sep 2023",
                end_date="Apr 2024",
                location="Waterloo, ON",
                description=(
                    "Contributed to a research project on information extraction from legal documents — "
                    "specifically, extracting named entities (parties, dates, obligations, jurisdictions) "
                    "from contract text where the entity boundaries are ambiguous and domain vocabulary "
                    "differs substantially from general-domain NLP corpora. Fine-tuned BERT and Legal-BERT "
                    "on a labeled dataset of 4,200 contracts assembled from court filings. The primary "
                    "challenge was label consistency: different annotators classified the same spans "
                    "differently for nested entity types. Implemented an inter-annotator agreement "
                    "measurement pipeline (Cohen's kappa per entity class) and ran two re-annotation "
                    "rounds that improved kappa from 0.61 to 0.84 on the ambiguous classes. Final model "
                    "achieved F1 of 0.91 on the test split, up from the 0.79 baseline. Built the full "
                    "training and evaluation pipeline in Python with PyTorch and the Hugging Face "
                    "Transformers library."
                ),
                sort_order=1,
            ),
        ]:
            db.add(exp)

        # ── Projects ───────────────────────────────────────────────────────────

        for project in [
            Project(
                name="Distributed Tracing System",
                start_date="Jan 2025",
                end_date="Apr 2025",
                github_url="https://github.com/jordanpark-dev/dist-trace",
                description=(
                    "Built a distributed tracing system from scratch to understand where latency "
                    "accumulates in a microservices benchmark environment. The core challenge was context "
                    "propagation: when a request fans out across services, each hop needs to carry the "
                    "original trace ID without the application code being aware of it. Implemented "
                    "W3C TraceContext propagation via gRPC metadata interceptors and HTTP middleware, "
                    "so instrumentation is transparent to service code. Traces are collected by a "
                    "custom collector agent (Go) that batches spans locally, compresses them, and "
                    "forwards to a Jaeger backend over gRPC. The sampling layer supports head-based "
                    "and tail-based strategies — tail-based sampling buffers spans in Redis until the "
                    "full trace arrives, then makes the keep/drop decision on complete trace data rather "
                    "than on the first span. This catches latency outliers that head-based sampling "
                    "misses. Benchmarked against OpenTelemetry Collector: comparable throughput "
                    "(120k spans/sec on a single node) with 35% lower memory footprint due to more "
                    "aggressive span compaction. Written in Go; PostgreSQL stores trace metadata for "
                    "querying; Grafana dashboards for visualization."
                ),
                sort_order=0,
            ),
            Project(
                name="LLM Evaluation Framework",
                start_date="Oct 2024",
                end_date="Dec 2024",
                github_url="https://github.com/jordanpark-dev/llm-eval",
                description=(
                    "Built an evaluation framework for instruction-following language models that goes "
                    "beyond accuracy metrics to measure factuality, refusal calibration, and instruction "
                    "adherence on multi-turn conversations. The motivation: standard benchmarks measure "
                    "knowledge but not whether a model follows constraints ('respond only in JSON', "
                    "'do not mention competitors') reliably under paraphrasing. Framework has three "
                    "evaluation tracks: (1) factuality — retrieved documents are injected into context "
                    "and answers are verified against them using an entailment model; (2) constraint "
                    "adherence — prompts with explicit formatting or topic constraints are tested across "
                    "30+ paraphrase variants generated with back-translation; (3) calibration — "
                    "refusal rate on out-of-scope queries versus in-scope queries, measuring whether "
                    "the model refuses the right things. Results are logged to PostgreSQL and surfaced "
                    "via a FastAPI + React dashboard. Ran evaluation suites against GPT-4o, Claude 3.5 "
                    "Sonnet, and Llama 3.1 70B. Found that all three models had constraint adherence "
                    "drop-off above 4 simultaneous constraints, with different failure modes. "
                    "Framework used in two lab papers as the evaluation methodology."
                ),
                sort_order=1,
            ),
            Project(
                name="Real-time Collaborative Editor",
                start_date="Jun 2024",
                end_date="Sep 2024",
                github_url="https://github.com/jordanpark-dev/collab-edit",
                description=(
                    "Built a browser-based collaborative text editor that supports concurrent editing "
                    "without conflicts — users see each other's changes in real time and the document "
                    "converges to the same state for all clients regardless of network order. The "
                    "conflict resolution uses CRDTs (specifically Yjs) rather than operational "
                    "transformation: each character has a globally unique ID and a causal ordering, "
                    "so concurrent insertions at the same position are deterministically ordered "
                    "without a central coordinator making decisions. The WebSocket server (Node.js) "
                    "acts as a relay — it does not arbitrate conflicts, just broadcasts changes. This "
                    "means the server is stateless with respect to document content and can be "
                    "horizontally scaled. Presence (cursor positions, user avatars) is handled "
                    "separately via a lightweight awareness protocol layered on top of the sync "
                    "channel. Offline support: changes made while disconnected are stored in "
                    "IndexedDB and merged on reconnect using the same CRDT merge operation. "
                    "Frontend: TypeScript and React. Handles documents up to 500k characters with "
                    "no perceptible lag on mid-range hardware."
                ),
                sort_order=2,
            ),
            Project(
                name="Wildfire Risk Prediction Pipeline",
                start_date="Feb 2024",
                end_date="May 2024",
                description=(
                    "Built a machine learning pipeline to predict short-term wildfire spread risk "
                    "from satellite imagery and historical weather data. Dataset assembled from 10 "
                    "years of MODIS fire detection records, VIIRS surface reflectance (vegetation "
                    "index as a fuel proxy), and ERA5 reanalysis weather data (wind speed, humidity, "
                    "temperature). The core modeling challenge was spatial autocorrelation: adjacent "
                    "grid cells share weather and vegetation characteristics, so random train/test "
                    "splits leak information and produce optimistically biased accuracy. Used "
                    "spatial block cross-validation (blocks of 50km x 50km withheld as test folds) "
                    "to get honest generalization estimates. Compared random forest, gradient boosting, "
                    "and a simple CNN on rasterized inputs. Random forest with spatial CV gave the most "
                    "honest estimate (AUC 0.81); the CNN scored 0.91 on random splits but 0.74 on "
                    "spatial splits — a 17-point gap that would have gone unnoticed without the spatial "
                    "validation. Pipeline built in Python: GeoPandas for spatial joins, rasterio for "
                    "satellite data, scikit-learn for models, PostgreSQL + PostGIS for storing predictions."
                ),
                sort_order=3,
            ),
        ]:
            db.add(project)

        # ── Skills ─────────────────────────────────────────────────────────────

        for skill in [
            SkillCategory(
                category="Languages",
                items=["Python", "Go", "TypeScript", "JavaScript", "R", "SQL"],
                sort_order=0,
            ),
            SkillCategory(
                category="ML / AI",
                items=["PyTorch", "Hugging Face Transformers", "scikit-learn", "NumPy", "Pandas"],
                sort_order=1,
            ),
            SkillCategory(
                category="Backend & Infra",
                items=["FastAPI", "Node.js", "gRPC", "Redis", "Kafka", "Docker", "Kubernetes"],
                sort_order=2,
            ),
            SkillCategory(
                category="Frontend",
                items=["React", "Next.js", "WebSockets", "TypeScript"],
                sort_order=3,
            ),
            SkillCategory(
                category="Databases",
                items=["PostgreSQL", "PostGIS", "Redis", "MongoDB"],
                sort_order=4,
            ),
        ]:
            db.add(skill)

        await db.commit()
        print("Demo profile seeded successfully.")
        print("Candidate: Jordan Park")
        print("Projects:  Distributed Tracing · LLM Eval Framework · Collaborative Editor · Wildfire Pipeline")
        print("\nNext: paste the JDs in demo/sample_jds/ to see project selection in action.")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    if reset:
        print("WARNING: --reset will delete ALL profile data in the target database.")
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)
    asyncio.run(seed_demo(reset=reset))
