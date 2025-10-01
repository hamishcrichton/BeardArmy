#!/usr/bin/env python3
"""Test improved extraction logic on real BMF video title patterns."""
import re
from typing import Optional, Tuple

# Real video titles from the channel
REAL_TITLES = [
    "I TRIED TO EAT THE BIGGEST PIZZA IN LAS VEGAS...SUPER MARIO'S 45\" PIZZA CHALLENGE! | BeardMeatsFood",
    "WIN THE CASH JACKPOT IF YOU FINISH THIS UNBEATEN BREAKFAST CHALLENGE FAST ENOUGH! | BeardMeatsFood",
    "EAT FREE FOR A MONTH IF YOU CAN BEAT THIS GIANT BURGER CHALLENGE IN AUSTRIA! | BeardMeatsFood",
    "THIS BBQ SANDWICH CHALLENGE IN SOUTH CAROLINA HAS BEEN FAILED 76 TIMES! | BeardMeatsFood",
    "IN NORWAY YOU HAVE TO STAY SEATED FOR 15 MINUTES AFTER ATTEMPTING THIS CHALLENGE! | BeardMeatsFood",
    "THIS €140 BARBECUE CHALLENGE IN FINLAND HAS ONLY BEEN BEATEN ONCE! | BeardMeatsFood",
    "IN KENTUCKY FOR A CHALLENGE OVER 200 PEOPLE HAVE FAILED! | BeardMeatsFood",
    "IN WALES FOR A MIXED GRILL THAT'S NEVER BEEN BEATEN | THE MOUNT'S MIGHTY CHALLENGE | BeardMeatsFood",
    "IN DALLAS FOR THE WACKIEST CHALLENGE I'VE DONE IN A WHILE | BeardMeatsFood",
    "THE WALL OF FAME HERE HAS BEEN EMPTY FOR MONTHS | THE 'AMERICAN TOON' CHALLENGE | BeardMeatsFood",
]


