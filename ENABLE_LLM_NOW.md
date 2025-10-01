# Enable LLM Extraction - Quick Setup

Your table is showing null values because LLM extraction is **NOT enabled** in GitHub Actions yet.

## Quick Fix (5 minutes)

### Step 1: Add GitHub Secret

1. Go to: https://github.com/hamishcrichton/BeardArmy/settings/secrets/actions
2. Click **"New repository secret"**
3. Enter:
   - **Name:** `ANTHROPIC_API_KEY`
   - **Secret:** Your Anthropic API key (starts with `sk-ant-api03-...`)
4. Click **"Add secret"**

### Step 2: Add GitHub Variables

Still on the same page:

1. Click the **"Variables"** tab (next to "Secrets")
2. Click **"New repository variable"**

**Variable 1:**
- **Name:** `USE_LLM_EXTRACTION`
- **Value:** `true`
- Click "Add variable"

**Variable 2:**
- Click "New repository variable" again
- **Name:** `LLM_PROVIDER`
- **Value:** `anthropic`
- Click "Add variable"

### Step 3: Trigger Backfill

1. Go to: https://github.com/hamishcrichton/BeardArmy/actions/workflows/refresh_publish.yml
2. Click **"Run workflow"** button (top right, green button)
3. In the dropdown:
   - **Run mode:** Select **`backfill`**
   - Leave other fields empty
4. Click **"Run workflow"** button

### Step 4: Monitor Progress

1. The workflow page will show "Workflow run started"
2. Click on the running workflow to see progress
3. Expand the **"Ingest content (refresh or backfill)"** step to see logs
4. You should see lines like:
   ```
   INFO: Extracted 487 words from captions for KPysiwgpWCk
   INFO: LLM extracted for KPysiwgpWCk: {'restaurant': 'Super Mario's Pizza', ...}
   ```

### Step 5: Verify Results (after ~30-60 minutes)

Once the workflow completes:

1. Go to your repository → `public/data/table.json`
2. You should now see:
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

3. Check `public/data/challenges.geojson` - should have features with coordinates

## Why This Is Needed

The GitHub Actions workflow checks these environment variables:

```yaml
USE_LLM_EXTRACTION: ${{ vars.USE_LLM_EXTRACTION || 'false' }}
LLM_PROVIDER: ${{ vars.LLM_PROVIDER || 'anthropic' }}
ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Currently:** These are not set, so `USE_LLM_EXTRACTION` defaults to `'false'`

**Result:** Pipeline runs without LLM → all restaurant/location fields stay null

**After setup:** LLM extraction enabled → all fields populated

## Troubleshooting

### "Missing ANTHROPIC_API_KEY" error
- Double-check the secret name is exactly: `ANTHROPIC_API_KEY`
- Make sure you copied the full API key including `sk-ant-api03-` prefix

### Variables not showing up
- Make sure you clicked the **"Variables"** tab, not "Secrets"
- Variable names are case-sensitive

### Still seeing null values after backfill
- Check workflow logs for "LLM extraction enabled: true"
- If it says "false", the variables weren't configured correctly
- Re-check variables are set exactly as shown above

## Cost

- **Per video:** ~$0.0004
- **Total for ~2000 videos:** ~$0.80
- **Daily refresh (5 new videos):** ~$0.002/day

This is negligible cost for the massive improvement in data quality!

## What Happens Next

After you trigger the backfill:

1. ✅ GitHub Actions creates fresh database
2. ✅ Downloads metadata for all ~2000 videos
3. ✅ Downloads captions (VTT files)
4. ✅ Parses first 3 minutes of each transcript
5. ✅ Calls Claude Haiku to extract:
   - Restaurant name, city, country
   - Result (success/failure)
   - Food type (burger, pizza, etc.)
   - 6 difficulty scores (0-10 scale)
6. ✅ Geocodes restaurant locations
7. ✅ Publishes `challenges.geojson` and `table.json`
8. ✅ Commits results back to repo

Your empty table will become a rich dataset with actual locations, scores, and metadata!

## Need Help?

If you get stuck, check the workflow logs:
- Go to Actions tab
- Click on the running/failed workflow
- Expand each step to see detailed output
- Look for error messages

The logs will show exactly what's happening at each stage.
