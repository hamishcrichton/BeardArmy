#!/usr/bin/env python3
"""Standalone test of improved extractor functions."""
import sys
import os

# Add the ingestion directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))

# Import the extractor functions
from bmf_ingest.extractors import _find_city_country, _find_restaurant_name

# Real video titles from the channel
TEST_CASES = [
    {
        "title": "I TRIED TO EAT THE BIGGEST PIZZA IN LAS VEGAS...SUPER MARIO'S 45\" PIZZA CHALLENGE! | BeardMeatsFood",
        "expected_city": "Las Vegas",
        "expected_country": "US",
    },
    {
        "title": "EAT FREE FOR A MONTH IF YOU CAN BEAT THIS GIANT BURGER CHALLENGE IN AUSTRIA! | BeardMeatsFood",
        "expected_city": "Austria",
        "expected_country": "AT",
    },
    {
        "title": "THIS BBQ SANDWICH CHALLENGE IN SOUTH CAROLINA HAS BEEN FAILED 76 TIMES! | BeardMeatsFood",
        "expected_city": "South Carolina",
        "expected_country": "US",
    },
    {
        "title": "IN NORWAY YOU HAVE TO STAY SEATED FOR 15 MINUTES AFTER ATTEMPTING THIS CHALLENGE! | BeardMeatsFood",
        "expected_city": "Norway",
        "expected_country": "NO",
    },
    {
        "title": "IN KENTUCKY FOR A CHALLENGE OVER 200 PEOPLE HAVE FAILED! | BeardMeatsFood",
        "expected_city": "Kentucky",
        "expected_country": "US",
    },
    {
        "title": "IN WALES FOR A MIXED GRILL THAT'S NEVER BEEN BEATEN | THE MOUNT'S MIGHTY CHALLENGE | BeardMeatsFood",
        "expected_city": "Wales",
        "expected_country": "UK",
    },
    {
        "title": "IN DALLAS FOR THE WACKIEST CHALLENGE I'VE DONE IN A WHILE | BeardMeatsFood",
        "expected_city": "Dallas",
        "expected_country": "US",
    },
]


def main():
    print("Testing improved extractor functions:")
    print("=" * 100)

    passed = 0
    failed = 0

    for i, test in enumerate(TEST_CASES, 1):
        title = test["title"]
        expected_city = test.get("expected_city")
        expected_country = test.get("expected_country")

        city, country = _find_city_country(title)

        status = "✓" if (city == expected_city and country == expected_country) else "✗"
        if status == "✓":
            passed += 1
        else:
            failed += 1

        print(f"\n{status} Test {i}:")
        print(f"  Title: {title[:80]}...")
        print(f"  Expected: City={expected_city}, Country={expected_country}")
        print(f"  Got:      City={city}, Country={country}")

    print("\n" + "=" * 100)
    print(f"\nResults: {passed}/{len(TEST_CASES)} tests passed")

    if failed > 0:
        print(f"⚠️  {failed} tests failed")
        return 1
    else:
        print("✓ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
