"""Parse VTT/SRT caption files for video transcripts."""
from __future__ import annotations

import os
import re
from typing import Optional

from loguru import logger


def parse_vtt_intro(vtt_path: str, max_duration_seconds: int = 180, max_words: int = 500) -> Optional[str]:
    """
    Parse VTT caption file and extract intro (first N seconds or M words).

    Args:
        vtt_path: Path to VTT file
        max_duration_seconds: Maximum duration to extract (default 180 = 3 minutes)
        max_words: Maximum number of words to extract

    Returns:
        Transcript text or None if parsing fails
    """
    if not os.path.exists(vtt_path):
        return None

    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # VTT format:
        # WEBVTT
        #
        # 00:00:01.000 --> 00:00:04.000
        # Caption text here
        #
        # 00:00:04.000 --> 00:00:07.000
        # More caption text

        lines = content.split('\n')
        transcript_parts = []
        current_time = 0.0
        word_count = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp line (e.g., "00:00:01.000 --> 00:00:04.000")
            if '-->' in line:
                # Extract start time
                match = re.match(r'(\d{2}):(\d{2}):(\d{2})\.?\d*\s*-->', line)
                if match:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    current_time = hours * 3600 + minutes * 60 + seconds

                    # Stop if we've exceeded max duration
                    if current_time > max_duration_seconds:
                        break

                    # Next line(s) should be caption text
                    i += 1
                    while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                        caption_text = lines[i].strip()

                        # Clean up caption text
                        caption_text = _clean_caption_text(caption_text)

                        if caption_text:
                            transcript_parts.append(caption_text)
                            word_count += len(caption_text.split())

                            # Stop if we've hit word limit
                            if word_count >= max_words:
                                break

                        i += 1

                    if word_count >= max_words:
                        break

            i += 1

        if transcript_parts:
            transcript = ' '.join(transcript_parts)
            logger.debug(f"Extracted {len(transcript_parts)} caption segments, {word_count} words from {vtt_path}")
            return transcript

        return None

    except Exception as e:
        logger.warning(f"Failed to parse VTT file {vtt_path}: {e}")
        return None


def _clean_caption_text(text: str) -> str:
    """Clean caption text by removing formatting tags and artifacts."""
    # Remove VTT formatting tags like <c>, </c>, <i>, </i>
    text = re.sub(r'<[^>]+>', '', text)

    # Remove speaker labels like "[Music]", "[Applause]"
    text = re.sub(r'\[.*?\]', '', text)

    # Remove music notes ♪
    text = re.sub(r'[♪♫]', '', text)

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_srt_intro(srt_path: str, max_duration_seconds: int = 180, max_words: int = 500) -> Optional[str]:
    """
    Parse SRT caption file and extract intro.

    SRT format:
    1
    00:00:01,000 --> 00:00:04,000
    Caption text here

    2
    00:00:04,000 --> 00:00:07,000
    More caption text
    """
    if not os.path.exists(srt_path):
        return None

    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        transcript_parts = []
        current_time = 0.0
        word_count = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp line
            if '-->' in line:
                # Extract start time (format: 00:00:01,000)
                match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,\.]?\d*\s*-->', line)
                if match:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    current_time = hours * 3600 + minutes * 60 + seconds

                    if current_time > max_duration_seconds:
                        break

                    # Next line(s) should be caption text
                    i += 1
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                        caption_text = lines[i].strip()
                        caption_text = _clean_caption_text(caption_text)

                        if caption_text:
                            transcript_parts.append(caption_text)
                            word_count += len(caption_text.split())

                            if word_count >= max_words:
                                break

                        i += 1

                    if word_count >= max_words:
                        break

            i += 1

        if transcript_parts:
            transcript = ' '.join(transcript_parts)
            logger.debug(f"Extracted {len(transcript_parts)} caption segments, {word_count} words from {srt_path}")
            return transcript

        return None

    except Exception as e:
        logger.warning(f"Failed to parse SRT file {srt_path}: {e}")
        return None


def extract_caption_intro(caption_path: str, max_duration_seconds: int = 180, max_words: int = 500) -> Optional[str]:
    """
    Extract intro from caption file (auto-detects VTT or SRT format).

    Args:
        caption_path: Path to caption file (.vtt or .srt)
        max_duration_seconds: Maximum duration to extract (default 3 minutes)
        max_words: Maximum words to extract (default 500)

    Returns:
        Transcript text or None
    """
    if not caption_path or not os.path.exists(caption_path):
        return None

    # Auto-detect format
    if caption_path.endswith('.vtt'):
        return parse_vtt_intro(caption_path, max_duration_seconds, max_words)
    elif caption_path.endswith('.srt'):
        return parse_srt_intro(caption_path, max_duration_seconds, max_words)
    else:
        # Try VTT first, then SRT
        result = parse_vtt_intro(caption_path, max_duration_seconds, max_words)
        if result:
            return result
        return parse_srt_intro(caption_path, max_duration_seconds, max_words)
