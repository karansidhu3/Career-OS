from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

import app.models  # noqa: F401 — registers all models with Base before create_all
from app.auth import verify_api_key
from app.config import settings
from app.database import Base, engine
from app.routers import jobs, profile
from app.seed import seed

# Rate limiter — shared across all routers
limiter = Limiter(key_func=get_remote_address)


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


app = FastAPI(
    title="CareerOS API",
    lifespan=lifespan,
    # Disable interactive docs in all environments — full API schema is not public
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Rate limiter — must be attached before routers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),  # reads ALLOWED_ORIGINS env var
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# All /admin routes require API key authentication
_auth = [Depends(verify_api_key)]
app.include_router(profile.router, prefix="/admin", dependencies=_auth)
app.include_router(jobs.router, prefix="/admin", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "ok"}
