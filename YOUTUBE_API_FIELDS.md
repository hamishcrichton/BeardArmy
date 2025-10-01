# YouTube API Fields - Complete Usage Audit

## API Parts Requested

**In `youtube_client.py:56`:**
```python
part="snippet,contentDetails,recordingDetails,localizations,topicDetails"
```

## Field-by-Field Breakdown

### ✅ SNIPPET (Fully Utilized)

| Field | Used? | Where | How | Notes |
|-------|-------|-------|-----|-------|
| `snippet.title` | ✅ Yes | `extractors.py:40` | Regex + LLM extraction | Primary source |
| `snippet.description` | ✅ Yes | `extractors.py:40` | Regex + LLM extraction | Full text used |
| `snippet.tags` | ✅ Yes | `extractors.py:42` | Added to extraction context | Array of keywords |
| `snippet.thumbnails` | ✅ Yes | `youtube_client.py:97` | Display in UI | High-quality URL |
| `snippet.channelId` | ✅ Yes | `youtube_client.py:98` | Metadata | Channel reference |
| `snippet.publishedAt` | ✅ Yes | `youtube_client.py:93` | Date fallback | ISO 8601 timestamp |
| `snippet.categoryId` | ❌ No | - | Not requested | Could filter non-food videos |
| `snippet.defaultLanguage` | ❌ No | - | Not requested | Usually "en" |
| `snippet.defaultAudioLanguage` | ❌ No | - | Not requested | Usually "en" |

### ✅ CONTENT DETAILS (Partially Utilized)

| Field | Used? | Where | How | Notes |
|-------|-------|-------|-----|-------|
| `contentDetails.duration` | ✅ Yes | `youtube_client.py:66-67` | Parsed to seconds | ISO 8601 format (PT23M10S) |
| `contentDetails.dimension` | ❌ No | - | Not requested | "2d" or "3d" |
| `contentDetails.definition` | ❌ No | - | Not requested | "hd" or "sd" |
| `contentDetails.caption` | ❌ No | - | Not requested | "true" or "false" (we use yt-dlp instead) |
| `contentDetails.licensedContent` | ❌ No | - | Not requested | Copyright status |
| `contentDetails.regionRestriction` | ❌ No | - | Not requested | Geographic availability |

### ✅ RECORDING DETAILS (High Priority - Fully Utilized)

**This is the gold standard for location data!**

| Field | Used? | Where | How | Notes |
|-------|-------|-------|-----|-------|
| `recordingDetails.location.latitude` | ✅ Yes | `youtube_client.py:74` | Direct coordinates | **Best source** |
| `recordingDetails.location.longitude` | ✅ Yes | `youtube_client.py:75` | Direct coordinates | **Best source** |
| `recordingDetails.location.altitude` | ✅ Yes | `youtube_client.py:76` | Stored (not used) | Elevation in meters |
| `recordingDetails.locationDescription` | ✅ Yes | `youtube_client.py:77` | Used as fallback name | Text description |
| `recordingDetails.recordingDate` | ❌ No | - | Not requested | Date video was filmed |

**Usage in pipeline (`pipeline.py:58-85`):**
```python
if v.recording_location and v.recording_location.get("lat"):
    # Priority 1: Use recording location (95% confidence)
    rest = Restaurant(
        name=ext.restaurant_name or v.recording_location.get("description"),
        lat=v.recording_location["lat"],
        lng=v.recording_location["lng"],
        place_source="youtube_recording"
    )
```

### ✅ LOCALIZATIONS (Minimally Utilized)

| Field | Used? | Where | How | Notes |
|-------|-------|-------|-----|-------|
| `localizations[lang].title` | ⚠️ Minimal | `extractors.py:49` | Checked for hints | Alternate language titles |
| `localizations[lang].description` | ⚠️ Minimal | `extractors.py:51` | First 500 chars only | Could parse more |

