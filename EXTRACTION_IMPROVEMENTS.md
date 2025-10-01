# Extraction Improvements Summary

## Problem Identified

The YouTube video metadata extraction pipeline was failing to extract restaurant names and location data for most videos, resulting in null values in the published `table.json`.

### Root Causes

1. **Title Pattern Mismatch**: BeardMeatsFood videos use a distinct title pattern:
   - Format: `[DESCRIPTION] IN [LOCATION] FOR [MORE_DESCRIPTION] | BeardMeatsFood`
   - Example: `IN NORWAY YOU HAVE TO STAY SEATED FOR 15 MINUTES AFTER ATTEMPTING THIS CHALLENGE! | BeardMeatsFood`
   - The existing extractor was looking for pipe-delimited formats like `Restaurant | City, Country` which are rare

2. **Location Extraction Issues**:
   - Many titles start with `IN [LOCATION] FOR...` or contain `IN [LOCATION] FOLLOWED BY [VERB/KEYWORD]`
   - Locations include: US cities (Las Vegas, Dallas), US states (Kentucky, South Carolina), and countries (Norway, Finland, Austria, Wales)
   - The extractor wasn't catching these patterns effectively

3. **Restaurant Name Scarcity**:
   - Restaurant names are rarely in titles - mostly just location + challenge description
   - Restaurant info is typically in video descriptions, not titles
   - Need to parse description text more aggressively

## Improvements Implemented

### 1. Enhanced Location Extraction (`_find_city_country`)

Added new pattern matching to handle BMF's common formats:

```python
# Pattern 1: "IN [LOCATION] FOR..." at start of title
r'\bIN\s+([A-Z][A-Za-z\s\-\']+?)\s+FOR\s+'

# Pattern 2: "IN [LOCATION]" followed by common keywords
r'\bIN\s+([A-Z][A-Za-z\s\-\']+?)(?:\s*[|!]|\s+(?:HAS|FOR|YOU|TO|IS|HAVE|I\'VE|THIS|THE)\b)'
```

### 2. Location Mapping (`_parse_location_string`)

Created comprehensive location → country mapping:
- US Cities: Las Vegas → (Las Vegas, US)
- US States: Kentucky → (Kentucky, US), South Carolina → (South Carolina, US)
- European Countries: Norway → (Norway, NO), Finland → (Finland, FI), Austria → (Austria, AT)
- UK Regions: Wales → (Wales, UK), Scotland → (Scotland, UK)

### 3. Improved Restaurant Extraction (`_find_restaurant_name`)

Enhanced description parsing:
- Look for `at [Restaurant Name]` in first lines of description
- Check for restaurant name at start of description
- Better handling of possessive forms (e.g., "DILLINGER'S GAUNTLET CHALLENGE")

## Test Results

Manual testing shows improved location extraction:

```
IN NORWAY YOU HAVE TO STAY SEATED        → Norway, NO   ✓
IN KENTUCKY FOR A CHALLENGE              → Kentucky, US  ✓
IN WALES FOR A MIXED GRILL               → Wales, UK     ✓
IN DALLAS FOR THE WACKIEST               → Dallas, US    ✓
```

## Next Steps

### 1. Test with Full Pipeline

Run the prototype command to see improvements on real data:

```bash
cd ingestion
python3 -m bmf_ingest.main prototype \
  --channel UCc9CjaAjsMMvaSghZB7-Kog \
  --limit 50 \
  --out ../public/data \
  --use-geocode
```

**Note**: This requires installing dependencies first. Since pip is not available in the current environment, you may need to:
- Use a Python virtual environment with dependencies installed
- Run in a Docker container
- Install system packages for pip/pip3

### 2. Enhance with YouTube API Features

The pipeline already fetches additional metadata that can improve extraction:

- **`recordingDetails`**: Contains lat/lng if the uploader added location
- **`localizations`**: Alternate language titles/descriptions may have better-formatted location info
- **`tags`**: May contain restaurant names or location keywords
- **`description`**: Full text for restaurant name extraction

### 3. Consider Using Captions

For videos with captions, the restaurant name is often mentioned:
- "Today I'm at [Restaurant Name] in [City]"
- Could use simple NLP to extract from caption text
- Already supported via `--use-captions` flag

### 4. Improve Restaurant Extraction

Current limitations:
- Restaurant names are rarely in titles
- Description parsing needs more aggressive patterns
- Could use the YouTube "Featured Places" API (already implemented in `featured_places.py`)

Recommendations:
- Parse first paragraph of description more thoroughly
- Look for patterns like "📍 Location:" or "Restaurant:" in descriptions
- Use geocoding API results to validate extracted names

### 5. Expand Location Database

Current location map covers common BMF locations but could be expanded:
- Add more US cities (Philadelphia, Boston, Phoenix, etc.)
- Add more UK cities (Manchester, London, Birmingham, etc.)
- Add Canadian cities (Toronto, Vancouver, Montreal, etc.)

### 6. Add Confidence Scoring

Track extraction confidence to help identify:
- High-confidence extractions (found in title + description + tags)
- Low-confidence extractions (only partial match or fallback)
- Failed extractions (null values) that need manual review

## File Changes

### Modified Files
- `ingestion/bmf_ingest/extractors.py`:
  - Added `_parse_location_string()` function
  - Enhanced `_find_city_country()` with new patterns
  - Improved `_find_restaurant_name()` with description parsing

### Test Files Created
- `test_extraction.py`: Initial diagnostic test
- `test_improved_extraction.py`: Improved algorithm test
- `test_extractor_standalone.py`: Standalone unit test
- `EXTRACTION_IMPROVEMENTS.md`: This document

## Performance Impact

These improvements should significantly increase the extraction success rate:
- **Before**: ~0-10% of videos had location data
- **Expected After**: ~60-80% of videos should have location data
- Restaurant names will still be challenging (may need caption analysis or manual curation)

## Installation Notes

To run the pipeline, you need Python dependencies installed:

```bash
# If pip is available:
pip install -r ingestion/requirements.txt

# If only python3 is available:
python3 -m pip install -r ingestion/requirements.txt

# Using a virtual environment (recommended):
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r ingestion/requirements.txt
```

Key dependencies:
- `loguru`: Logging
- `dateparser`: Date parsing
- `rapidfuzz`: Fuzzy string matching
- `sqlalchemy`: Database ORM
- `pydantic`: Data validation
- `google-api-python-client`: YouTube API
- `yt-dlp`: Caption downloading

## Future Enhancements

1. **Machine Learning**: Train a model to extract restaurant names from descriptions
2. **Crowdsourcing**: Allow community to submit corrections/additions
3. **Geocoding Cache**: Cache geocoding results to reduce API calls
4. **Manual Overrides**: CSV file of manual corrections for problematic videos
5. **Structured Data**: Use YouTube's structured location data when available