def extract_location_improved(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract city and country from text.

    Patterns to handle:
    - "IN [CITY/STATE/COUNTRY] FOR..."
    - "... IN [LOCATION] ..."
    - "... AT [RESTAURANT] IN [LOCATION]"
    """
    city = None
    country = None

    # Pattern 1: "IN LOCATION FOR..." at start of title
    match = re.search(r'\bIN\s+([A-Z][A-Za-z\s]+?)\s+FOR\s+', text, re.I)
    if match:
        location = match.group(1).strip()
        city, country = _parse_location_string(location)
        return city, country

    # Pattern 2: "IN LOCATION" anywhere in title
    match = re.search(r'\bIN\s+([A-Z][A-Za-z\s]+?)(?:\s*[|!]|\s+(?:HAS|FOR|YOU|TO|IS|HAVE|I\'VE)\b)', text, re.I)
    if match:
        location = match.group(1).strip()
        city, country = _parse_location_string(location)
        return city, country

    # Pattern 3: Explicit country/state mentions
    locations = {
        # Countries
        'AUSTRIA': ('Austria', 'AT'),
        'NORWAY': ('Norway', 'NO'),
        'FINLAND': ('Finland', 'FI'),
        'WALES': ('Wales', 'UK'),
        'SCOTLAND': ('Scotland', 'UK'),
        'ENGLAND': ('England', 'UK'),
        'IRELAND': ('Ireland', 'IE'),
        'GERMANY': ('Germany', 'DE'),
        'FRANCE': ('France', 'FR'),
        'ITALY': ('Italy', 'IT'),
        # US States
        'LAS VEGAS': ('Las Vegas', 'US'),
        'PENNSYLVANIA': ('Pennsylvania', 'US'),
        'SOUTH CAROLINA': ('South Carolina', 'US'),
        'KENTUCKY': ('Kentucky', 'US'),
        'DALLAS': ('Dallas', 'US'),
        'TEXAS': ('Texas', 'US'),
    }

    for keyword, (loc_city, loc_country) in locations.items():
        if re.search(rf'\b{re.escape(keyword)}\b', text, re.I):
            return loc_city, loc_country

    return None, None


def _parse_location_string(location: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a location string like 'Las Vegas', 'South Carolina', 'Norway', etc."""
    location = location.strip()

    # Map known locations to country codes
    country_map = {
        'NORWAY': 'NO',
        'FINLAND': 'FI',
        'AUSTRIA': 'AT',
        'WALES': 'UK',
        'SCOTLAND': 'UK',
        'ENGLAND': 'UK',
        'DALLAS': 'US',
        'KENTUCKY': 'US',
        'SOUTH CAROLINA': 'US',
        'PENNSYLVANIA': 'US',
        'LAS VEGAS': 'US',
    }

    upper_loc = location.upper()
    if upper_loc in country_map:
        # It's a known location
        return location, country_map[upper_loc]

    return location, None


def extract_restaurant_improved(text: str) -> Optional[str]:
    """
    Extract restaurant name from text.

    Patterns to handle:
    - "... AT [RESTAURANT NAME] IN [LOCATION]"
    - "... AT [RESTAURANT NAME] ..."
    - "THE [NAME] CHALLENGE" when it refers to a restaurant
    - Explicit restaurant names before pipe delimiter
    """
    # Remove BeardMeatsFood suffix
    text = re.sub(r'\s*\|\s*BeardMeatsFood\s*$', '', text, flags=re.I)

    # Pattern 1: "... at RESTAURANT NAME in LOCATION"
    match = re.search(r'\bat\s+([A-Z][A-Za-z\'\s&]+?)\s+in\s+[A-Z]', text, re.I)
    if match:
        restaurant = match.group(1).strip()
        restaurant = _clean_restaurant_name(restaurant)
        if _is_valid_restaurant_name(restaurant):
            return restaurant

    # Pattern 2: "THE [NAME] CHALLENGE" where NAME might be a restaurant
    # This is tricky - often it's just a descriptive challenge name
    # Only extract if it's very specific (e.g., "THE MOUNT'S MIGHTY CHALLENGE")
    match = re.search(r'\bTHE\s+([A-Z][A-Za-z\'\s]+?)(?:\'S)?\s+(?:MIGHTY\s+)?CHALLENGE\b', text, re.I)
    if match:
        name = match.group(1).strip()
        # Only use if it looks like a proper name (not generic words)
        if _looks_like_proper_name(name):
            return name

    # Pattern 3: Restaurant name mentioned with possessive
    # e.g., "DILLINGER'S GAUNTLET CHALLENGE"
    match = re.search(r'\b([A-Z][A-Za-z]+\'S)\s+', text)
    if match:
        name = match.group(1).replace("'S", "").strip()
        if len(name) >= 4:  # Minimum length for a restaurant name
            return name

    # Pattern 4: Explicit restaurant name after "at"
    match = re.search(r'\bat\s+([A-Z][A-Za-z\'\s&-]+?)(?:\s*[|!]|\s+(?:in|has|for|is)\b)', text, re.I)
    if match:
        restaurant = match.group(1).strip()
        restaurant = _clean_restaurant_name(restaurant)
        if _is_valid_restaurant_name(restaurant):
            return restaurant

    return None


def _clean_restaurant_name(name: str) -> str:
    """Clean up extracted restaurant name."""
    name = name.strip()
    # Remove trailing common words
    name = re.sub(r'\s+(Challenge|Restaurant|Diner|Cafe|Bar|Pub|Grill)$', '', name, flags=re.I)
    # Remove leading articles
    name = re.sub(r'^(The|A)\s+', '', name, flags=re.I)
    return name.strip()


def _is_valid_restaurant_name(name: str) -> bool:
    """Check if extracted name looks like a valid restaurant name."""
    if not name or len(name) < 3:
        return False
    words = name.split()
    if len(words) > 10:  # Too long
        return False
    # Reject if it's all common words
    common_words = {'challenge', 'breakfast', 'lunch', 'dinner', 'burger', 'pizza', 'sandwich'}
    if all(w.lower() in common_words for w in words):
        return False
    return True


def _looks_like_proper_name(name: str) -> bool:
    """Check if a name looks like a proper name (not generic description)."""
    name_lower = name.lower()
    # Reject generic words
    generic = {'mighty', 'giant', 'massive', 'huge', 'big', 'great', 'super'}
    if name_lower in generic:
        return False
    # Accept if it's a specific name
    if len(name.split()) <= 3 and any(c.isupper() for c in name[1:]):
        return True
    return False


def main():
    print("Testing IMPROVED extraction on real BMF video titles:\n")
    print("=" * 120)

    for title in REAL_TITLES:
        print(f"\nTitle: {title[:90]}...")

        city, country = extract_location_improved(title)
        restaurant = extract_restaurant_improved(title)

        print(f"  → Restaurant: {restaurant or 'NOT FOUND'}")
        print(f"  → City: {city or 'NOT FOUND'}")
        print(f"  → Country: {country or 'NOT FOUND'}")
        print("-" * 120)

    print("\n" + "=" * 120)
    print("\nKEY INSIGHTS:")
    print("1. Most BMF titles use pattern: [DESCRIPTION] IN [LOCATION] FOR [MORE_DESCRIPTION]")
    print("2. Locations mentioned: Las Vegas, South Carolina, Norway, Finland, Kentucky, Wales, Dallas, Austria")
    print("3. Restaurant names are rare in titles - usually just location + challenge description")
    print("4. Need to extract from VIDEO DESCRIPTION for restaurant names!")
    print("5. Consider using YouTube's 'recordingDetails' API field for coordinates")


if __name__ == "__main__":
    main()
