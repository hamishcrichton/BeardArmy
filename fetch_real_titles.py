#!/usr/bin/env python3
"""Fetch real video titles from BeardMeatsFood channel to understand patterns."""
import json
import os
import sys

# Check for API key
api_key = os.getenv("YOUTUBE_API_KEY")
if not api_key:
    print("ERROR: YOUTUBE_API_KEY environment variable not set")
    print("Please run: export YOUTUBE_API_KEY='your_key_here'")
    sys.exit(1)

try:
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: google-api-python-client not installed")
    print("Please run: python3 -m pip install --user google-api-python-client")
    sys.exit(1)

CHANNEL_ID = "UCc9CjaAjsMMvaSghZB7-Kog"  # BeardMeatsFood

def fetch_recent_titles(api_key: str, channel_id: str, max_results: int = 20):
    """Fetch recent video titles from a channel."""
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    # Get uploads playlist
    resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_id = resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get recent videos
    resp = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=uploads_id,
        maxResults=max_results
    ).execute()

    video_ids = [item["contentDetails"]["videoId"] for item in resp["items"]]

    # Fetch video details
    resp = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids)
    ).execute()

    videos = []
    for item in resp["items"]:
        videos.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"][:200],  # First 200 chars
        })

    return videos


def main():
    print(f"Fetching recent video titles from BeardMeatsFood...\n")

    videos = fetch_recent_titles(api_key, CHANNEL_ID, max_results=25)

    print(f"Found {len(videos)} videos:\n")
    print("=" * 120)

    for i, v in enumerate(videos, 1):
        print(f"{i}. [{v['video_id']}]")
        print(f"   Title: {v['title']}")
        print(f"   Desc:  {v['description'][:100]}...")
        print("-" * 120)

    # Save to file
    output_file = "data/real_titles.json"
    os.makedirs("data", exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(videos, f, indent=2)

    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()
