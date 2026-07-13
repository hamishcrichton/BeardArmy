-- Adds YouTube statistics to videos and challenge weight from extraction v2.1.
-- Safe to re-run: sqlite3 CLI continues past "duplicate column" errors by default.
ALTER TABLE videos ADD COLUMN view_count INTEGER;
ALTER TABLE videos ADD COLUMN like_count INTEGER;
ALTER TABLE challenges ADD COLUMN weight_lb REAL;
