# LLM Challenge Scoring - Setup Guide

## Changes Made

### 1. Enhanced LLM Extraction
- ✅ Replaced generic "type" field with **food_type** (cuisine: burger, pizza, bbq, breakfast, etc.)
- ✅ Added 6 challenge difficulty scores (0-10 scale):
  - **food_volume_score**: Amount of food (0=snack, 10=enormous)
  - **time_limit_score**: Time constraint strictness (0=no limit, 10=very tight)
  - **success_rate_score**: Historical difficulty (0=easy, 10=almost impossible)
  - **spiciness_score**: Heat level (0=mild, 10=Carolina Reaper)
  - **food_diversity_score**: Variety of items (0=single item, 10=huge variety)
  - **risk_level_score**: Stakes/consequences (0=low risk, 10=high cost/big prize)

### 2. Database Updates
- ✅ Added `food_type` column to `challenges` table
- ✅ Added 6 score columns (integers 0-10)
- ✅ Updated indexes for `food_type` queries
- ✅ Migration script: `db/sqlite_add_challenge_scores.sql`

### 3. Pipeline Integration
- ✅ LLM extraction enabled via `USE_LLM_EXTRACTION=true`
- ✅ Falls back to regex if LLM fails
- ✅ Scores automatically saved to database
- ✅ Published in `table.json` and `challenges.geojson`

### 4. GitHub Actions
- ✅ Added LLM environment variables
- ✅ Auto-installs `anthropic` or `openai` package
- ✅ Applies database migration automatically

## Local Setup

### 1. Test LLM Scoring

```powershell
# Set API key
$env:ANTHROPIC_API_KEY = "sk-ant-your-key"

# Test on sample videos
python test_llm_extraction.py
```

**Expected output:**
```
✅ Extracted:
   Restaurant:  Super Mario's Italian Restaurant
   City:        Las Vegas
   Country:     US
   Result:      failure
   Food Type:   pizza
   Confidence:  0.92

   Challenge Scores (0-10):
   - Food Volume:    9/10
   - Time Limit:     7/10
   - Success Rate:   8/10 (difficulty)
   - Spiciness:      0/10
   - Food Diversity: 2/10
   - Risk Level:     8/10

   Reasoning:  45-inch pizza is massive (high volume), 2-hour limit is moderate, $500 prize...
```

### 2. Apply Database Migration

If you have an existing `data/app.db`:

```powershell
sqlite3 data/app.db < db/sqlite_add_challenge_scores.sql
```

This adds the new columns without losing existing data.

### 3. Enable LLM in Local Pipeline

Edit `.env`:
```env
USE_LLM_EXTRACTION=true
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 4. Run Pipeline

```powershell
cd ingestion
python -m bmf_ingest.main refresh --channel UCc9CjaAjsMMvaSghZB7-Kog --since-days 7
python -m bmf_ingest.main publish --out ../public/data
```

Check `public/data/table.json` - you should see the new fields:
```json
{
  "restaurant": "Illegal Burger",
  "city": "Oslo",
  "food_type": "burger",
  "food_volume_score": 8,
  "time_limit_score": 5,
  "success_rate_score": 9,
  ...
}
```

## GitHub Actions Setup

### 1. Add Secrets

Go to: **Settings → Secrets and variables → Actions**

**Add these secrets:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- (Or `OPENAI_API_KEY` if using OpenAI)

### 2. Add Variables

**Add these variables:**
- `USE_LLM_EXTRACTION` = `true`
- `LLM_PROVIDER` = `anthropic` (or `openai`)

### 3. Trigger Workflow

Go to **Actions** tab → **Refresh and Publish Artifacts** → **Run workflow**

- Mode: `refresh` (for recent videos) or `backfill` (for all videos)
- Since days: `7` (default)

The workflow will:
1. Install Anthropic/OpenAI package
2. Apply database migration
3. Run LLM extraction on videos
4. Publish scores to `table.json`
5. Commit results back to repo

## Cost Estimation

**Per video with Claude Haiku:**
- ~600 tokens input (title + description + tags)
- ~150 tokens output (JSON with scores)
- Cost: ~$0.0003 (3/100th of a cent)

**For full backfill (2000 videos):** ~$0.60

**Monthly refresh (30 videos):** ~$0.01

## Viewing Results

### In Database

```sql
SELECT
  video_id,
  food_type,
  food_volume_score,
  time_limit_score,
  success_rate_score,
  spiciness_score,
  food_diversity_score,
  risk_level_score
