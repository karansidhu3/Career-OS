# CareerOS Demo

This folder contains a fictional candidate profile and three sample job descriptions for demonstrating CareerOS without exposing real personal data.

## The demo candidate

**Jordan Park** — CS grad, University of Waterloo. Four projects spanning different technical domains:

| Project | Domain | Key technologies |
|---|---|---|
| Distributed Tracing System | Backend / Infra | Go, gRPC, Redis, Jaeger, OpenTelemetry |
| LLM Evaluation Framework | ML / AI | Python, PyTorch, Hugging Face, FastAPI |
| Real-time Collaborative Editor | Full-stack product | TypeScript, React, WebSockets, CRDTs (Yjs) |
| Wildfire Risk Prediction Pipeline | Data / ML | Python, scikit-learn, GeoPandas, PostGIS |

The diversity is intentional. Each sample JD triggers a different project selection.

## What to watch for

The point of the demo is to show that the **same profile** produces **different outputs** for different roles — not just different wording, but genuinely different project selection and emphasis.

| JD | Expected project selection |
|---|---|
| `backend-systems-engineer.md` | Distributed Tracing + Shopify experience front |
| `ml-engineer-llm.md` | LLM Eval Framework + NLP research front |
| `fullstack-product-engineer.md` | Collaborative Editor + Shopify experience front |

After generating all three: compare the **"Emphasized:"** bar at the top of each result, then compare the resume previews side by side. The AI committed to project selection before writing a word — that decision is visible.

## Setup

### 1. Provision a demo database

Use a separate database — do not run this against your real `DATABASE_URL`.

```bash
# Local Postgres
createdb careeros_demo

# Or provision a fresh Railway Postgres service and use its connection string
```

### 2. Start the backend pointing at the demo DB

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://localhost/careeros_demo uvicorn app.main:app --reload
```

### 3. Seed the demo profile

```bash
# From repo root
DATABASE_URL=postgresql+asyncpg://localhost/careeros_demo \
    python demo/seed_demo_profile.py
```

### 4. Open the frontend

```bash
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### 5. Generate applications

Paste each JD from `demo/sample_jds/` into the textarea and generate. Run all three before taking screenshots or recording.

## Re-seeding

If you need to start fresh:

```bash
DATABASE_URL=postgresql+asyncpg://localhost/careeros_demo \
    python demo/seed_demo_profile.py --reset
```

This wipes and re-seeds the demo database. It will not touch any other database.
