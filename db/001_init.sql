-- Postgres + PostGIS schema for BMF Challenges

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enums
DO $$ BEGIN
  CREATE TYPE challenge_result AS ENUM ('success', 'failure', 'unknown');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Core tables
CREATE TABLE IF NOT EXISTS videos (
  video_id           text PRIMARY KEY, -- YouTube ID
  title              text NOT NULL,
  description        text,
  published_at       timestamptz NOT NULL,
  duration_seconds   integer,
  captions_available boolean DEFAULT false,
  playlist_ids       text[] DEFAULT '{}',
  thumbnail_url      text,
  channel_id         text NOT NULL,
  raw_json           jsonb,
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS restaurants (
  id               bigserial PRIMARY KEY,
  name             text NOT NULL,
  place_source     text,  -- google|osm|opencage|mapbox|manual
  place_ref        text,
  address          text,
  city             text,
  region           text,
  country_code     text,
  phone            text,
  website          text,
  opening_hours    jsonb,
  image_url        text,
  status           text,  -- open|closed|unknown
  lat              double precision,
  lng              double precision,
  geom             geometry(Point, 4326),
  last_verified_at timestamptz,
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

-- Unique reference if we have an external place id
CREATE UNIQUE INDEX IF NOT EXISTS restaurants_place_unique
ON restaurants (place_source, place_ref)
WHERE place_source IS NOT NULL AND place_ref IS NOT NULL;

-- Keep geom synced
CREATE OR REPLACE FUNCTION set_restaurant_geom() RETURNS trigger AS $$
BEGIN
  IF NEW.lat IS NOT NULL AND NEW.lng IS NOT NULL THEN
    NEW.geom := ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326);
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_restaurant_geom ON restaurants;
CREATE TRIGGER trg_restaurant_geom
BEFORE INSERT OR UPDATE OF lat, lng ON restaurants
FOR EACH ROW EXECUTE FUNCTION set_restaurant_geom();

CREATE TABLE IF NOT EXISTS challenge_types (
  id     serial PRIMARY KEY,
  slug   text UNIQUE NOT NULL,
  label  text NOT NULL,
  category text  -- quantity|spicy|speed|mixed
);

CREATE TABLE IF NOT EXISTS challenges (
  id               bigserial PRIMARY KEY,
  video_id         text NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  restaurant_id    bigint REFERENCES restaurants(id) ON DELETE SET NULL,
  date_attempted   date,
  result           challenge_result DEFAULT 'unknown',
  challenge_type_id integer REFERENCES challenge_types(id) ON DELETE SET NULL,
  time_limit       interval,
  price_cents      integer,
  notes            text,
  charity_flag     boolean DEFAULT false,
  source           text,   -- title|description|caption|manual|provider
  confidence       real,   -- 0..1
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collaborators (
  id             bigserial PRIMARY KEY,
  name           text NOT NULL,
  yt_channel_id  text,
  website        text,
  image_url      text,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS challenge_collaborators (
  challenge_id   bigint NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
  collaborator_id bigint NOT NULL REFERENCES collaborators(id) ON DELETE CASCADE,
  PRIMARY KEY (challenge_id, collaborator_id)
);

CREATE TABLE IF NOT EXISTS tags (
  id      bigserial PRIMARY KEY,
  label   text NOT NULL,
  type    text   -- food|place|meta
);

CREATE TABLE IF NOT EXISTS challenge_tags (
  challenge_id bigint NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
  tag_id       bigint NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (challenge_id, tag_id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_challenges_video ON challenges(video_id);
CREATE INDEX IF NOT EXISTS idx_challenges_restaurant ON challenges(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_challenges_date ON challenges(date_attempted);
CREATE INDEX IF NOT EXISTS idx_restaurants_geom ON restaurants USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_restaurants_country ON restaurants(country_code);

-- Seed challenge types (idempotent)
INSERT INTO challenge_types (slug, label, category) VALUES
  ('quantity', 'Quantity', 'quantity'),
  ('spicy', 'Spicy', 'spicy'),
  ('speed', 'Speed', 'speed'),
  ('mixed', 'Mixed', 'mixed')
ON CONFLICT (slug) DO NOTHING;

