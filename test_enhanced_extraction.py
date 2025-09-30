#!/usr/bin/env python3
"""
Test script to verify enhanced YouTube API extraction.
Tests a few sample BeardMeatsFood videos to see if we get better data.
"""

import os
import sys
from datetime import datetime
from pprint import pprint

# Add the ingestion module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))

from bmf_ingest.config import Settings
from bmf_ingest.youtube_client import fetch_videos
from bmf_ingest.extractors import extract_from_video
from bmf_ingest.featured_places import get_featured_place
from loguru import logger

# Sample video IDs from BeardMeatsFood channel
TEST_VIDEO_IDS = [
    "video_id_1",  # Replace with actual BMF video IDs
    "video_id_2",
    "video_id_3",
]

def test_enhanced_extraction():
    """Test the enhanced extraction with sample videos."""
    
    # Load settings
    settings = Settings.load()
    
    if not settings.youtube_api_key:
        print("ERROR: No YouTube API key found. Please set YOUTUBE_API_KEY in .env")
        return
    
    print("=" * 80)
    print("TESTING ENHANCED YOUTUBE API EXTRACTION")
    print("=" * 80)
    
    # Get some recent video IDs from the channel
    print(f"\nFetching recent videos from channel: {settings.youtube_channel_id}")
    
    # For testing, let's use the list_videos function to get a few recent ones
    from bmf_ingest.youtube_client import list_videos
    video_ids = []
    for vid_id in list_videos(settings.youtube_api_key, settings.youtube_channel_id):
        video_ids.append(vid_id)
        if len(video_ids) >= 3:  # Test with 3 videos
            break
    
    if not video_ids:
        print("ERROR: Could not fetch any videos from channel")
        return
    
    print(f"Testing with video IDs: {video_ids}")
    
    # Fetch videos with enhanced metadata
    videos = fetch_videos(settings.youtube_api_key, video_ids)
    
    for i, video in enumerate(videos, 1):
        print(f"\n{'=' * 80}")
        print(f"VIDEO {i}: {video.video_id}")
        print(f"{'=' * 80}")
        print(f"Title: {video.title}")
        print(f"Published: {video.published_at}")
        
        # Check enhanced metadata
        print(f"\n--- Enhanced Metadata ---")
        print(f"Tags: {video.tags[:5] if video.tags else 'None'}")
        print(f"Recording Location: {video.recording_location}")
        print(f"Topics: {video.topics}")
        print(f"Localizations available: {list(video.localizations.keys()) if video.localizations else 'None'}")
        
        # Extract information
        extracted = extract_from_video(video)
        print(f"\n--- Extracted Data ---")
        print(f"Restaurant: {extracted.restaurant_name}")
        print(f"City: {extracted.city}")
        print(f"Country: {extracted.country}")
        print(f"Date: {extracted.date_attempted}")
        print(f"Result: {extracted.result}")
        print(f"Challenge Type: {extracted.challenge_type_slug}")
        print(f"Confidence: {extracted.confidence:.2f}")
        
        # Try to get featured place
        print(f"\n--- Featured Place Check ---")
        try:
            featured = get_featured_place(video.video_id)
            if featured:
                name, lat, lng = featured
                print(f"Featured Place: {name}")
                print(f"Coordinates: ({lat}, {lng})")
            else:
                print("No featured place found")
        except Exception as e:
            print(f"Error checking featured place: {e}")
        
        print()

if __name__ == "__main__":
    test_enhanced_extraction()