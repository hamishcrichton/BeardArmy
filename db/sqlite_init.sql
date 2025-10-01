-- SQLite schema for BMF Challenges (lightweight)

PRAGMA foreign_keys = ON;

-- Core tables
CREATE TABLE IF NOT EXISTS videos (
  video_id           TEXT PRIMARY KEY,
  title              TEXT NOT NULL,
  description        TEXT,
  published_at       TEXT NOT NULL,              -- ISO8601
  duration_seconds   INTEGER,
  captions_available INTEGER DEFAULT 0,          -- boolean
  playlist_ids       TEXT,                       -- JSON array
  thumbnail_url      TEXT,
  channel_id         TEXT NOT NULL,
  raw_json           TEXT,                       -- JSON object
  created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at         TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurants (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  name             TEXT NOT NULL,
  place_source     TEXT,
  place_ref        TEXT,
  address          TEXT,
  city             TEXT,
  region           TEXT,
  country_code     TEXT,
  phone            TEXT,
  website          TEXT,
  opening_hours    TEXT,    -- JSON object
  image_url        TEXT,
  status           TEXT,
  lat              REAL,
  lng              REAL,
  last_verified_at TEXT,
  created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Partial unique index matching Postgres behavior
CREATE UNIQUE INDEX IF NOT EXISTS restaurants_place_unique
ON restaurants (place_source, place_ref)
WHERE place_source IS NOT NULL AND place_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS challenge_types (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  slug     TEXT UNIQUE NOT NULL,
  label    TEXT NOT NULL,
  category TEXT
);

CREATE TABLE IF NOT EXISTS challenges (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id         TEXT NOT NULL,
  restaurant_id    INTEGER,
  date_attempted   TEXT,                  -- ISO8601 date
  result           TEXT DEFAULT 'unknown',
  challenge_type_id INTEGER,
  food_type        TEXT,                  -- e.g., burger, pizza, bbq, breakfast
  time_limit       INTEGER,               -- seconds
  price_cents      INTEGER,
  notes            TEXT,
  charity_flag     INTEGER DEFAULT 0,
  source           TEXT,
  confidence       REAL,
  -- Challenge difficulty scores (0-10 scale)
  food_volume_score    INTEGER DEFAULT 0,
  time_limit_score     INTEGER DEFAULT 0,
  success_rate_score   INTEGER DEFAULT 0,
  spiciness_score      INTEGER DEFAULT 0,
  food_diversity_score INTEGER DEFAULT 0,
  risk_level_score     INTEGER DEFAULT 0,
  created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
  FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE SET NULL,
  FOREIGN KEY(challenge_type_id) REFERENCES challenge_types(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS collaborators (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  yt_channel_id TEXT,
  website       TEXT,
  image_url     TEXT,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS challenge_collaborators (
  challenge_id    INTEGER NOT NULL,
  collaborator_id INTEGER NOT NULL,
  PRIMARY KEY (challenge_id, collaborator_id),
  FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
  FOREIGN KEY(collaborator_id) REFERENCES collaborators(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  type  TEXT
);

CREATE TABLE IF NOT EXISTS challenge_tags (
  challenge_id INTEGER NOT NULL,
  tag_id       INTEGER NOT NULL,
  PRIMARY KEY (challenge_id, tag_id),
  FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_challenges_video ON challenges(video_id);
CREATE INDEX IF NOT EXISTS idx_challenges_restaurant ON challenges(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_challenges_date ON challenges(date_attempted);
CREATE INDEX IF NOT EXISTS idx_challenges_food_type ON challenges(food_type);
CREATE INDEX IF NOT EXISTS idx_restaurants_country ON restaurants(country_code);

-- Seed challenge types
INSERT OR IGNORE INTO challenge_types (slug, label, category) VALUES
  ('quantity', 'Quantity', 'quantity'),
  ('spicy', 'Spicy', 'spicy'),
  ('speed', 'Speed', 'speed'),
  ('mixed', 'Mixed', 'mixed');

