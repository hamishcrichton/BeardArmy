#!/usr/bin/env python3
"""Test LLM-based extraction on sample videos."""
import sys
import os
from datetime import datetime

# Add ingestion to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))

from bmf_ingest.models import Video
from bmf_ingest.llm_extractor import extract_with_llm

# Sample videos from the actual channel
SAMPLE_VIDEOS = [
    {
        "video_id": "KPysiwgpWCk",
        "title": "I TRIED TO EAT THE BIGGEST PIZZA IN LAS VEGAS...SUPER MARIO'S 45\" PIZZA CHALLENGE! | BeardMeatsFood",
        "description": """Watch as I attempt to eat the biggest pizza in Las Vegas at Super Mario's Italian Restaurant! This massive 45-inch pizza challenge is one of the most epic food challenges I've ever attempted. Located in the heart of the Las Vegas Strip, Super Mario's is known for their huge portions and this pizza lives up to the hype.

The challenge rules are simple: finish the entire 45-inch pizza in under 2 hours to get your name on the wall of fame and win $500. Very few people have ever completed this monster pizza challenge.

Unfortunately, I couldn't finish this one - the sheer volume was just too much even for me! Came close though.

📍 Location: Super Mario's Italian Restaurant, Las Vegas, NV

Support the channel:
Patreon: https://www.patreon.com/beardmeatsfood""",
        "tags": ["food challenge", "pizza challenge", "las vegas", "competitive eating"],
    },
    {
        "video_id": "9J-dYr7j-3I",
        "title": "IN NORWAY YOU HAVE TO STAY SEATED FOR 15 MINUTES AFTER ATTEMPTING THIS CHALLENGE! | BeardMeatsFood",
        "description": """Today I'm in Oslo, Norway attempting one of the most unique food challenges I've ever tried. At Illegal Burger, you have to stay seated for 15 minutes after finishing to make sure the food stays down!

The burger is absolutely massive with multiple patties, cheese, bacon and all the toppings. Not many people have completed this challenge.

Update: I managed to finish the burger and stayed seated for the full 15 minutes - challenge completed! My name is on the wall!

📍 Location: Illegal Burger, Oslo, Norway""",
        "tags": ["food challenge", "burger challenge", "norway", "oslo"],
    },
    {
        "video_id": "wjPo5i1NdZs",
        "title": "I DEMOLISHED THE UNBEATEN MIXED GRILL IN WALES | THE MOUNT'S MIGHTY CHALLENGE | BeardMeatsFood",
        "description": """In Wales at The Mount pub for their famous Mighty Mixed Grill Challenge. This beast has never been beaten in the time limit!

The challenge includes: 3 steaks, 3 chicken breasts, 3 burgers, sausages, bacon, black pudding, 3 eggs, mushrooms, tomatoes, onion rings, chips and beans. You have 45 minutes to finish everything to win.

Result: I absolutely demolished it with 8 minutes to spare! First person ever to beat it in time! The staff couldn't believe it.

📍 The Mount, Merthyr Tydfil, Wales""",
        "tags": ["food challenge", "mixed grill", "wales", "uk"],
    },
]


def main():
    # Check for API key
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ Error: No API key found")
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable")
        print("\nExample:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print("  python3 test_llm_extraction.py")
        return 1

    print(f"Testing LLM extraction using {provider}")
    print("=" * 100)

    for i, sample in enumerate(SAMPLE_VIDEOS, 1):
        print(f"\n🎬 Video {i}: {sample['video_id']}")
        print(f"Title: {sample['title'][:80]}...")

        # Create Video object
        video = Video(
            video_id=sample["video_id"],
            title=sample["title"],
            description=sample["description"],
            published_at=datetime.now(),
            tags=sample["tags"],
        )

        # Extract with LLM
        try:
            result = extract_with_llm(video, provider=provider, api_key=api_key)

            print(f"\n✅ Extracted:")
            print(f"   Restaurant:  {result.get('restaurant', 'N/A')}")
            print(f"   City:        {result.get('city', 'N/A')}")
            print(f"   Country:     {result.get('country', 'N/A')}")
            print(f"   Result:      {result.get('result', 'N/A')}")
            print(f"   Food Type:   {result.get('food_type', 'N/A')}")
            print(f"   Confidence:  {result.get('confidence', 0.0):.2f}")
            print(f"\n   Challenge Scores (0-10):")
            print(f"   - Food Volume:    {result.get('food_volume_score', 0)}/10")
            print(f"   - Time Limit:     {result.get('time_limit_score', 0)}/10")
            print(f"   - Success Rate:   {result.get('success_rate_score', 0)}/10 (difficulty)")
            print(f"   - Spiciness:      {result.get('spiciness_score', 0)}/10")
            print(f"   - Food Diversity: {result.get('food_diversity_score', 0)}/10")
            print(f"   - Risk Level:     {result.get('risk_level_score', 0)}/10")
            print(f"\n   Reasoning:  {result.get('reasoning', 'N/A')[:150]}...")

        except Exception as e:
            print(f"\n❌ Extraction failed: {e}")

        print("-" * 100)

    print("\n✅ Test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
