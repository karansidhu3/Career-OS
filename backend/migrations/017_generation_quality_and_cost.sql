-- Migration 017: generation v2 quality, provenance, and cost accounting.
--
-- IMPORTANT: this migration is intentionally committed but must not be run in
-- production without Karan's explicit deployment approval. The application
-- startup migration runner will execute it on the next backend deployment.

ALTER TABLE job ADD COLUMN IF NOT EXISTS generation_version VARCHAR(32);
ALTER TABLE job ADD COLUMN IF NOT EXISTS generation_metadata JSONB;
ALTER TABLE job ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE job ADD COLUMN IF NOT EXISTS total_cost_usd DOUBLE PRECISION;

CREATE TABLE IF NOT EXISTS profile_fact_banks (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    profile_hash VARCHAR(64) NOT NULL,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1',
    fact_bank JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES job(id) ON DELETE SET NULL,
    purpose VARCHAR(64) NOT NULL,
    model VARCHAR(64) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_llm_calls_user_created ON llm_calls(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_llm_calls_job ON llm_calls(job_id);

ALTER TABLE profile_fact_banks ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile_fact_banks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON profile_fact_banks;
CREATE POLICY tenant_isolation ON profile_fact_banks
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON llm_calls;
CREATE POLICY tenant_isolation ON llm_calls
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
