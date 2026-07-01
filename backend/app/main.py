import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

import app.models  # noqa: F401 — registers all models with Base before create_all
from app.config import settings
from app.database import Base, engine
from app.routers import account, credentials, jobs, profile

_log = logging.getLogger(__name__)


def _limiter_key(request: Request) -> str:
    """Rate-limit by the bearer token when present; fall back to IP for unauthenticated paths."""
    auth_header = request.headers.get("authorization", "")
    return auth_header or get_remote_address(request)


# Rate limiter — shared across all routers
limiter = Limiter(key_func=_limiter_key)


def _split_sql_statements(raw: str) -> list[str]:
    """Split a SQL file into individual statements on `;`.

    Comment lines (starting with --) are stripped first. `$$...$$` dollar-quoted
    regions (used by DO blocks) are tracked so semicolons inside them — e.g. the
    ALTER TABLE inside a conditional DO $$ ... END $$; block — aren't mistaken
    for statement separators.
    """
    cleaned = "\n".join(
        line for line in raw.splitlines() if not line.strip().startswith("--")
    )
    statements: list[str] = []
    current: list[str] = []
    in_dollar_quote = False
    i = 0
    while i < len(cleaned):
        if cleaned[i:i + 2] == "$$":
            in_dollar_quote = not in_dollar_quote
            current.append("$$")
            i += 2
            continue
        ch = cleaned[i]
        if ch == ";" and not in_dollar_quote:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


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
            for stmt in _split_sql_statements(path.read_text()):
                await conn.execute(text(stmt))


async def _warmup_tectonic() -> None:
    """Compile a minimal LaTeX doc at startup to pre-download Tectonic packages.
    Runs in the background so startup is not blocked. First cold-start compilation
    takes 30–90 s; warming the cache here means the first real user PDF request is fast.
    """
    import logging
    _log = logging.getLogger(__name__)
    _WARMUP_LATEX = r"""
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
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage{xcolor}
\usepackage{eso-pic}
\begin{document}
CareerOS warmup.
\end{document}
"""
    try:
        from app.services.pdf import compile_latex_to_pdf
        await compile_latex_to_pdf(_WARMUP_LATEX)
        _log.info("Tectonic warmup complete — PDF cache is ready")
    except Exception as exc:
        _log.warning("Tectonic warmup failed (PDFs will compile on first request): %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Refuse to start in production without Clerk configured — every /admin/* route
    # depends on app.clerk_auth.get_current_user, which needs both of these.
    # Set DEV_MODE=true in backend/.env to bypass this check locally.
    if not settings.clerk_secret_key or not settings.clerk_frontend_api_domain:
        if settings.dev_mode:
            _log.warning(
                "CLERK_SECRET_KEY / CLERK_FRONTEND_API_DOMAIN not fully set — running in DEV_MODE. "
                "Never set DEV_MODE=true in production."
            )
        else:
            _log.critical(
                "CLERK_SECRET_KEY and CLERK_FRONTEND_API_DOMAIN must both be set. "
                "Set them in environment variables, or set DEV_MODE=true for local development."
            )
            sys.exit(1)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()
    # Note: app.seed.seed() previously ran here to bootstrap single-user demo
    # profile data. It inserts ownerless rows (no user_id), which RLS now
    # rejects, and the single-profile model it assumes no longer holds in a
    # multi-tenant app. Left in the repo but not run — needs a per-user
    # redesign (e.g. seeding a demo Clerk account) before it's useful again.
    # Warm up Tectonic package cache in the background — doesn't block startup
    import asyncio
    asyncio.create_task(_warmup_tectonic())

    # ARQ pool for enqueueing generation jobs (Phase 5) — the actual work runs in
    # a separate worker process (`arq app.worker.WorkerSettings`), not here.
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        yield
    finally:
        await app.state.arq_pool.close()


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
    allow_headers=["Content-Type", "Authorization"],
)

# /admin routes are authenticated per-route via app.clerk_auth.get_current_user,
# not a router-level dependency — each handler needs the resolved User to scope its queries.
app.include_router(profile.router, prefix="/admin")
app.include_router(jobs.router, prefix="/admin")
app.include_router(credentials.router, prefix="/admin")
app.include_router(account.router, prefix="/admin")


@app.get("/health")
async def health():
    return {"status": "ok"}