**Current usage:**
```python
if video.localizations:
    for lang_code, localized in video.localizations.items():
        if localized.get("title"):
            localized_texts.append(localized["title"])
        if localized.get("description"):
            localized_texts.append(localized["description"][:500])  # Only first 500 chars
```

**Potential improvement:** Non-English descriptions might have better-formatted location info

### ✅ TOPIC DETAILS (Stored but Not Used)

| Field | Used? | Where | How | Notes |
|-------|-------|-------|-----|-------|
| `topicDetails.topicIds` | ⚠️ Stored | `youtube_client.py:82-83` | Saved to Video model | Wikipedia topic IDs |
| `topicDetails.topicCategories` | ❌ No | - | Not requested | Topic URLs |
| `topicDetails.relevantTopicIds` | ❌ No | - | Not requested | Related topics |

**What are topicIds?**
- Wikipedia entity IDs (e.g., `/m/02wbm` = "Food")
- Could be used to filter or categorize videos
- Currently stored but never queried

### ❌ STATISTICS (Not Requested)

**Could be useful for filtering low-quality videos:**

| Field | Available? | Potential Use |
|-------|-----------|---------------|
| `statistics.viewCount` | ✅ Available | Skip videos with <10k views? |
| `statistics.likeCount` | ✅ Available | Quality indicator |
| `statistics.commentCount` | ✅ Available | Engagement metric |

**To request:** Add `"statistics"` to parts list in `youtube_client.py:56`

### ❌ STATUS (Not Requested)

| Field | Available? | Potential Use |
|-------|-----------|---------------|
| `status.uploadStatus` | ✅ Available | Filter "processed" only |
| `status.privacyStatus` | ✅ Available | Filter "public" only |
| `status.license` | ✅ Available | Copyright info |
| `status.embeddable` | ✅ Available | Can embed on website? |
| `status.publicStatsViewable` | ✅ Available | Privacy setting |

### ❌ PLAYER (Not Requested)

| Field | Available? | Potential Use |
|-------|-----------|---------------|
| `player.embedHtml` | ✅ Available | Embed code for preview |
| `player.embedHeight` | ✅ Available | Default dimensions |
| `player.embedWidth` | ✅ Available | Default dimensions |

## Featured Places - Special Case

**Important:** YouTube does NOT expose "Featured Places" via the official API!

**What we do instead:**
- Scrape HTML from `youtube.com/watch?v={video_id}`
- Parse Google Maps links from page source
- Extract coordinates from Maps URLs

**Implementation:** `featured_places.py:27-82`

**Process:**
1. Fetch watch page HTML
2. Find Google Maps links (`google.com/maps` or `maps.app.goo.gl`)
3. Extract coordinates from URL pattern `/@{lat},{lng},`
4. Extract place name from anchor text or URL path

**Priority in pipeline:**
1. ✅ `recordingDetails.location` (API, highest confidence)
2. ✅ Featured Places (HTML scrape, high confidence)
3. ⚠️ Regex/LLM extraction (medium confidence)

**Example Featured Place:**
```html
<a href="https://maps.google.com/maps/place/Illegal+Burger/@59.9139,10.7522,...">
    Illegal Burger
</a>
```

Extracted: `("Illegal Burger", 59.9139, 10.7522)`

## Captions - Via yt-dlp (Not YouTube API)

**Important:** Caption content is NOT available via YouTube Data API v3!

**What we do:**
- Use `yt-dlp` command-line tool to download VTT/SRT files
- Store caption files in `data/captions/`
- Flag `captions_available` but don't parse content (yet)

**Implementation:** `youtube_client.py:123-206`

**Functions:**
- `probe_captions_available()` - Check if captions exist
- `list_captions()` - Get available language codes
- `download_captions()` - Download VTT files (en, en-*, auto-generated)

**Current usage:**
```python
v.captions_available = probe_captions_available(v.video_id)
captions_path = download_captions(v.video_id, "data/captions/")
```

**⚠️ Not currently parsed for extraction content!**

