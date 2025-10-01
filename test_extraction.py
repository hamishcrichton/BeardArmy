#!/usr/bin/env python3
"""Quick test of extraction logic on sample video titles."""
from datetime import datetime
from dataclasses import dataclass

# Sample video data from the actual output
SAMPLE_VIDEOS = [
    {
        "video_id": "KPysiwgpWCk",
        "title": "I TRIED TO EAT THE BIGGEST PIZZA IN LAS VEGAS...SUPER MARIO'S 45\" PIZZA CHALLENGE! | BeardMeatsFood",
        "description": "Sample description mentioning Las Vegas",
    },
    {
        "video_id": "N60Q0n26KFI",
        "title": "WIN THE CASH JACKPOT IF YOU FINISH THIS UNBEATEN BREAKFAST CHALLENGE FAST ENOUGH! | BeardMeatsFood",
        "description": "Sample description",
    },
    {
        "video_id": "test1",
        "title": "MASSIVE 10LB BURGER CHALLENGE at Big Bob's Diner | Manchester, UK | BeardMeatsFood",
        "description": "Taking on the massive burger at Big Bob's Diner in Manchester",
    },
    {
        "video_id": "test2",
        "title": "5KG PIZZA CHALLENGE | Pizza Palace, Rome, Italy | BeardMeatsFood",
        "description": "Epic pizza challenge at Pizza Palace in the heart of Rome",
    },
]


@dataclass
class Video:
    video_id: str
    title: str
    description: str
    published_at: datetime
    tags: list = None
    localizations: dict = None


def extract_restaurant_from_title(title: str) -> tuple:
    """Extract restaurant name and location from pipe-delimited titles."""
    import re

    # Remove BeardMeatsFood suffix
    title = re.sub(r'\s*\|\s*BeardMeatsFood\s*$', '', title, flags=re.I)

    # Split by pipes
    parts = [p.strip() for p in title.split('|')]

    restaurant = None
    city = None
    country = None

    if len(parts) >= 2:
        # Check if second part looks like location (City, Country format)
        location_part = parts[1]

        # Pattern: "City, Country" or "City, State"
        loc_match = re.match(r'^([^,]+)(?:,\s*(.+))?$', location_part)
        if loc_match:
            potential_city = loc_match.group(1).strip()
            potential_region = (loc_match.group(2) or "").strip() if loc_match.group(2) else None

            # If it looks like a location, first part is restaurant
            if potential_region or len(potential_city.split()) <= 3:
                restaurant = parts[0].strip()
                city = potential_city

                # Map common country names
                if potential_region:
                    country_map = {
                        "UK": "UK", "United Kingdom": "UK", "England": "UK",
                        "USA": "US", "United States": "US", "America": "US",
                        "Italy": "IT", "Germany": "DE", "France": "FR",
                    }
                    country = country_map.get(potential_region, potential_region)

    # Look for "at RESTAURANT" or "at RESTAURANT in CITY" patterns
    if not restaurant:
        at_match = re.search(r'\bat\s+([^|]+?)(?:\s+in\s+([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*))?(?=\s*\||\s*$)', title, re.I)
        if at_match:
            restaurant = at_match.group(1).strip()
            if at_match.group(2):
                city = at_match.group(2).strip()

    # Clean up restaurant name
    if restaurant:
        restaurant = re.sub(r"^(The|A)\s+", "", restaurant, flags=re.I)
        restaurant = re.sub(r'\s+(Challenge|Restaurant|Diner|Cafe)$', '', restaurant, flags=re.I)
        restaurant = restaurant.strip("'\"")

    return restaurant, city, country


def main():
    print("Testing extraction on sample videos:\n")
    print("=" * 80)

    for video_data in SAMPLE_VIDEOS:
        print(f"\nVideo ID: {video_data['video_id']}")
        print(f"Title: {video_data['title']}")

        restaurant, city, country = extract_restaurant_from_title(video_data['title'])

        print(f"  → Restaurant: {restaurant or 'NOT FOUND'}")
        print(f"  → City: {city or 'NOT FOUND'}")
        print(f"  → Country: {country or 'NOT FOUND'}")
        print("-" * 80)

    print("\nDiagnosis:")
    print("1. Many BMF video titles use pipe-delimited format: Challenge | Location | Brand")
    print("2. Current extractor may not be parsing this format correctly")
    print("3. Need to improve pattern matching for 'at RESTAURANT' and location extraction")


if __name__ == "__main__":
    main()
