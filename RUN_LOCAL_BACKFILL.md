# Local Backfill with LLM Extraction

## Problem Identified

Your current `data/app.db` was created with the **old schema** and doesn't have LLM extraction enabled. This is why:
- ❌ All restaurant/city/country fields are `null`
- ❌ Still shows old `"type": "quantity"` instead of `food_type`
- ❌ No challenge difficulty scores
- ❌ GeoJSON is empty (no locations to geocode)

## What I Did

✅ **Backed up old database**: `data/app.db.backup-20251001-105431`
✅ **Recreated database**: Now uses new schema with `food_type` and scoring fields

## Run Local Backfill (PowerShell)

Since you successfully tested from PowerShell before, run this there:

```powershell
# Open PowerShell in project directory
cd C:\Users\hamis\PycharmProjects\BeardArmy

# Set environment variables (use your actual API keys)
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."
$env:USE_LLM_EXTRACTION = "true"
$env:LLM_PROVIDER = "anthropic"
$env:YOUTUBE_API_KEY = "AIza..."

# Test with just 5 recent videos first
cd ingestion
python -m bmf_ingest.main refresh --channel UCc9CjaAjsMMvaSghZB7-Kog --since-days 30

# Check results
cd ..
python -m bmf_ingest.main publish --out ./public/data

# Verify table.json has data
Get-Content public/data/table.json | Select-String "restaurant"
```

### Expected Output

You should see log lines like:
```
INFO: Extracted 487 words from captions for KPysiwgpWCk
INFO: LLM extracted for KPysiwgpWCk: {'restaurant': 'Super Mario's Pizza', 'city': 'Las Vegas', ...}
```

### Check Results

After running, check `public/data/table.json` - you should now see:
```json
{
  "restaurant": "Super Mario's Pizza",
  "city": "Las Vegas",
  "country_code": "US",
  "result": "failure",
  "food_type": "pizza",
  "food_volume_score": 9,
  "time_limit_score": 6,
  ...
}
```

## Full Backfill (All Videos)

Once the test works, run the full backfill:

```powershell
# This will process ALL ~2000 videos (takes 30-60 minutes)
cd ingestion
python -m bmf_ingest.main backfill --channel UCc9CjaAjsMMvaSghZB7-Kog

# Publish results
cd ..
python -m bmf_ingest.main publish --out ./public/data

# Commit and push
git add data/app.db public/data
git sync   # Uses the new git alias I created
```

## Alternative: Run on GitHub Actions

Instead of running locally, you can configure GitHub Actions and let it do the work:

### 1. Add GitHub Secret
Go to: https://github.com/hamishcrichton/BeardArmy/settings/secrets/actions

- Click "New repository secret"
- Name: `ANTHROPIC_API_KEY`
- Value: Your Anthropic API key

### 2. Add GitHub Variables
Same page, click "Variables" tab:

- Variable 1:
  - Name: `USE_LLM_EXTRACTION`
  - Value: `true`

- Variable 2:
  - Name: `LLM_PROVIDER`
  - Value: `anthropic`

### 3. Delete Old Database from Repo

```powershell
# Remove old database so GitHub Actions creates a new one
git rm data/app.db
git commit -m "chore: remove old database for schema migration"
git sync
```

### 4. Trigger Backfill

1. Go to: https://github.com/hamishcrichton/BeardArmy/actions
2. Click "Refresh and Publish Artifacts"
3. Click "Run workflow"
4. Select mode: `backfill`
5. Click "Run workflow"

The workflow will:
- Create fresh database with new schema
- Download captions for all videos
- Extract metadata with LLM
- Geocode locations
- Publish to `public/data/`
- Commit results

**Cost**: ~$0.80 for ~2000 videos

## Verify Results

After backfill (local or GitHub Actions), verify:

```powershell
# Check table.json has populated fields
Get-Content public/data/table.json | Select-String "restaurant" | Select-Object -First 5

# Check GeoJSON has features
Get-Content public/data/challenges.geojson | Select-String "features"
```

You should see actual restaurant names, not `null`.

## Why This Happened

The original database was created before the LLM extraction changes. The GitHub Actions workflow has a migration step:

```yaml
sqlite3 data/app.db < db/sqlite_add_challenge_scores.sql 2>/dev/null || echo "Migration already applied"
```

However, this migration only **adds columns** to the old schema. It doesn't:
- Change the schema from foreign-key based (`restaurant_id`) to inline fields (`restaurant`, `city`, `country`)
- Re-run extraction with LLM enabled

**Solution**: Fresh database + full backfill with LLM enabled.

## Summary

**Problem**: Old database without LLM extraction
**Fix**: Recreated database with new schema
**Next**: Run backfill (locally in PowerShell OR via GitHub Actions)
**Result**: All videos will have restaurant/location/scores populated

Choose your preferred approach:
- 💻 **Local (PowerShell)**: Full control, see logs in real-time
- ☁️ **GitHub Actions**: Set it and forget it, free compute

Either way, the end result is the same: a fully populated dataset with LLM-powered extraction!
