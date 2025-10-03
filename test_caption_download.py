"""Test harness for caption downloads - NO API costs, local testing only."""
import os
import sys

# Add ingestion to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))

from bmf_ingest.youtube_client import download_captions

# Test with 5 known BeardMeatsFood videos
test_videos = [
    ("JGb3RHBxfuw", "I TRIED A BREAKFAST CHALLENGE..."),
    ("PH-G-qRjpUc", "I ORDERED A CHICKEN DIPPER CHALLENGE..."),
    ("SJQloccusZI", "ATTEMPTING THE 'BOMB BURRITO' CHALLENGE..."),
    ("Iu32WpkTg9I", "THIS SPICY CURRY BANQUET CHALLENGE..."),
    ("9L1Z9vrXc20", "I FLEW TO ICELAND FOR A FOOD CHALLENGE..."),
]

print("=" * 70)
print("CAPTION DOWNLOAD TEST HARNESS")
print("Testing 5 videos - NO LLM API calls, $0 cost")
print("=" * 70)
print()

os.makedirs("test_captions", exist_ok=True)

success_count = 0
failed_count = 0

for video_id, title in test_videos:
    print(f"Testing {video_id}: {title[:50]}...")

    try:
        result = download_captions(video_id, "test_captions")

        if result and os.path.exists(result):
            size = os.path.getsize(result)
            print(f"  ✓ SUCCESS: {os.path.basename(result)}")
            print(f"    File size: {size:,} bytes")

            # Show first few lines to verify it's valid VTT
            with open(result, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:5]
                print(f"    First line: {lines[0].strip()}")

            success_count += 1
        else:
            print(f"  ✗ FAILED: No VTT file created")
            failed_count += 1

    except Exception as e:
        print(f"  ✗ EXCEPTION: {type(e).__name__}: {e}")
        failed_count += 1

    print()

print("=" * 70)
print(f"RESULTS: {success_count}/5 successful, {failed_count}/5 failed")
if success_count == 5:
    print("✓ ALL TESTS PASSED - Ready to deploy to GitHub Actions!")
elif success_count > 0:
    print(f"⚠ PARTIAL SUCCESS - {success_count} worked, investigate failures")
else:
    print("✗ ALL TESTS FAILED - Do not deploy, needs more debugging")
print("=" * 70)
