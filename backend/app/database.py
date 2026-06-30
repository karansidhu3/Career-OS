from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _normalize(url: str) -> str:
    # Railway provides postgresql:// or postgres:// — rewrite to asyncpg dialect
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _get_db_url() -> str:
    return _normalize(settings.database_url)


def _get_app_db_url() -> str:
    # Falls back to DATABASE_URL when APP_DATABASE_URL is unset, so a deployment
    # that hasn't provisioned the restricted role yet still boots (RLS will simply
    # be inert for it, same as before this role existed — see migration 006).
    return _normalize(settings.app_database_url or settings.database_url)


# Elevated-privilege engine — owns the schema, runs migrations and create_all.
# Used only at startup (app.main._run_migrations, Base.metadata.create_all).
engine = create_async_engine(
    _get_db_url(),
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Least-privilege engine — what every request actually runs queries through.
# Bound to APP_DATABASE_URL's restricted role (no superuser, no BYPASSRLS) so
# Row-Level Security in migration 006 is actually enforced against it.
app_engine = create_async_engine(
    _get_app_db_url(),
    echo=False,
    # Limit connections to prevent exhaustion under concurrent requests or runaway clients
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # recycle connections every 30 min to avoid stale connections
)
AsyncSessionLocal = async_sessionmaker(app_engine, expire_on_commit=False)

# Bound to the elevated engine — for the rare operation that genuinely needs
# owner privileges mid-request (currently: app.clerk_auth._claim_legacy_data's
# ALTER TABLE ... NO FORCE ROW LEVEL SECURITY toggle, which the restricted
# app_engine role can never do by design).
ElevatedSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # The RLS GUC (app.current_user_id) is session-scoped, not transaction-scoped
            # (see app.clerk_auth.get_current_user), so it survives this request's commits.
            # Clear it before the connection returns to the pool — otherwise the next
            # request to reuse this connection could inherit a stale user's identity.
            try:
                await session.rollback()
                await session.execute(text("SELECT set_config('app.current_user_id', '', false)"))
            except Exception:
                pass  # best-effort cleanup — a broken connection will be discarded by the pool anyway
