-- Adds content-kind classification: challenge (default) vs special
-- (music videos, Q&As, cheat days, tours - no win/lose stakes).
ALTER TABLE challenges ADD COLUMN kind TEXT DEFAULT 'challenge';
