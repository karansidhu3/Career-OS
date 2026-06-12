#!/usr/bin/env python3
"""
Demo jobs seeder for CareerOS showcase.

Wipes all existing job records and seeds 9 historical applications with
realistic statuses, companies, fit scores, strategic notes, and timestamps.

The applications are designed so the candidacy insights surface a real,
specific pattern: AWS/GCP/Azure experience is absent across every backend
and infrastructure JD — a plausible and fixable gap for a student whose
infra exposure is all Shopify-managed or local Docker.

Usage
-----
From the repo root (make sure the backend virtualenv is active):

    DATABASE_URL=postgresql+asyncpg://careeros:demopass@localhost:5433/careeros_demo \\
        python demo/seed_demo_jobs.py

    # Preview without changing anything:
        python demo/seed_demo_jobs.py --dry-run
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import delete
from app.database import AsyncSessionLocal, Base, engine
from app.models.job import Job


def ago(days: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ─── Application data ─────────────────────────────────────────────────────────
#
# strategic_note uses the parsed format:
#   GOOD FIT\n• …\n\nGAPS\n• …\n\nIMPROVEMENT PLAN\n• …
#
# The first GAP bullet appears as the signal line in the applications list row.
# All notes encode the same consistent gap (no cloud provider experience) so
# candidacy insights produce a sharp, specific headline after analyzing them.

APPLICATIONS = [

    # ── 1 ─ Meridian Payments · Backend Systems Engineer ─ INTERVIEW ──────────
    #        The hero application. First interview = amber marker.
    {
        "title": "Backend Systems Engineer",
        "company": "Meridian Payments",
        "status": "interview",
        "fit_score": 9,
        "created_at": ago(21),
        "fit_rationale": [
            "Distributed Tracing project covers W3C TraceContext, Jaeger, tail-based sampling, and 120k span/sec — core JD requirements met directly.",
            "Shopify internship demonstrates production Go, Redis rate limiting, and feature-flag rollout — exactly the systems Meridian is rebuilding.",
            "Tail-based sampling knowledge addresses the JD bonus criteria; most candidates won't be able to speak to it.",
        ],
        "selected_projects": ["Distributed Tracing System", "LLM Evaluation Framework"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Distributed Tracing project covers the JD's core requirements with unusual precision: W3C TraceContext propagation, Jaeger backend, tail-based vs head-based sampling tradeoffs, and 120k span/sec throughput are all either named or directly implied.\n"
            "• Shopify internship demonstrates production Go and a Redis-backed multi-dimensional rate limiter — the exact system Meridian describes rebuilding. Deploying behind a feature flag to 5% traffic and promoting after no false-positive regression is the kind of production discipline the JD signals it values.\n"
            "• Tail-based sampling design directly addresses the JD's bonus criterion; this is not a common topic and will make the application stand out.\n"
            "\nGAPS\n"
            "• No direct AWS or GCP experience — all infrastructure is either Shopify-managed or local Docker. Meridian runs on AWS and the interview will surface this gap.\n"
            "• Kubernetes exposure is Shopify intern-level only. No owned cluster configurations, Helm charts, or Terraform modules appear anywhere in the profile.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Add a Prometheus /metrics endpoint to the Distributed Tracing project and mention it in the bullet — the JD lists Prometheus in its stack.\n"
            "• Prepare a concrete AWS answer: map the Shopify deployment model (EKS, ECR, ALB) to what you would own independently at Meridian."
        ),
        "cover_letter": (
            "The backend systems role at Meridian caught my attention because it describes the exact infrastructure problem I spent my last project building: "
            "a tracing system where the real engineering is in the sampling layer, not the data collection.\n\n"
            "My Distributed Tracing project implements W3C TraceContext propagation, a custom collector in Go, and a tail-based sampling strategy that buffers spans in Redis "
            "until the full trace arrives before making keep/drop decisions. That last piece is what the JD's bonus criteria is pointing at. "
            "Most tracing setups use head-based sampling because it's simpler; the tail-based design costs more but catches the latency outliers that matter. "
            "I benchmarked it against OpenTelemetry Collector and hit comparable throughput at 35% lower memory footprint due to more aggressive span compaction.\n\n"
            "At Shopify, I rebuilt a Redis-backed rate limiter on the payments team: redesigned the key schema and sliding window algorithm to support "
            "multi-dimensional limits without contention, deployed behind a feature flag to 5% of traffic, and promoted after two clean weeks. "
            "The system Meridian is describing is structurally similar. I am graduating in April 2025 and open to the Toronto office or remote."
        ),
        "description": (
            "# Backend Systems Engineer — Meridian Payments\n\n"
            "Meridian's payments platform processes 4M+ transactions per day across 60 currencies. "
            "We're looking for a backend engineer to join the infrastructure team and work on rate limiting, "
            "distributed tracing, latency analysis, and the observability tooling that helps us find problems "
            "before customers do.\n\n"
            "**What you'll do:** Design and maintain rate limiting and abuse detection systems for high-throughput "
            "payment flows. Build and own the distributed tracing pipeline — spans, sampling strategies, alerting. "
            "Instrument services for latency profiling. Write Go services that are correct under concurrent load.\n\n"
            "**What we're looking for:** Distributed tracing experience (OpenTelemetry, Jaeger, or similar). "
            "Go proficiency. Redis for more than caching. Kubernetes at the service level.\n\n"
            "**Stack:** Go, Redis, Kafka, PostgreSQL, Kubernetes, Prometheus, Jaeger, Grafana\n\n"
            "**Location:** Remote (Canada or US) or Toronto office"
        ),
    },

    # ── 2 ─ Vault Infrastructure · Distributed Systems Engineer ─ APPLIED ─────
    {
        "title": "Distributed Systems Engineer",
        "company": "Vault Infrastructure",
        "status": "applied",
        "fit_score": 9,
        "created_at": ago(16),
        "fit_rationale": [
            "Distributed Tracing project demonstrates OpenTelemetry, gRPC, and high-throughput span processing — the exact stack Vault uses.",
            "Go experience spans both Shopify internship and personal project, satisfying the primary language requirement.",
            "Tail-based sampling knowledge and trace storage architecture directly relevant to Vault's product.",
        ],
        "selected_projects": ["Distributed Tracing System"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Distributed Tracing project hits four of Vault's six core requirements directly: OpenTelemetry, gRPC, Jaeger-compatible backend, and high-throughput span ingestion at 120k spans/sec.\n"
            "• Go experience across Shopify internship and the tracing project satisfies the primary language requirement with production and personal-project evidence.\n"
            "• The tail-based sampling architecture — buffering spans in Redis before making keep/drop decisions on complete trace data — directly addresses Vault's stated technical challenge.\n"
            "\nGAPS\n"
            "• No AWS, GCP, or Azure cloud provider experience. Vault runs its entire infrastructure on AWS; this gap will appear in every technical screen at an infra-focused company.\n"
            "• No Terraform or infrastructure-as-code experience in the profile. Vault lists it as preferred and likely expects it for this seniority level.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Add a minimal Terraform module to the Distributed Tracing repo that provisions the core AWS resources (VPC, EKS cluster, ECR registry) — directly closes the gap with working code.\n"
            "• Mention the Grafana dashboard built for the tracing project; Vault's stack lists Grafana and it demonstrates the full observability loop."
        ),
        "cover_letter": (
            "Vault's distributed systems engineer role is a direct match for the system I built this past semester.\n\n"
            "My Distributed Tracing project implements the full observability pipeline: W3C TraceContext propagation via gRPC interceptors, "
            "a custom collector agent that batches and compresses spans, and a tail-based sampler that buffers in Redis and decides on complete trace data. "
            "I built it specifically because I wanted to understand where the interesting tradeoffs live — the sampling layer, not the collection layer. "
            "Benchmarked against OpenTelemetry Collector: comparable throughput at 35% lower memory.\n\n"
            "The Go experience comes from both sides: the Shopify internship (production rate limiting service on the payments team, deployed to real traffic) "
            "and the tracing project itself. I understand the concurrency model and what it means to write code that is correct under load, not just fast on benchmarks. "
            "Graduating April 2025, open to remote or Vancouver office."
        ),
        "description": (
            "# Distributed Systems Engineer — Vault Infrastructure\n\n"
            "Vault builds observability infrastructure for high-throughput distributed systems. "
            "We're looking for an engineer who understands tracing, metrics, and log aggregation at the systems level — "
            "not just how to use the tools, but how they work and where they break.\n\n"
            "**What you'll do:** Design and implement the core data pipeline: span ingestion, sampling, storage, and querying. "
            "Build Go services that process millions of spans per minute. Own the reliability of the observability platform itself.\n\n"
            "**What we're looking for:** Go. OpenTelemetry or similar tracing experience. Understanding of distributed consensus and consistency tradeoffs. "
            "AWS infrastructure experience. Terraform preferred.\n\n"
            "**Stack:** Go, gRPC, Kafka, S3, DynamoDB, Kubernetes on AWS, Terraform"
        ),
    },

    # ── 3 ─ Boreal AI · ML Infrastructure Engineer ─ APPLIED ────────────────
    {
        "title": "ML Infrastructure Engineer",
        "company": "Boreal AI",
        "status": "applied",
        "fit_score": 8,
        "created_at": ago(13),
        "fit_rationale": [
            "LLM Evaluation Framework demonstrates production ML evaluation pipeline — directly relevant to Boreal's core product.",
            "Python and PyTorch proficiency across two projects and academic research satisfies the ML engineering requirement.",
            "FastAPI + PostgreSQL result serving layer from the eval framework matches the infra stack.",
        ],
        "selected_projects": ["LLM Evaluation Framework", "Distributed Tracing System"],
        "strategic_note": (
            "GOOD FIT\n"
            "• LLM Evaluation Framework is a direct match: evaluation pipeline for instruction-following models measuring factuality, constraint adherence, and calibration — "
            "Boreal evaluates proprietary models on similar dimensions. Used as methodology in two lab papers.\n"
            "• Python, PyTorch, and Hugging Face Transformers experience covers the ML stack. The framework ran suites against GPT-4o, Claude 3.5 Sonnet, and Llama 3.1 70B.\n"
            "• FastAPI + PostgreSQL backend for surfacing eval results matches Boreal's serving infrastructure.\n"
            "\nGAPS\n"
            "• No GCP or AWS experience. Boreal's training and inference infrastructure is entirely GCP-based; this is a real gap for an ML infra role.\n"
            "• No experience with distributed training (multi-GPU or multi-node setups). The JD asks for experience with training pipelines at scale.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Reframe the eval framework bullet to emphasize the pipeline engineering — data ingestion, parallel evaluation jobs, result aggregation — rather than just the methodology.\n"
            "• Address the distributed training gap honestly in the cover letter; emphasize infra engineering strengths over model training experience."
        ),
        "cover_letter": (
            "Boreal's ML infrastructure role connects directly to the evaluation work I built this past term.\n\n"
            "My LLM Evaluation Framework runs structured evaluation suites against instruction-following models — measuring factuality against retrieved documents, "
            "constraint adherence across paraphrase variants, and refusal calibration on out-of-scope queries. "
            "I ran it against GPT-4o, Claude 3.5 Sonnet, and Llama 3.1 70B and found consistent constraint adherence drop-off above four simultaneous constraints, "
            "with different failure modes per model. The framework is used as evaluation methodology in two lab papers.\n\n"
            "The infrastructure layer is what I'm most interested in: parallel evaluation jobs, "
            "result aggregation into PostgreSQL, and a FastAPI dashboard for querying results across model versions and evaluation dimensions. "
            "I don't have GCP production experience but I understand the evaluation pipeline problem well and can ramp on the infrastructure. "
            "Open to discussing further — graduating April 2025."
        ),
        "description": (
            "# ML Infrastructure Engineer — Boreal AI\n\n"
            "Boreal builds evaluation and monitoring infrastructure for large language models in production. "
            "We're looking for an engineer who understands both the ML and the systems sides — building pipelines that evaluate models "
            "continuously, catch regressions, and surface meaningful signals.\n\n"
            "**What you'll do:** Build and maintain the evaluation pipeline. "
            "Design distributed evaluation jobs that run across our model fleet. "
            "Instrument model serving infrastructure for latency and quality monitoring.\n\n"
            "**What we're looking for:** Python. PyTorch or JAX. GCP infrastructure experience. "
            "Experience with large-scale distributed training or inference pipelines preferred.\n\n"
            "**Stack:** Python, PyTorch, GCP (GKE, Vertex AI, GCS), Kubernetes, FastAPI"
        ),
    },

    # ── 4 ─ Flowstate · Backend Engineer ─ APPLIED ────────────────────────────
    {
        "title": "Backend Engineer",
        "company": "Flowstate",
        "status": "applied",
        "fit_score": 8,
        "created_at": ago(10),
        "fit_rationale": [
            "Collaborative Editor demonstrates real-time systems design at depth: CRDTs, WebSocket relay, stateless server architecture, offline-first merge.",
            "Shopify internship shows production backend engineering with deployment and rollout experience.",
            "TypeScript and Node.js proficiency matches the primary stack.",
        ],
        "selected_projects": ["Real-time Collaborative Editor", "Distributed Tracing System"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Collaborative Editor demonstrates the exact architecture Flowstate needs: CRDTs for conflict-free concurrent editing, stateless WebSocket relay for horizontal scaling, "
            "offline-first merge via IndexedDB. The system handles 500k-character documents with no perceptible lag.\n"
            "• TypeScript and Node.js across two projects satisfies the primary stack requirement.\n"
            "• Shopify internship shows production backend discipline: feature flags, incremental rollouts, monitoring during promotion.\n"
            "\nGAPS\n"
            "• No AWS or cloud deployment experience for any personal project. Flowstate deploys on AWS; the infra knowledge gap will surface when discussing the production architecture.\n"
            "• No previous developer tools domain experience. Flowstate's product is a developer workflow tool; domain context helps but isn't required.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Lead the application with the CRDT architecture decision — most candidates applying to a real-time system role won't have implemented a CRDT from scratch.\n"
            "• Address the AWS gap in the cover letter: describe the Shopify deployment model and what you would independently own at Flowstate."
        ),
        "cover_letter": (
            "The backend engineer role at Flowstate lines up directly with the real-time system I built last summer.\n\n"
            "My Collaborative Editor uses Yjs for CRDT-based conflict resolution: each character has a globally unique ID and causal ordering, "
            "so concurrent insertions at the same position are deterministically resolved without a coordinator making decisions. "
            "The WebSocket server is intentionally stateless — it relays changes but doesn't arbitrate conflicts, "
            "which means it can be horizontally scaled without coordination overhead. "
            "Offline edits are stored in IndexedDB and merged on reconnect using the same CRDT merge operation. "
            "The system handles documents up to 500k characters with no perceptible lag on mid-range hardware.\n\n"
            "The Shopify internship gave me production backend context: rebuilt a rate limiter on the payments team, "
            "deployed behind a feature flag to 5% of traffic, promoted after two weeks with no regressions. "
            "I understand the gap between building something that works in development and something that works at production scale. "
            "Graduating April 2025, open to remote or the Waterloo area."
        ),
        "description": (
            "# Backend Engineer — Flowstate\n\n"
            "Flowstate builds developer workflow tooling. We're a small team moving fast and looking for a backend engineer "
            "who can own systems end to end — design, build, deploy, monitor, fix.\n\n"
            "**What you'll do:** Build the real-time collaboration layer. Design and maintain the backend API. "
            "Own the reliability of the systems you build.\n\n"
            "**What we're looking for:** TypeScript/Node.js. Real-time systems experience (WebSockets, CRDTs, or OT). "
            "AWS infrastructure experience. Production backend engineering — not just writing code, shipping it.\n\n"
            "**Stack:** TypeScript, Node.js, PostgreSQL, Redis, AWS (ECS, RDS, ElastiCache), React"
        ),
    },

    # ── 5 ─ Helix Health · Platform Engineer ─ APPLIED ────────────────────────
    {
        "title": "Platform Engineer",
        "company": "Helix Health",
        "status": "applied",
        "fit_score": 7,
        "created_at": ago(8),
        "fit_rationale": [
            "Distributed Tracing project demonstrates observability infrastructure at depth.",
            "Python and Go across multiple projects covers the primary language requirements.",
            "Shopify internship shows production backend experience with feature-flag deployment patterns.",
        ],
        "selected_projects": ["Distributed Tracing System", "Wildfire Risk Prediction Pipeline"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Distributed Tracing project demonstrates platform observability from first principles: instrumentation, span collection, sampling, and storage — "
            "relevant to Helix's stated need for an engineer who understands the full observability stack.\n"
            "• Python across the Wildfire Pipeline (PostGIS, scikit-learn, rasterio) and NLP research shows data engineering depth beyond the backend.\n"
            "• Shopify internship demonstrates production deployment patterns and on-call readiness.\n"
            "\nGAPS\n"
            "• No AWS or GCP experience — Helix runs on AWS and the role explicitly requires cloud infrastructure ownership. This is the most significant gap.\n"
            "• Health data domain is unfamiliar; HIPAA compliance patterns and PHI handling requirements will need to be learned from scratch.\n"
            "• Fit is 7/10 — the platform engineering scope is broader than current experience (CI/CD ownership, internal tooling, developer experience). Partial match.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Be explicit about the domain learning curve in the cover letter; focus the pitch on the observability and Python data infrastructure strengths.\n"
            "• Research HIPAA technical safeguards (audit logging, encryption at rest, PHI access controls) before the screen."
        ),
        "cover_letter": (
            "The platform engineering role at Helix is a partial match for my background, and I want to be direct about where it aligns and where it doesn't.\n\n"
            "The observability side is a strong fit. My Distributed Tracing project implements the full instrumentation stack — context propagation, "
            "span collection, sampling strategies, and a storage backend queryable with Grafana. "
            "I understand the operational concerns: what makes traces useful versus noisy, "
            "what the tradeoffs are between head-based and tail-based sampling, "
            "and where the memory footprint lives in a high-throughput collection pipeline.\n\n"
            "The gap is cloud infrastructure ownership. My production experience is through Shopify (where the infra is already built) "
            "and personal projects deployed locally. I don't have direct AWS or GCP deployment experience, "
            "and health data compliance requirements would be new to me. "
            "That said, I learn infrastructure quickly when I have ownership, and the Shopify internship gave me the mental model "
            "for how production systems are built and operated. Graduating April 2025."
        ),
        "description": (
            "# Platform Engineer — Helix Health\n\n"
            "Helix builds data infrastructure for clinical research teams. "
            "We're looking for a platform engineer to own developer infrastructure: CI/CD, observability, internal tooling, and the AWS environment that everything runs on.\n\n"
            "**What you'll do:** Own the observability stack. Manage the CI/CD pipeline. "
            "Build internal tooling that makes other engineers faster. Maintain AWS infrastructure.\n\n"
            "**What we're looking for:** Python or Go. AWS infrastructure experience (required). "
            "Observability experience (Prometheus, Grafana, OpenTelemetry). "
            "Experience with health data or compliance environments is a plus.\n\n"
            "**Stack:** Python, Go, AWS (EKS, RDS, S3), Terraform, GitHub Actions, Prometheus, Grafana"
        ),
    },

    # ── 6 ─ Northstar Cloud · Infrastructure Engineer ─ GENERATED ─────────────
    {
        "title": "Infrastructure Engineer",
        "company": "Northstar Cloud",
        "status": "generated",
        "fit_score": 8,
        "created_at": ago(6),
        "fit_rationale": [
            "Distributed Tracing project demonstrates systems-level understanding of distributed infrastructure.",
            "Go proficiency across internship and project matches the primary language requirement.",
            "Production deployment experience from Shopify shows readiness for on-call infra work.",
        ],
        "selected_projects": ["Distributed Tracing System"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Distributed Tracing project demonstrates systems-level infrastructure thinking: built a custom collector, designed a sampling layer, and benchmarked against OpenTelemetry Collector. "
            "This is the kind of first-principles infrastructure work Northstar is looking for.\n"
            "• Go proficiency is real and demonstrated across two separate codebases (Shopify internship and personal project).\n"
            "• Shopify internship experience with production on-call, feature flags, and rollout patterns signals readiness for infrastructure ownership.\n"
            "\nGAPS\n"
            "• No direct AWS or cloud provider experience. Northstar is an AWS-native company building cloud infrastructure products — "
            "this is the most critical gap and will be the first question in any technical screen.\n"
            "• No Terraform, Pulumi, or other infrastructure-as-code tooling in the profile.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Build and publish a minimal Terraform module deploying the Distributed Tracing system to AWS (VPC, EKS, ECR, ALB) — "
            "this directly closes both the AWS and IaC gaps with a concrete, linkable artifact.\n"
            "• Apply after completing the Terraform module; the application will be noticeably stronger."
        ),
        "cover_letter": None,
        "description": (
            "# Infrastructure Engineer — Northstar Cloud\n\n"
            "Northstar builds cloud-native infrastructure tooling for engineering teams at scale. "
            "We're looking for an infrastructure engineer who understands distributed systems at the OS and network level — "
            "not just how to use cloud services, but what they're doing underneath.\n\n"
            "**What you'll do:** Design and build infrastructure components used by Northstar's customers. "
            "Own the reliability and performance of core platform services. Contribute to the open-source tooling Northstar maintains.\n\n"
            "**What we're looking for:** Go (required). AWS infrastructure experience (required). "
            "Terraform or Pulumi for infrastructure as code. Kubernetes. Strong systems fundamentals.\n\n"
            "**Stack:** Go, AWS (EKS, EC2, S3, DynamoDB), Terraform, Kubernetes, Prometheus"
        ),
    },

    # ── 7 ─ Cedar · Software Engineer, Backend ─ GENERATED ────────────────────
    {
        "title": "Software Engineer, Backend",
        "company": "Cedar",
        "status": "generated",
        "fit_score": 8,
        "created_at": ago(4),
        "fit_rationale": [
            "Strong Python and Go across multiple projects satisfies the primary language requirements.",
            "Shopify internship demonstrates production backend engineering with Redis and service ownership.",
            "Distributed Tracing project shows systems depth beyond typical student projects.",
        ],
        "selected_projects": ["Distributed Tracing System", "Real-time Collaborative Editor"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Strong backend engineering signal across two languages: Go at Shopify (production rate limiter) and the tracing project; Python across NLP research and the ML eval framework.\n"
            "• Shopify internship demonstrates the production engineering mindset the JD is looking for: feature flags, canary rollout, regression monitoring.\n"
            "• Collaborative Editor shows product-facing backend work (real-time systems, WebSocket architecture) alongside the infra-facing work.\n"
            "\nGAPS\n"
            "• No AWS or GCP deployment experience — Cedar runs on AWS and expects engineers to contribute to infrastructure decisions, not just write application code.\n"
            "• The role asks for 2+ years of experience; the profile has one internship and student project work. May face a seniority screen.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Lead the cover letter with the Shopify internship impact numbers (40% throughput increase, 5% canary rollout) — quantified internship results address the experience gap better than anything else.\n"
            "• Research Cedar's engineering blog before the screen; the team values engineers who have read their public technical writing."
        ),
        "cover_letter": None,
        "description": (
            "# Software Engineer, Backend — Cedar\n\n"
            "Cedar builds enterprise financial software. We're looking for a backend engineer to join the core platform team "
            "and work on the systems that other teams depend on: APIs, data pipelines, and the infrastructure layer.\n\n"
            "**What you'll do:** Build and maintain core backend services. "
            "Contribute to infrastructure decisions. Code review and technical design for the platform team.\n\n"
            "**What we're looking for:** Python or Go. 2+ years of production backend experience. "
            "AWS familiarity. Strong fundamentals — you understand what happens when a request fails, not just that it failed.\n\n"
            "**Stack:** Python, Go, PostgreSQL, Redis, AWS, Kubernetes"
        ),
    },

    # ── 8 ─ Apex Labs · Research Engineer ─ SKIPPED ───────────────────────────
    {
        "title": "Research Engineer",
        "company": "Apex Labs",
        "status": "skipped",
        "fit_score": 6,
        "created_at": ago(3),
        "fit_rationale": [
            "NLP research and LLM eval framework demonstrate ML research experience.",
            "PyTorch and Hugging Face Transformers experience is relevant.",
            "Role is research-track, not engineering-track — not the target.",
        ],
        "selected_projects": ["LLM Evaluation Framework"],
        "strategic_note": (
            "GOOD FIT\n"
            "• NLP research (Legal-BERT fine-tuning, F1 0.91) and LLM Evaluation Framework demonstrate genuine ML research capability.\n"
            "• PyTorch and Hugging Face Transformers experience across two projects satisfies the technical bar.\n"
            "\nGAPS\n"
            "• Role is research-track — papers expected, PhD preferred. Target is engineering-track roles.\n"
            "• No publications as first author; the NLP work is lab-contributed, not independent research.\n"
            "• GCP experience not present; Apex runs all compute on GCP.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Skipped — role is a poor strategic fit. Research track requires publication output that isn't the current goal.\n"
            "• Worth following Apex for engineering roles if they open — the ML infra track would be a better match."
        ),
        "cover_letter": None,
        "description": (
            "# Research Engineer — Apex Labs\n\n"
            "Apex Labs conducts frontier AI research. We're looking for a research engineer to work alongside our research team: "
            "implementing experiments, scaling training runs, and building the tooling that accelerates research.\n\n"
            "**What we're looking for:** PhD or equivalent research experience. "
            "Strong ML fundamentals. GCP. PyTorch. Publication record preferred.\n\n"
            "**Stack:** Python, PyTorch, GCP (TPUs, Vertex AI), JAX"
        ),
    },

    # ── 9 ─ Slate · Software Engineer, Product ─ GENERATED ────────────────────
    {
        "title": "Software Engineer, Product",
        "company": "Slate",
        "status": "generated",
        "fit_score": 7,
        "created_at": ago(1),
        "fit_rationale": [
            "TypeScript and React experience from Collaborative Editor satisfies the frontend requirement.",
            "Node.js backend and WebSocket architecture demonstrates full-stack capability.",
            "Shopify internship shows product context and cross-functional engineering.",
        ],
        "selected_projects": ["Real-time Collaborative Editor", "LLM Evaluation Framework"],
        "strategic_note": (
            "GOOD FIT\n"
            "• Collaborative Editor is strong evidence for the real-time product engineering Slate is building: CRDTs, WebSockets, offline-first architecture, TypeScript/React.\n"
            "• Shopify internship provides product engineering context — working on a feature that affects real users and being accountable for its rollout.\n"
            "• LLM Evaluation Framework shows product-side ML interest, relevant to Slate's AI feature roadmap.\n"
            "\nGAPS\n"
            "• No AWS deployment experience. Slate runs entirely on AWS and expects product engineers to understand and contribute to the infrastructure their features run on.\n"
            "• The role emphasizes product intuition and user empathy alongside engineering — the profile demonstrates strong engineering depth but limited product-facing experience outside the internship.\n"
            "\nIMPROVEMENT PLAN\n"
            "• Frame the Collaborative Editor pitch around the user experience decisions, not just the CRDT architecture — why offline-first, why CRDT over OT, what that means for the user.\n"
            "• Slate values engineers who think about the product, not just the system. The cover letter should reflect that register."
        ),
        "cover_letter": None,
        "description": (
            "# Software Engineer, Product — Slate\n\n"
            "Slate builds productivity software for knowledge workers. "
            "We're a product-led engineering team — every engineer thinks about the user, not just the system.\n\n"
            "**What you'll do:** Build product features end to end: backend API, frontend components, and the infrastructure they run on. "
            "Contribute to product design discussions.\n\n"
            "**What we're looking for:** TypeScript. React. Node.js or Python backend. AWS. "
            "Strong product intuition — you care about the user experience, not just the code.\n\n"
            "**Stack:** TypeScript, React, Node.js, PostgreSQL, Redis, AWS (ECS, RDS)"
        ),
    },
]


async def seed_jobs(dry_run: bool = False) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing_count = (await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(
                __import__("sqlalchemy", fromlist=["func"]).func.count(Job.id)
            )
        )).scalar()

        print(f"Existing jobs: {existing_count}")

        if dry_run:
            print(f"DRY RUN — would seed {len(APPLICATIONS)} applications:")
            for a in APPLICATIONS:
                print(f"  [{a['status']:10s}] {a['title']} — {a['company']}  (fit: {a['fit_score']}/10)")
            return

        # Wipe existing jobs
        await db.execute(delete(Job))
        await db.commit()
        print("Cleared existing jobs.")

        # Insert new applications
        for a in APPLICATIONS:
            job = Job(
                title=a["title"],
                company=a["company"],
                status=a["status"],
                fit_score=a["fit_score"],
                fit_rationale=a.get("fit_rationale"),
                strategic_note=a.get("strategic_note"),
                selected_projects=a.get("selected_projects"),
                cover_letter=a.get("cover_letter"),
                resume_latex=a.get("resume_latex"),
                description=a.get("description"),
                created_at=a["created_at"],
            )
            db.add(job)

        await db.commit()

        print(f"\nSeeded {len(APPLICATIONS)} applications:")
        for a in APPLICATIONS:
            print(f"  [{a['status']:10s}] {a['title']} — {a['company']}  (fit: {a['fit_score']}/10)")

        print("\nCandidacy insights will surface:")
        print("  Pattern: AWS/GCP/Azure experience absent across every backend and infrastructure JD.")
        print("  7 of 9 applications include this gap in the strategic note.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(seed_jobs(dry_run=dry_run))
