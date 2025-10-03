from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from googleapiclient.discovery import build
from loguru import logger
import sys

from .models import Video


def _build_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def get_uploads_playlist_id(youtube, channel_id: str) -> str:
    resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"Channel not found: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_videos(api_key: str, channel_id: str, published_after: Optional[datetime] = None) -> Iterable[str]:
    """Yield video IDs from the channel uploads."""
    youtube = _build_client(api_key)
    uploads_id = get_uploads_playlist_id(youtube, channel_id)
    page_token = None
    while True:
        req = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_id, maxResults=50, pageToken=page_token
        )
        resp = req.execute()
        for it in resp.get("items", []):
            vid = it["contentDetails"]["videoId"]
            if published_after:
                published = it["contentDetails"].get("videoPublishedAt")
                if published and datetime.fromisoformat(published.replace("Z", "+00:00")) < published_after:
                    continue
            yield vid
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def fetch_videos(api_key: str, video_ids: List[str]) -> List[Video]:
    if not video_ids:
        return []
    youtube = _build_client(api_key)
    out: List[Video] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        # Fetch additional parts for enhanced metadata
        resp = youtube.videos().list(
            part="snippet,contentDetails,recordingDetails,localizations,topicDetails", 
            id=",".join(batch)
        ).execute()
        for it in resp.get("items", []):
            snip = it["snippet"]
            content = it.get("contentDetails", {})
            recording = it.get("recordingDetails", {})
            localizations = it.get("localizations", {})
            topic_details = it.get("topicDetails", {})
            
            duration_iso = content.get("duration")  # e.g., PT23M10S
            duration_seconds = _iso8601_duration_to_seconds(duration_iso) if duration_iso else None
            
            # Extract recording location if available
            recording_location = None
            if recording.get("location"):
                loc = recording["location"]
                recording_location = {
                    "lat": loc.get("latitude"),
                    "lng": loc.get("longitude"),
                    "altitude": loc.get("altitude"),
                    "description": recording.get("locationDescription")
                }
            
            # Extract topic IDs if available
            topics = []
            if topic_details.get("topicIds"):
                topics = topic_details["topicIds"]
            
            # Extract tags from snippet
            tags = snip.get("tags", [])
            
            out.append(
                Video(
                    video_id=it["id"],
                    title=snip.get("title", ""),
                    description=snip.get("description", ""),
                    published_at=datetime.fromisoformat(snip["publishedAt"].replace("Z", "+00:00")),
                    duration_seconds=duration_seconds,
                    captions_available=False,  # set later via captions probe
                    playlist_ids=[],
                    thumbnail_url=snip.get("thumbnails", {}).get("high", {}).get("url"),
                    channel_id=snip.get("channelId"),
                    raw_json=it,
                    recording_location=recording_location,
                    localizations=localizations,
                    topics=topics,
                    tags=tags,
                )
            )
    return out


def _iso8601_duration_to_seconds(iso: str) -> int:
    # Minimal parser for ISO 8601 duration (P[n]Y[n]M[n]DT[n]H[n]M[n]S)
    import re

    m = re.match(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$", iso)
    if not m:
        return 0
    days = int(m.group("days") or 0)
    hours = int(m.group("hours") or 0)
    minutes = int(m.group("minutes") or 0)
    seconds = int(m.group("seconds") or 0)
    return seconds + minutes * 60 + hours * 3600 + days * 86400


def probe_captions_available(video_id: str) -> bool:
    """Quick probe using yt-dlp to see if any captions are available (any language)."""
    import subprocess
    try:
        args = [
            f"https://www.youtube.com/watch?v={video_id}",
            "--skip-download",
            "--list-subs",
            "-q",
        ]
        try:
            res = subprocess.run(["yt-dlp", *args], check=True, capture_output=True, text=True)
        except FileNotFoundError:
            res = subprocess.run([sys.executable, "-m", "yt_dlp", *args], check=True, capture_output=True, text=True)
        out = res.stdout or ""
        return "Available subtitles" in out or "auto captions" in out.lower()
    except Exception as e:
        logger.warning(f"Caption probe failed for {video_id}: {e}")
        return False


def list_captions(video_id: str) -> List[str]:
    """Return a list of available caption language codes using yt-dlp."""
    import subprocess, re
    langs: List[str] = []
    try:
        args = [
            f"https://www.youtube.com/watch?v={video_id}",
            "--skip-download",
            "--list-subs",
            "-q",
        ]
        try:
            res = subprocess.run(["yt-dlp", *args], check=True, capture_output=True, text=True)
        except FileNotFoundError:
            res = subprocess.run([sys.executable, "-m", "yt_dlp", *args], check=True, capture_output=True, text=True)
        for line in (res.stdout or "").splitlines():
            m = re.match(r"^([a-zA-Z0-9\-_.]+)\s*:\s*", line)
            if m:
                langs.append(m.group(1))
    except Exception:
        pass
    return langs


def download_captions(video_id: str, out_dir: str) -> Optional[str]:
    """Download English (including en-GB/en-US) auto/normal subtitles as VTT if available. Return file path or None."""
    import subprocess
    import os, glob
    import time
    import random
    os.makedirs(out_dir, exist_ok=True)

    # Random delay to avoid YouTube bot detection (looks more human-like)
    time.sleep(random.uniform(2.0, 5.0))

    try:
        # Use Android client - less likely to be bot-detected than web browser
        # No cookies needed - works in CI/CD and locally
        args = [
            f"https://www.youtube.com/watch?v={video_id}",
            "--extractor-args", "youtube:player_client=android",  # Use Android client (avoids bot detection)
            "--write-auto-sub",
            "--write-subs",
            "--sub-langs",
            "en,en.*,English",
            "--sub-format",
            "vtt",
            "--skip-download",
            "--no-warnings",  # Reduce noise
            "-o",
            os.path.join(out_dir, f"%(id)s.%(ext)s"),
        ]
        try:
            result = subprocess.run(["yt-dlp", *args], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            result = subprocess.run([sys.executable, "-m", "yt_dlp", *args], capture_output=True, text=True, timeout=30)

        # Check if yt-dlp actually succeeded (return code 0)
        if result.returncode != 0:
            # Log the actual error from yt-dlp
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            if error_msg and "No subtitles" not in error_msg:  # Don't log when captions simply don't exist
                logger.debug(f"yt-dlp returned {result.returncode} for {video_id}: {error_msg[:200]}")
            return None

        # Prefer en.vtt then any en-*.vtt then auto variants
        candidates = [
            os.path.join(out_dir, f"{video_id}.en.vtt"),
            *sorted(glob.glob(os.path.join(out_dir, f"{video_id}.en.*.vtt"))),
            os.path.join(out_dir, f"{video_id}.en.auto.vtt"),
            *sorted(glob.glob(os.path.join(out_dir, f"{video_id}.en.*.auto.vtt"))),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        # As a last resort, return any vtt for this video
        any_vtt = sorted(glob.glob(os.path.join(out_dir, f"{video_id}*.vtt")))
        if any_vtt:
            logger.debug(f"Found caption file: {os.path.basename(any_vtt[0])}")
            return any_vtt[0]
        else:
            logger.debug(f"No caption files found for {video_id} (captions may not exist)")
            return None
    except subprocess.TimeoutExpired:
        logger.warning(f"Caption download timed out for {video_id}")
        return None
    except Exception as e:
        logger.error(f"Caption download exception for {video_id}: {type(e).__name__}: {e}")
        return None
