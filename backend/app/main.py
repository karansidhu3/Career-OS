import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
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

_log = logging.getLogger(__name__)


def _limiter_key(request: Request) -> str:
    """Rate-limit by API key when present; fall back to IP for unauthenticated paths."""
    key = request.headers.get("x-api-key")
    return key if key else get_remote_address(request)


# Rate limiter — shared across all routers
limiter = Limiter(key_func=_limiter_key)


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
    # Refuse to start in production without an API key.
    # Set DEV_MODE=true in backend/.env to bypass this check locally.
    if not settings.api_key:
        if settings.dev_mode:
            _log.warning(
                "API_KEY is not set — running in DEV_MODE with authentication disabled. "
                "Never set DEV_MODE=true in production."
            )
        else:
            _log.critical(
                "API_KEY is not set and DEV_MODE is false. "
                "Set API_KEY in environment variables, or set DEV_MODE=true for local development."
            )
            sys.exit(1)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()
    await seed()
    # Warm up Tectonic package cache in the background — doesn't block startup
    import asyncio
    asyncio.create_task(_warmup_tectonic())
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
