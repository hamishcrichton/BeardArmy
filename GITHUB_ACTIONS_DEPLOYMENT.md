# GitHub Actions Deployment Guide

This guide will help you enable LLM extraction with caption parsing in GitHub Actions and backfill all BeardMeatsFood videos.

## Prerequisites

- GitHub repository with admin access
- Anthropic API key (for Claude Haiku) OR OpenAI API key (for GPT-4o-mini)
- YouTube Data API v3 key (already configured)

## Step 1: Configure GitHub Secrets

Go to your repository on GitHub:

1. Click **Settings** (top menu)
2. Click **Secrets and variables** → **Actions** (left sidebar)
3. Click **New repository secret**

### Add LLM API Key

**For Anthropic (Recommended - cheaper):**
- Name: `ANTHROPIC_API_KEY`
- Value: `sk-ant-api03-...` (your Anthropic API key)

**For OpenAI (Alternative):**
- Name: `OPENAI_API_KEY`
- Value: `sk-...` (your OpenAI API key)

### Verify Existing Secrets

Make sure these are already configured:
- ✅ `YOUTUBE_API_KEY` - YouTube Data API v3 key
- ✅ `GEOCODER_API_KEY` - Geocoding API key (optional)

## Step 2: Configure GitHub Variables

Still in **Settings** → **Secrets and variables** → **Actions**:

1. Click the **Variables** tab
2. Click **New repository variable**

### Add LLM Configuration Variables

**Variable 1: Enable LLM Extraction**
- Name: `USE_LLM_EXTRACTION`
- Value: `true`

**Variable 2: Select LLM Provider**
- Name: `LLM_PROVIDER`
- Value: `anthropic` (or `openai`)

### Verify Existing Variables

Make sure these are configured:
- ✅ `YOUTUBE_CHANNEL_ID` - BeardMeatsFood channel ID: `UCc9CjaAjsMMvaSghZB7-Kog`
- ✅ `GEOCODER_PROVIDER` - e.g., `opencage` or `nominatim`

## Step 3: Run Backfill

Now that everything is configured, trigger the backfill:

1. Go to **Actions** tab in your repository
2. Click **Refresh and Publish Artifacts** workflow (left sidebar)
3. Click **Run workflow** button (top right)
4. Configure the workflow run:
   - **Run mode**: Select `backfill` (to process all videos)
   - **Days to look back**: Leave empty (not used for backfill)
   - **Channel ID**: Leave empty (uses default BeardMeatsFood channel)
5. Click **Run workflow** (green button)

## What Happens During Backfill

The workflow will:

1. ✅ **Fetch all videos** from BeardMeatsFood channel (~2000+ videos)
2. ✅ **Download captions** for each video (VTT format)
3. ✅ **Parse transcripts** (first 3 minutes, ~500 words per video)
4. ✅ **Extract metadata with LLM**:
   - Restaurant name, city, country
   - Challenge result (success/failure/unknown)
   - Food type (burger, pizza, bbq, etc.)
   - 6 difficulty scores (0-10 scale):
     - food_volume_score
     - time_limit_score
     - success_rate_score
     - spiciness_score
     - food_diversity_score
     - risk_level_score
5. ✅ **Geocode locations** (if geocoding enabled)
6. ✅ **Publish JSON/GeoJSON** artifacts to `public/data/`
7. ✅ **Commit and push** updated database and artifacts

## Monitoring Progress

### View Workflow Logs

1. Go to **Actions** tab
2. Click on the running workflow
3. Click on the **refresh** job
4. Expand steps to see detailed logs:
   - "Ingest content" - Shows video processing
   - "Publish artifacts" - Shows output generation

### Check Output

After completion, view the **Inspect published outputs** step logs to see:
- Number of videos processed
- Number of restaurants found
- Number of challenges recorded
- Number of geocoded locations

### Expected Metrics

For ~2000 BeardMeatsFood videos:
- **Runtime**: ~30-60 minutes (depends on API rate limits)
- **LLM API Cost**: ~$0.80 (using Claude Haiku)
- **Extraction Success**: ~85-90% (vs. ~20% with regex-only)
- **Caption Availability**: ~80% of videos have captions

