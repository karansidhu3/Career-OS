-- Migration 015: Add personal_info.custom_preamble.
-- Stores a user-supplied LaTeX preamble used when resume_template = 'custom'.
-- The stored value is the full preamble (packages + commands + heading + education)
-- exactly as the user wrote it. Generation appends the body sections and
-- \end{document} without any dynamic injection — the user owns the entire preamble.

ALTER TABLE personal_info ADD COLUMN IF NOT EXISTS custom_preamble TEXT;
