-- Migration 014: Add personal_info.resume_template.
-- Stores the user's chosen LaTeX resume template key ('jake', 'crisp', 'modern').
-- NULL means the user hasn't chosen yet — the onboarding template picker shows on
-- next sign-in and writes the choice back, after which it's set for all future
-- generations. Existing users get NULL and will see the picker on next login.
--
-- No DEFAULT here: keeping NULL as the sentinel for "hasn't picked yet" avoids
-- silently assigning existing users to a template they never chose.

ALTER TABLE personal_info ADD COLUMN IF NOT EXISTS resume_template VARCHAR(32);
