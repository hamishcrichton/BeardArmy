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
        resp = youtube.videos().list(part="snippet,contentDetails", id=",".join(batch)).execute()
        for it in resp.get("items", []):
            snip = it["snippet"]
            content = it.get("contentDetails", {})
            duration_iso = content.get("duration")  # e.g., PT23M10S
            duration_seconds = _iso8601_duration_to_seconds(duration_iso) if duration_iso else None
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
    """Quick probe using yt-dlp to see if captions are available."""
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
        return "Available subtitles" in res.stdout
    except Exception as e:
        logger.warning(f"Caption probe failed for {video_id}: {e}")
        return False


def download_captions(video_id: str, out_dir: str) -> Optional[str]:
    """Download English auto/normal subtitles as VTT if available. Return file path or None."""
    import subprocess
    import os
    os.makedirs(out_dir, exist_ok=True)
    try:
        args = [
            f"https://www.youtube.com/watch?v={video_id}",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang",
            "en",
            "--sub-format",
            "vtt",
            "--skip-download",
            "-o",
            os.path.join(out_dir, f"%(id)s.%(ext)s"),
        ]
        try:
            subprocess.run(["yt-dlp", *args], check=True, capture_output=True, text=True)
        except FileNotFoundError:
            subprocess.run([sys.executable, "-m", "yt_dlp", *args], check=True, capture_output=True, text=True)
        vtt_path = os.path.join(out_dir, f"{video_id}.en.vtt")
        if os.path.exists(vtt_path):
            return vtt_path
        # Fallback auto-captions naming
        auto_vtt = os.path.join(out_dir, f"{video_id}.en.auto.vtt")
        return auto_vtt if os.path.exists(auto_vtt) else None
    except Exception as e:
        logger.warning(f"Caption download failed for {video_id}: {e}")
        return None
