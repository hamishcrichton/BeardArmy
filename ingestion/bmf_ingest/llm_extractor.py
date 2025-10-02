"""LLM-based metadata extraction for BeardMeatsFood videos."""
from __future__ import annotations

import json
import os
from typing import Dict, Optional, Any

from loguru import logger

from .models import Video

# Extraction prompt template
EXTRACTION_PROMPT = """You are extracting food challenge metadata from a BeardMeatsFood YouTube video.

Extract these fields from the video metadata:
1. **restaurant**: The name of the restaurant/venue (or null if not mentioned)
2. **city**: The city/location name (or null if not found)
3. **country**: The country code (US, UK, CA, NO, FI, etc.) or null
4. **result**: Did they complete the challenge? ("success", "failure", or "unknown")
5. **food_type**: The primary cuisine type (e.g., "burger", "pizza", "bbq", "breakfast", "mixed_grill", "sandwich", "wings", "noodles", "dessert", etc.)
6. **confidence**: Your confidence in this extraction (0.0 to 1.0)

Also provide challenge difficulty scores (0-10 scale for each):
7. **food_volume_score**: How much food? (0=snack, 5=large meal, 10=enormous multi-person portions)
8. **time_limit_score**: How strict is the time limit? (0=no limit, 5=moderate time, 10=very tight time constraint)
9. **success_rate_score**: Based on mentioned stats, how hard is it? (0=everyone wins, 5=50% success, 10=almost no one completes)
10. **spiciness_score**: How spicy? (0=not spicy, 5=medium heat, 10=extreme Carolina Reaper level)
11. **food_diversity_score**: Variety of foods? (0=single item, 5=few items, 10=huge variety of different foods)
12. **risk_level_score**: Stakes/consequences? (0=no risk, 5=moderate cost, 10=high cost if fail or huge prize if win)

Video Title:
{title}

Video Description (first 1000 chars):
{description}

Video Tags:
{tags}

{captions_section}

CRITICAL: If captions/transcript is provided, it is the ONLY reliable source for determining the result.
The transcript captures the actual moment of success/failure - titles and descriptions are often clickbait and don't reveal the outcome.

Success phrases to listen for:
- "I did it!", "I've done it!", "I beat it!", "I finished it!"
- "That's the challenge beaten", "Challenge complete"
- "My name goes on the wall", "I'm getting the t-shirt"
- "I got it done", "Absolutely smashed it", "Demolished it"

Failure phrases to listen for:
- "I can't do it", "I couldn't finish", "I'm done", "I'm tapping out"
- "That's beaten me", "I can't eat anymore", "I'm full"
- "Unfortunately I didn't make it", "Didn't quite get there"
- "Too much for me", "I've had to give up"

The ending of the transcript (last 100 words) is most important - that's where the result is revealed.
If no transcript is available, result should be "unknown" unless the title/description explicitly states the outcome.

Respond ONLY with valid JSON in this exact format:
{{
  "restaurant": "Restaurant Name" or null,
  "city": "City Name" or null,
  "country": "US" or null,
  "result": "success" or "failure" or "unknown",
  "food_type": "burger" or "pizza" etc,
  "confidence": 0.85,
  "food_volume_score": 8,
  "time_limit_score": 6,
  "success_rate_score": 9,
  "spiciness_score": 0,
  "food_diversity_score": 3,
  "risk_level_score": 7,
  "reasoning": "Brief explanation of extraction and scoring"
}}

Important notes for extraction:
- For US states (Kentucky, Texas, etc.), use country="US"
- For UK regions (Wales, Scotland, England), use country="UK"
- If restaurant name is unclear, use null rather than guessing
- Common patterns: "IN [LOCATION] FOR..." means the location is in LOCATION
- "AT [RESTAURANT]" or "at [Restaurant]" in description is usually the venue

Result inference (WITHOUT transcript):
- Only use title/description if they EXPLICITLY state the outcome
- result="success" if title contains: "DEMOLISHED", "COMPLETED", "BEAT", "WON", "SUCCESS"
- result="failure" if title contains: "FAILED", "COULDN'T FINISH", "DNF", "DEFEATED"
- result="unknown" for ambiguous titles like "I TRIED", "ATTEMPTING", "CHALLENGE" (very common)
- DO NOT assume "TRIED TO" means failure - BeardMeatsFood uses this for both outcomes

Scoring guidelines:
- food_volume: Look for phrases like "massive", "giant", "10lb", "45 inch", "family-sized"
- time_limit: Look for minutes mentioned, "fast enough", "speed challenge"
- success_rate: Look for "unbeaten", "only X people have completed", "failed Y times"
- spiciness: Look for "Carolina Reaper", "ghost pepper", "scoville", "spicy"
- food_diversity: Single food=low score, platters/mixed grills=high score
- risk_level: Look for prize money, "free for a month", "eat free if you win", expensive cost
"""


