from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models  # noqa: F401 — registers all models with Base before create_all
from app.config import settings
from app.database import Base, engine
from app.routers import jobs, profile
from app.seed import seed


async def _run_migrations() -> None:
    """Run raw SQL migration files from the migrations/ directory in alphabetical order.
    All statements are idempotent (IF NOT EXISTS / IF EXISTS guards), safe to run on every startup.
    """
    migrations_dir = Path(__file__).parent.parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        return
    async with engine.begin() as conn:
        for path in sql_files:
            raw = path.read_text()
            # Strip comment lines, split on semicolons, execute each statement
            for stmt in raw.split(";"):
                stmt = "\n".join(
                    line for line in stmt.splitlines() if not line.strip().startswith("--")
                ).strip()
                if stmt:
                    await conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()
    await seed()
    yield


app = FastAPI(title="CareerOS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/admin")
app.include_router(jobs.router, prefix="/admin")


@app.get("/health")
async def health():
    return {"status": "ok"}
