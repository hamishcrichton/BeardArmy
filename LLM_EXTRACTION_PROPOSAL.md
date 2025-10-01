# LLM-Based Extraction Architecture Proposal

## Current State Analysis

### What We're Fetching from YouTube API ✅

**Currently Used:**
- `snippet.title` ✅ - Used in regex extraction
- `snippet.description` ✅ - Partially used (only first few lines)
- `snippet.tags` ✅ - Added to extraction context
- `snippet.thumbnails` ✅ - For display
- `contentDetails.duration` ✅ - Stored
- `recordingDetails.location` ✅ - Priority source for coordinates (pipeline.py:58-85)
- `localizations` ✅ - Checked for alternate language hints

**Available but Underutilized:**
- Full description text (we only check first 3 lines)
- Captions/transcripts (downloaded but not parsed for extraction)
- Featured Places (scraped from HTML, not API)
- Video comments (not fetched at all)

### What We're Missing ❌

1. **Full Description Parsing**: Currently only scanning first 3 lines for restaurant names
2. **Caption Content**: Downloaded but not used for extraction (only availability flag)
3. **Structured Location Data**: YouTube doesn't expose "Featured Places" via API - we scrape HTML
4. **Rich Context**: Not combining all signals (title + description + tags + captions) holistically

## The Core Problem

**Regex patterns are brittle and fail for:**
- Non-standard title formats
- Restaurant names buried in descriptions
- Contextual location references ("back in Texas", "returned to this spot")
- Ambiguous patterns (Is "MARIO" a restaurant or part of challenge description?)

## Proposed Solution: LLM-Based Extraction

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Data Collection Layer (YouTube API)                        │
│  - Title, Description, Tags, Localizations                  │
│  - Recording Location (lat/lng if available)                │
│  - Captions (via yt-dlp)                                    │
│  - Featured Places (HTML scrape)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Extraction Strategy Selector                                │
│  ┌─────────────────┬────────────────┬────────────────────┐  │
│  │ High Confidence │ Medium Conf.   │ Low Confidence     │  │
│  │ (has recording  │ (has featured  │ (title/desc only)  │  │
│  │  location)      │  place)        │                    │  │
│  └─────────────────┴────────────────┴────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LLM Extraction Engine                                       │
│  - Prompt: "Extract restaurant, city, country from video"   │
│  - Input: Rich context (all available text)                 │
│  - Output: Structured JSON                                  │
│  - Model: Claude Haiku (fast + cheap) or GPT-4o-mini       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Validation & Enrichment Layer                              │
│  - Merge LLM output with API location data                  │
│  - Geocode if needed                                        │
│  - Confidence scoring                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    [Database]
```

### Implementation Details

#### 1. Enhanced Data Collection

**Improve caption usage:**
```python
def extract_from_captions(captions_path: str) -> str:
    """Extract first 2-3 minutes of captions for context."""
    # Parse VTT/SRT and get first ~500 words
    # Focus on intro where restaurant is usually mentioned
    return caption_text[:500]
```

**Full description parsing:**
```python
def prepare_extraction_context(video: Video, captions: Optional[str] = None) -> dict:
    """Prepare rich context for LLM extraction."""
    return {
        "title": video.title,
        "description": video.description[:1000],  # First 1000 chars
        "tags": video.tags,
        "captions_intro": captions[:500] if captions else None,
        "recording_location": video.recording_location,
    }
```

#### 2. LLM Extraction Module

**New file: `ingestion/bmf_ingest/llm_extractor.py`**

```python
from anthropic import Anthropic
from typing import Optional
import json

EXTRACTION_PROMPT = """You are extracting food challenge metadata from a BeardMeatsFood YouTube video.

Given the video metadata below, extract:
1. Restaurant/venue name (if mentioned)
2. City/location
3. Country (use ISO 2-letter codes: US, UK, CA, etc.)
4. Challenge result (success, failure, or unknown)

Video Title: {title}

Description:
{description}

Tags: {tags}

Captions (first 2 minutes):
{captions}

Respond ONLY with valid JSON:
{{
  "restaurant": "Restaurant Name" or null,
  "city": "City Name" or null,
  "country": "US" or null,
  "result": "success" or "failure" or "unknown",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}}
"""

