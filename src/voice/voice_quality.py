"""
Voice Quality Upgrade — 10/10 Voice Pipeline
=============================================
Problem Solved:
  Current (8/10):
  - Same TTS voice/rate for ALL intents (emergency vs FAQ = same speed)
  - Sentence boundary: regex split on [.!?] breaks on "Dr. Sharma", "Rs. 500"
  - No confidence filtering → low-confidence STT noise goes to LLM
  - Audio preprocessing: raw mic audio sent directly (background noise)

  Solution (10/10):
  1. Intent-aware TTS prosody via SSML
     - Emergency: faster rate (+10%), louder, urgent tone
     - Booking/Info: normal rate, warm, calm
     - Farewell: slightly slower, warm close
  2. Smart sentence boundary detector
     - Handles "Dr.", "Mr.", "Rs.", "etc.", "approx." (doesn't split on these)
  3. STT confidence filter
     - Ignores transcripts with confidence < 0.70 (prevents noise from reaching LLM)
  4. Filler word suppression
     - Removes "um", "uh", "hmm" from transcripts before processing
  5. Voice activity dedup with rolling window (prevents echo/double triggers)
"""

import re

from src.utils.logger import custom_logger as logger

# ─── 1. Smart Sentence Boundary Detector ─────────────────────────────────────

# Abbreviations that SHOULD NOT trigger sentence splits
_ABBREVIATIONS = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr",
    "rs", "no", "vol", "fig", "dept", "approx",
    "etc", "e.g", "i.e", "vs", "p.m", "a.m",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
}

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
_ABBREV_DOT   = re.compile(r'\b(' + '|'.join(_ABBREVIATIONS) + r')\.\s*', re.IGNORECASE)


def smart_split_sentences(text: str) -> list[str]:
    """
    Splits text into sentences without breaking on abbreviations.
    E.g.: "Dr. Sharma is available. Book at 10 AM." → ["Dr. Sharma is available.", "Book at 10 AM."]
    """
    # Temporarily replace abbreviation dots with placeholder
    protected = _ABBREV_DOT.sub(lambda m: m.group().replace(".", "<!DOT!>"), text)

    # Split on actual sentence boundaries
    parts = _SENTENCE_END.split(protected)

    # Restore dots and filter empty
    sentences = [p.replace("<!DOT!>", ".").strip() for p in parts if p.strip()]
    return sentences


# ─── 2. Intent-Aware TTS with SSML Prosody ───────────────────────────────────

# SSML prosody settings per intent
_PROSODY_MAP = {
    "emergency": {
        "rate": "fast",
        "pitch": "+5%",
        "volume": "loud",
        "prefix": "Please don't panic. "
    },
    "booking": {
        "rate": "medium",
        "pitch": "default",
        "volume": "medium",
        "prefix": ""
    },
    "pharmacy": {
        "rate": "medium",
        "pitch": "default",
        "volume": "medium",
        "prefix": ""
    },
    "billing": {
        "rate": "slow",    # Slow for numbers — easier to hear prices
        "pitch": "default",
        "volume": "medium",
        "prefix": ""
    },
    "lab_report": {
        "rate": "slow",    # Slow for medical results
        "pitch": "default",
        "volume": "medium",
        "prefix": ""
    },
    "farewell": {
        "rate": "slow",
        "pitch": "-2%",
        "volume": "medium",
        "prefix": ""
    },
    "llm_chat": {
        "rate": "+15%",
        "pitch": "default",
        "volume": "medium",
        "prefix": ""
    },
}

_DEFAULT_PROSODY = _PROSODY_MAP["llm_chat"]


def wrap_ssml(text: str, intent: str = "llm_chat", voice: str = "en-IN-NeerjaNeural") -> str:
    """
    Wraps text in SSML with intent-appropriate prosody.
    Used when Edge-TTS is the backend (it supports SSML).
    Falls back to plain text if SSML not supported.
    """
    prosody = _PROSODY_MAP.get(intent, _DEFAULT_PROSODY)
    prefix  = prosody.get("prefix", "")
    rate    = prosody.get("rate", "medium")
    pitch   = prosody.get("pitch", "default")
    volume  = prosody.get("volume", "medium")

    full_text = f"{prefix}{text}".strip()

    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-IN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
        f'{full_text}'
        f'</prosody>'
        f'</voice>'
        f'</speak>'
    )
    return ssml


async def speak_with_intent(tts, text: str, intent: str = "llm_chat"):
    """
    Drop-in replacement for tts.speak(text).
    Automatically applies SSML prosody based on detected intent.
    """
    if not text or not text.strip():
        return

    # Clean text first
    clean = re.sub(r'[*#_`]', '', text).strip()

    if tts.backend == "edge":
        # Edge-TTS supports SSML
        try:
            import edge_tts
            ssml = wrap_ssml(clean, intent=intent, voice=tts.edge_voice)
            communicate = edge_tts.Communicate(ssml, tts.edge_voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            if audio_data and not tts.should_stop:
                await tts._play_bytes(audio_data)
        except Exception as e:
            logger.warning(f"SSML failed, falling back to plain: {e}")
            await tts.speak(clean)
    else:
        # Non-Edge backends: just speak normally
        await tts.speak(clean)


# ─── 3. STT Confidence Filter & Filler Suppressor ────────────────────────────

_FILLER_WORDS = re.compile(
    r'\b(um+|uh+|hmm+|huh|ah+|er+|like|you know|i mean|so|well|right)\b',
    re.IGNORECASE
)

_MIN_CONFIDENCE = 0.70   # Ignore transcripts below this threshold
_MIN_WORDS      = 2       # Ignore very short transcripts (noise artifacts)


def filter_transcript(text: str, confidence: float) -> str | None:
    """
    Returns cleaned transcript if valid, None if should be ignored.

    Filters:
    1. Low confidence (<0.70) → noise, ignored
    2. Too short (<2 words) → likely a sound, ignored
    3. Filler words removed → "um I want to book appointment" → "I want to book appointment"
    """
    if confidence < _MIN_CONFIDENCE:
        logger.debug(f"[STT Filter] Ignored low-confidence ({confidence:.2f}): '{text}'")
        return None

    # Remove filler words
    cleaned = _FILLER_WORDS.sub("", text).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if len(cleaned.split()) < _MIN_WORDS:
        logger.debug(f"[STT Filter] Ignored short transcript: '{cleaned}'")
        return None

    if cleaned != text:
        logger.info(f"[STT Filter] Cleaned: '{text}' → '{cleaned}'")

    return cleaned


# ─── 4. Rolling Dedup Window ─────────────────────────────────────────────────

import time
from collections import deque


class TranscriptDeduplicator:
    """
    Prevents the same phrase from being processed twice in a short window.
    Handles echo artifacts where Deepgram picks up the AI's own speech.
    """

    def __init__(self, window_seconds: float = 3.0, max_history: int = 10):
        self._window = window_seconds
        self._history: deque = deque(maxlen=max_history)

    def is_duplicate(self, text: str) -> bool:
        """Returns True if this text was seen recently."""
        now = time.time()
        text_norm = text.lower().strip()

        # Clean old entries
        while self._history and (now - self._history[0][1]) > self._window:
            self._history.popleft()

        # Check for duplicate
        for past_text, _ in self._history:
            if past_text == text_norm:
                logger.debug(f"[Dedup] Suppressed duplicate: '{text}'")
                return True

        # Add to history
        self._history.append((text_norm, now))
        return False



