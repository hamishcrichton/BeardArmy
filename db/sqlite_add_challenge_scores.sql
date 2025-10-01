-- Migration: Add challenge scoring fields
-- Run this to add new fields to existing database

-- Add food_type field to challenges
ALTER TABLE challenges ADD COLUMN food_type TEXT;

-- Add challenge difficulty scores (0-10 scale)
ALTER TABLE challenges ADD COLUMN food_volume_score INTEGER DEFAULT 0;
ALTER TABLE challenges ADD COLUMN time_limit_score INTEGER DEFAULT 0;
ALTER TABLE challenges ADD COLUMN success_rate_score INTEGER DEFAULT 0;
ALTER TABLE challenges ADD COLUMN spiciness_score INTEGER DEFAULT 0;
ALTER TABLE challenges ADD COLUMN food_diversity_score INTEGER DEFAULT 0;
ALTER TABLE challenges ADD COLUMN risk_level_score INTEGER DEFAULT 0;

-- Add index for food_type queries
CREATE INDEX IF NOT EXISTS idx_challenges_food_type ON challenges(food_type);