FROM challenges
ORDER BY date_attempted DESC
LIMIT 10;
```

### In Published JSON

```powershell
cat public/data/table.json | python -m json.tool | Select-String "food_"
```

## Querying by Scores

### Find hardest challenges:
```sql
SELECT title, food_volume_score + success_rate_score + risk_level_score as difficulty
FROM challenges c
JOIN videos v ON c.video_id = v.video_id
ORDER BY difficulty DESC
LIMIT 10;
```

### Find spiciest challenges:
```sql
SELECT title, spiciness_score, result
FROM challenges c
JOIN videos v ON c.video_id = v.video_id
WHERE spiciness_score >= 8
ORDER BY spiciness_score DESC;
```

### Find by food type:
```sql
SELECT food_type, COUNT(*) as count, AVG(food_volume_score) as avg_volume
FROM challenges
GROUP BY food_type
ORDER BY count DESC;
```

## Troubleshooting

### "Missing anthropic package"

```powershell
pip install anthropic
```

### "LLM extraction failed"

Check API key is set:
```powershell
echo $env:ANTHROPIC_API_KEY
```

### "Column food_type does not exist"

Run migration:
```powershell
sqlite3 data/app.db < db/sqlite_add_challenge_scores.sql
```

### Scores are all 0

LLM extraction is disabled or failed. Check logs:
```
Looking for: "LLM extraction enabled"
```

## Next Steps

### 1. Visualize Scores

Create a dashboard showing:
- Difficulty distribution (volume + time + success_rate)
- Spiciest challenges map
- Food type breakdown by country

### 2. Filter/Sort by Scores

Update frontend to allow:
- "Show only spicy challenges"
- "Sort by difficulty"
- "Filter by food type"

### 3. Aggregate Stats

Calculate:
- Average difficulty per country
- Hardest food types
- Success rate correlation with scores

## Files Modified

- `ingestion/bmf_ingest/llm_extractor.py` - Enhanced prompt + scoring
- `ingestion/bmf_ingest/models.py` - Added score fields
- `ingestion/bmf_ingest/repository.py` - INSERT with new fields
- `ingestion/bmf_ingest/pipeline.py` - LLM integration + publish
- `db/sqlite_init.sql` - New schema with scores
- `db/sqlite_add_challenge_scores.sql` - Migration for existing DBs
- `.github/workflows/refresh_publish.yml` - LLM support
- `test_llm_extraction.py` - Display scores

## Example Queries

### Top 10 hardest challenges:
```sql
SELECT
  v.title,
  c.food_type,
  (c.food_volume_score + c.success_rate_score + c.time_limit_score) as total_difficulty,
  c.result
FROM challenges c
JOIN videos v ON c.video_id = v.video_id
WHERE c.food_volume_score > 0  -- Only LLM-extracted
ORDER BY total_difficulty DESC
LIMIT 10;
```

### Spicy challenges by country:
```sql
SELECT
  r.country_code,
  COUNT(*) as count,
  AVG(c.spiciness_score) as avg_spice,
  MAX(c.spiciness_score) as max_spice
FROM challenges c
JOIN restaurants r ON c.restaurant_id = r.id
WHERE c.spiciness_score > 0
GROUP BY r.country_code
ORDER BY avg_spice DESC;
```

### Food diversity vs success rate:
```sql
SELECT
  CASE
    WHEN food_diversity_score <= 3 THEN 'Simple'
    WHEN food_diversity_score <= 6 THEN 'Moderate'
    ELSE 'Complex'
  END as complexity,
  COUNT(*) as total,
  SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
FROM challenges
WHERE food_diversity_score > 0
GROUP BY complexity;
```
