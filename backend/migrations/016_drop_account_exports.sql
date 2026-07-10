-- Migration 016: Drop account_exports.
-- The account data export feature (Phase 6) has been removed — not needed for
-- this product. All application code that read/wrote this table (routers,
-- worker job, R2 zip storage) has already been deleted; this migration just
-- removes the now-orphaned table itself. Safe to run whenever convenient —
-- nothing in the app queries this table anymore.

DROP TABLE IF EXISTS account_exports;