**Proposed improvement (for LLM extraction):**
```python
def extract_caption_intro(vtt_path: str) -> str:
    """Extract first 2-3 minutes of captions for context."""
    # Restaurant usually mentioned in first 60 seconds:
    # "Today I'm at Illegal Burger in Oslo, Norway..."
    return first_500_words
```

## Summary Table

| Data Source | API/Scrape | Used? | Confidence | Notes |
|-------------|-----------|-------|------------|-------|
| **Recording Location** | ✅ API | ✅ Yes | 95% | Best source - direct coords |
| **Featured Places** | 🌐 Scrape | ✅ Yes | 85% | HTML parsing, reliable |
| Title | ✅ API | ✅ Yes | 60% | Regex patterns |
| Description | ✅ API | ⚠️ Partial | 70% | Full text available |
| Tags | ✅ API | ⚠️ Minimal | 50% | Array of keywords |
| Captions | 🔧 yt-dlp | ❌ No | 90% | **Downloaded but not parsed!** |
| Localizations | ✅ API | ⚠️ Minimal | 60% | Only first 500 chars |
| Topic IDs | ✅ API | ❌ No | N/A | Stored but unused |
| Statistics | ❌ Not requested | ❌ No | N/A | Could filter quality |
| Status | ❌ Not requested | ❌ No | N/A | Could filter privacy |

## Recommended Improvements

### 1. Parse Caption Content ⭐⭐⭐
**Impact:** High
**Effort:** Medium

Captions are gold for extraction - restaurant is almost always mentioned in first 60 seconds:
```
"Today I'm at Illegal Burger in Oslo, Norway attempting..."
```

**Implementation:**
```python
# New file: caption_parser.py
def parse_vtt_intro(vtt_path: str, max_duration_seconds: int = 180) -> str:
    """Parse first 3 minutes of VTT captions."""
    # Parse timestamps and extract text
    # Return first ~500 words
```

### 2. Request Recording Date ⭐⭐
**Impact:** Medium
**Effort:** Low

Add `recordingDetails.recordingDate` to know exact filming date (often differs from publish date).

**Change:** `youtube_client.py:77`
```python
recording_location = {
    "lat": loc.get("latitude"),
    "lng": loc.get("longitude"),
    "date": recording.get("recordingDate"),  # NEW
}
```

### 3. Add Statistics for Quality Filtering ⭐
**Impact:** Low
**Effort:** Low

Filter out unpopular videos (likely mistakes or private videos):
```python
part="snippet,contentDetails,recordingDetails,localizations,topicDetails,statistics"

# Later, filter:
if video.view_count < 10000:
    logger.info(f"Skipping low-view video {video.video_id}")
    continue
```

### 4. Parse Full Localizations ⭐
**Impact:** Low
**Effort:** Low

Currently only checking first 500 chars - parse full descriptions:
```python
for lang_code, localized in video.localizations.items():
    if localized.get("description"):
        localized_texts.append(localized["description"])  # Full text
```

## API Quota Usage

**Current quota cost per video:**
- `playlistItems.list`: 1 unit (to get video IDs)
- `videos.list` with 5 parts: 5 units per video

**Daily quota:** 10,000 units (default free tier)

**Videos per day:** ~1,900 videos per day

**For full backfill (2000 videos):** ~10,000 units = 1 day quota

## Conclusion

**Currently using well:**
✅ Recording Location (API) - Priority #1
✅ Featured Places (HTML scrape) - Priority #2
✅ Title, Description, Tags (API) - Used in extraction

**Underutilized:**
⚠️ **Captions** - Downloaded but content not parsed (HIGH PRIORITY)
⚠️ Localizations - Only first 500 chars checked
⚠️ Topic IDs - Stored but never used

**Not requested but potentially useful:**
- Statistics (view count, likes) for quality filtering
- Recording date for accurate timeline
- Status fields for filtering

**Next Steps:**
1. **Implement caption parsing** (`caption_parser.py`) for LLM context
2. Add `recordingDate` to metadata
3. Consider requesting `statistics` for quality filtering