## Verification

After backfill completes, check the published data:

1. Go to repository → `public/data/` folder
2. Open `table.json` - should show:
   - Restaurant names populated
   - Results (success/failure) detected
   - Food types identified
   - Challenge scores (0-10 for each metric)

### Sample Entry

```json
{
  "video_id": "abc123",
  "title": "I DEMOLISHED THE 10LB BURGER CHALLENGE",
  "restaurant": "Big Bob's Diner",
  "city": "Austin",
  "country": "US",
  "result": "success",
  "food_type": "burger",
  "food_volume_score": 9,
  "time_limit_score": 5,
  "success_rate_score": 8,
  "spiciness_score": 2,
  "food_diversity_score": 3,
  "risk_level_score": 6
}
```

## Cost Breakdown

### Using Anthropic (Claude Haiku - Recommended)

- **Input**: ~900 tokens/video (title + description + 500 word transcript)
- **Output**: ~100 tokens/video (JSON response)
- **Cost per video**: ~$0.0004
- **Total for 2000 videos**: ~$0.80

### Using OpenAI (GPT-4o-mini - Alternative)

- Similar token usage
- Cost per video: ~$0.0003
- Total for 2000 videos: ~$0.60

## Ongoing Refresh

After the initial backfill, the workflow runs automatically:

- **Schedule**: Daily at 03:00 UTC
- **Mode**: Refresh (only processes videos from last 7 days)
- **Cost**: ~$0.002/day (assuming 5 new videos/day)

This keeps your dataset up-to-date with new BeardMeatsFood videos.

## Troubleshooting

### Workflow Fails with "Missing ANTHROPIC_API_KEY"

**Cause**: Secret not configured or misspelled
**Fix**:
1. Go to Settings → Secrets and variables → Actions
2. Verify `ANTHROPIC_API_KEY` is spelled correctly
3. Re-enter the API key

### LLM Extraction Not Running

**Cause**: Variables not configured
**Fix**:
1. Go to Settings → Secrets and variables → Actions → Variables tab
2. Add `USE_LLM_EXTRACTION=true`
3. Add `LLM_PROVIDER=anthropic`
4. Re-run workflow

### Caption Parsing Errors

**Cause**: Some videos don't have captions (expected)
**Behavior**: Workflow continues, falls back to title/description-only extraction
**No action needed**: This is normal - ~20% of videos don't have captions

### Migration Error: "table challenges has no column named food_type"

**Cause**: Old database schema missing new columns
**Fix**: The workflow automatically applies migration in step "Initialize SQLite schema"
**Verify**: Check logs for "Applying challenge scoring migration" - should show success

## Manual Backfill (Local Testing)

If you want to test locally before GitHub Actions:

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."
$env:USE_LLM_EXTRACTION = "true"
$env:LLM_PROVIDER = "anthropic"
$env:YOUTUBE_API_KEY = "AIza..."

# Apply migration to existing DB
sqlite3 data/app.db < db/sqlite_add_challenge_scores.sql

# Run backfill
python -m bmf_ingest.main backfill --channel UCc9CjaAjsMMvaSghZB7-Kog

# Publish artifacts
python -m bmf_ingest.main publish --out ./public/data
```

## Summary

**Configuration Checklist:**
- ✅ Secret: `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`)
- ✅ Variable: `USE_LLM_EXTRACTION=true`
- ✅ Variable: `LLM_PROVIDER=anthropic` (or `openai`)

**Execution:**
1. Go to Actions → Refresh and Publish Artifacts
2. Click "Run workflow"
3. Select mode: `backfill`
4. Click "Run workflow"

**Expected Outcome:**
- ~2000 videos processed with LLM extraction
- ~85-90% extraction success rate
- Challenge difficulty scores for all videos
- Total cost: ~$0.80

🎉 **Your BeardMeatsFood dataset is now enhanced with AI-powered extraction!**
