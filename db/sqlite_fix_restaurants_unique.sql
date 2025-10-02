-- Fix restaurants table UNIQUE constraint for ON CONFLICT support
-- SQLite doesn't support ON CONFLICT with partial unique indexes

-- Drop the partial unique index if it exists
DROP INDEX IF EXISTS restaurants_place_unique;

-- Recreate the restaurants table with proper UNIQUE constraint
-- Note: SQLite doesn't support ALTER TABLE to add constraints, so we need to recreate

-- Step 1: Create new table with correct schema
CREATE TABLE IF NOT EXISTS restaurants_new (
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
  opening_hours    TEXT,
  image_url        TEXT,
  status           TEXT,
  lat              REAL,
  lng              REAL,
  last_verified_at TEXT,
  created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(place_source, place_ref)
);

-- Step 2: Copy data from old table
INSERT INTO restaurants_new
  SELECT * FROM restaurants;

-- Step 3: Drop old table
DROP TABLE restaurants;

-- Step 4: Rename new table
ALTER TABLE restaurants_new RENAME TO restaurants;

-- Step 5: Recreate indexes
CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);
CREATE INDEX IF NOT EXISTS idx_restaurants_country ON restaurants(country_code);
