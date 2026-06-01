-- Migration 003: Add selected_projects to job, cover_letter_voice to personal_info
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

-- Which projects the AI chose to emphasize — surfaced in result UI for quick verification
ALTER TABLE job ADD COLUMN IF NOT EXISTS selected_projects JSONB;

-- How Karan writes — fed directly into cover letter generation prompt
ALTER TABLE personal_info ADD COLUMN IF NOT EXISTS cover_letter_voice TEXT NOT NULL DEFAULT '';