class LLMExtractor:
    """Extract video metadata using an LLM."""

    def __init__(self, provider: str = "anthropic", api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM extractor.

        Args:
            provider: "anthropic" or "openai"
            api_key: API key (or uses env var)
            model: Model name (defaults to haiku for anthropic, gpt-4o-mini for openai)
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key()

        if self.provider == "anthropic":
            self.model = model or "claude-3-haiku-20240307"
            self._init_anthropic()
        elif self.provider == "openai":
            self.model = model or "gpt-4o-mini"
            self._init_openai()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        if self.provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            return key
        elif self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            return key

    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def extract(
        self,
        video: Video,
        captions_text: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Extract metadata from video using LLM.

        Args:
            video: Video object with title, description, tags
            captions_text: Optional caption text (first few minutes)
            max_retries: Number of retries on failure

        Returns:
            Dict with extracted fields: restaurant, city, country, result, confidence, reasoning
        """
        # Prepare context
        captions_section = ""
        if captions_text:
            # Use first 1000 words from captions (captures intro + ending where result is revealed)
            words = captions_text.split()[:1000]
            captions_section = f"\nVideo Transcript (first ~6-7 minutes, includes ending):\n{' '.join(words)}\n"
        else:
            captions_section = "\nVideo Transcript: Not available\n"

        prompt = EXTRACTION_PROMPT.format(
            title=video.title,
            description=video.description[:1000] if video.description else "Not available",
            tags=", ".join(video.tags) if video.tags else "None",
            captions_section=captions_section,
        )

        # Call LLM with retries
        for attempt in range(max_retries + 1):
            try:
                if self.provider == "anthropic":
                    result = self._call_anthropic(prompt)
                else:
                    result = self._call_openai(prompt)

                # Validate response
                if self._validate_response(result):
                    logger.info(f"LLM extracted for {video.video_id}: {result}")
                    return result
                else:
                    logger.warning(f"Invalid LLM response for {video.video_id}, attempt {attempt + 1}")

            except Exception as e:
                logger.warning(f"LLM extraction failed for {video.video_id}, attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    # Return empty result on final failure
                    return {
                        "restaurant": None,
                        "city": None,
                        "country": None,
                        "result": "unknown",
                        "food_type": None,
                        "confidence": 0.0,
                        "food_volume_score": 0,
                        "time_limit_score": 0,
                        "success_rate_score": 0,
                        "spiciness_score": 0,
                        "food_diversity_score": 0,
                        "risk_level_score": 0,
                        "reasoning": f"LLM extraction failed: {e}",
                    }

        return {
            "restaurant": None,
            "city": None,
            "country": None,
            "result": "unknown",
            "food_type": None,
            "confidence": 0.0,
            "food_volume_score": 0,
            "time_limit_score": 0,
            "success_rate_score": 0,
            "spiciness_score": 0,
            "food_diversity_score": 0,
            "risk_level_score": 0,
            "reasoning": "LLM extraction failed after retries",
        }

    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            temperature=0.0,  # Deterministic
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content
        text = response.content[0].text

        # Parse JSON from response
        # Handle cases where LLM wraps in markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600,
            response_format={"type": "json_object"},  # Force JSON mode
        )

        text = response.choices[0].message.content
        return json.loads(text.strip())

    def _validate_response(self, result: Dict[str, Any]) -> bool:
        """Validate LLM response has required fields."""
        required = {
            "restaurant", "city", "country", "result", "food_type", "confidence",
            "food_volume_score", "time_limit_score", "success_rate_score",
            "spiciness_score", "food_diversity_score", "risk_level_score"
        }
        return all(k in result for k in required)


def extract_with_llm(
    video: Video,
    captions_text: Optional[str] = None,
    provider: str = "anthropic",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function for LLM extraction.

    Args:
        video: Video to extract from
        captions_text: Optional caption text
        provider: "anthropic" or "openai"
        api_key: API key (or uses env var)

    Returns:
        Extracted metadata dict
    """
    extractor = LLMExtractor(provider=provider, api_key=api_key)
    return extractor.extract(video, captions_text=captions_text)