class LLMExtractor:
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def extract(self, context: dict) -> dict:
        """Extract metadata using LLM."""
        prompt = EXTRACTION_PROMPT.format(
            title=context.get("title", ""),
            description=context.get("description", "")[:800],
            tags=", ".join(context.get("tags", [])),
            captions=context.get("captions_intro", "Not available")
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.0,  # Deterministic
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        result = json.loads(response.content[0].text)
        return result
```

#### 3. Hybrid Approach: Fallback Chain

```python
def extract_with_fallback(video: Video, settings: Settings) -> Extracted:
    """Multi-strategy extraction with confidence scoring."""

    # Strategy 1: Recording location from YouTube API (highest confidence)
    if video.recording_location and video.recording_location.get("lat"):
        # Already have coordinates from API - just need restaurant name
        if settings.llm_api_key:
            llm_result = llm_extract_restaurant_only(video)
            return merge_with_recording_location(video, llm_result)

    # Strategy 2: Featured Places scraping (high confidence)
    featured = get_featured_place(video.video_id)
    if featured:
        # Has name + maybe coords, use LLM for city/country
        if settings.llm_api_key:
            llm_result = llm_extract_location_only(video)
            return merge_with_featured_place(featured, llm_result)

    # Strategy 3: Full LLM extraction (medium confidence)
    if settings.llm_api_key:
        context = prepare_extraction_context(video)
        return llm_extractor.extract(context)

    # Strategy 4: Fallback to regex (low confidence)
    return extract_from_video_regex(video)
```

### Cost Analysis

**Claude Haiku Pricing (as of Jan 2025):**
- Input: $0.25 / million tokens
- Output: $1.25 / million tokens

**Per video cost:**
- Input: ~500 tokens (title + description + tags) = $0.000125
- Output: ~100 tokens (JSON response) = $0.000125
- **Total: ~$0.00025 per video**

**For 500 videos:** ~$0.125 (12.5 cents)

**Alternative: GPT-4o-mini**
- Even cheaper: $0.150/1M input, $0.600/1M output
- Per video: ~$0.00015

### Advantages of LLM Approach

1. **Robust to Format Variations**: Handles any title/description format
2. **Context-Aware**: Understands "returned to X" or "back in Y"
3. **Multi-Source**: Naturally combines title + description + captions
4. **Self-Documenting**: LLM provides reasoning for extractions
5. **Confidence Scoring**: Can estimate extraction reliability
6. **Easy to Extend**: Add new fields without regex engineering

### Disadvantages & Mitigations

1. **Cost**: ~$0.00025/video (mitigate with caching, batch processing)
2. **Latency**: ~500ms per video (mitigate with async processing)
3. **API Dependency**: Requires external service (mitigate with fallback to regex)
4. **Non-Determinism**: Slight variations (mitigate with temperature=0, structured output)

## Recommended Implementation Plan

### Phase 1: Add LLM as Optional Enhancement (Week 1)
- Add `llm_extractor.py` module
- Make LLM extraction opt-in via `--use-llm` flag
- Run side-by-side with regex, compare results
- Store both extractions for evaluation

### Phase 2: Enhanced Caption Usage (Week 2)
- Parse caption VTT files for first 2-3 minutes
- Feed intro captions to LLM for context
- Measure improvement in restaurant name extraction

### Phase 3: Hybrid Strategy (Week 3)
- Implement fallback chain (API location → Featured Place → LLM → Regex)
- Add confidence scoring across all strategies
- Use LLM selectively (only when needed)

### Phase 4: Optimization (Week 4)
- Batch LLM requests where possible
- Cache LLM responses keyed by video_id
- Add retry logic with exponential backoff
- Monitor costs and adjust model selection

## Alternative: Local LLM

For cost-sensitive scenarios, consider local models:

**Options:**
- **Ollama** with `llama3.1:8b` or `mistral:7b`
- **llama.cpp** with quantized models
- **vLLM** for batch processing

**Tradeoffs:**
- Zero API cost
- Requires GPU (or slow CPU inference)
- Lower quality than Claude/GPT
- More complex deployment

## Immediate Next Steps

1. **Prototype LLM extraction** on 10-20 sample videos
2. **Compare accuracy** vs current regex approach
3. **Measure cost** and latency for full backfill
4. **Decide**: Is accuracy improvement worth the cost?

## Code Changes Summary

**New Files:**
- `ingestion/bmf_ingest/llm_extractor.py` - LLM extraction module
- `ingestion/bmf_ingest/caption_parser.py` - Parse VTT/SRT captions

**Modified Files:**
- `ingestion/bmf_ingest/pipeline.py` - Add LLM fallback chain
- `ingestion/bmf_ingest/extractors.py` - Keep as fallback
- `ingestion/bmf_ingest/config.py` - Add LLM API key config
- `.env.example` - Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

**New Dependencies:**
```
anthropic>=0.40.0    # or openai>=1.0.0
```

## Evaluation Metrics

Track these metrics to evaluate LLM vs regex:

1. **Extraction Rate**: % of videos with non-null restaurant/location
2. **Accuracy**: Manual verification of 50-100 samples
3. **Cost**: Total $ spent on LLM calls
4. **Latency**: Time to process full backfill
5. **Confidence Distribution**: How often is confidence >0.8?

## Conclusion

**Recommendation: YES, use LLM extraction**

The current regex approach is fundamentally limited by format brittleness. For ~$0.00025 per video, LLM extraction provides:
- **Significantly higher accuracy** (est. 60% → 90%+ extraction rate)
- **Better context understanding** (descriptions, captions, localization)
- **Easier maintenance** (no regex engineering)
- **Built-in reasoning** (explainable extractions)

Start with a prototype on 20 videos to validate the approach, then roll out gradually with the hybrid fallback chain.
