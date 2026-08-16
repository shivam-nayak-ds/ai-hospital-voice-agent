"""
response_builder.py
-------------------
Implements the Response Builder (Speech Formatter) layer.
Cleans and formats agent responses to be warm, voice-friendly, and natural
for playback over telephony/TTS pipelines (e.g. converting "Rs. 500" to "five hundred rupees").

Uses INSTANT local heuristic formatting (regex rules) instead of calling an LLM.
This avoids blocking the event loop for 1-3 seconds on every response.
"""

import re

from src.utils.logger import custom_logger as logger


class AshaResponseBuilder:
    """
    Transforms text-based database and LLM outputs into friendly spoken text.
    Uses local heuristic formatting for instant, non-blocking execution.
    """
    def __init__(self):
        logger.success("AshaResponseBuilder initialized.")

    def format_speech(self, raw_text: str, session_id: str = "default") -> str:
        """
        Formats text for spoken playback using instant local heuristic rules.
        No LLM calls — runs in <1ms instead of 1-3 seconds.
        """
        log = logger.bind(session_id=session_id)
        if not raw_text:
            return ""

        try:
            # Step 1: Strip markdown characters
            clean_text = re.sub(r'[*#_`\[\]\(\)]', '', raw_text)
            
            # Step 2: Apply local heuristic speech formatting (instant, no API call)
            formatted_speech = self._local_heuristic_formatting(clean_text)

            # Step 3: Collapse multiple spaces into one
            formatted_speech = re.sub(r'\s+', ' ', formatted_speech).strip()
            
            log.info("Speech formatted via local heuristics in <1ms")
            return formatted_speech

        except Exception as e:
            log.exception(f"Unhandled exception in response speech formatting: {e}")
            # Secure return: strip basic characters and return original string
            return re.sub(r'[*#_`]', '', raw_text)

    def _local_heuristic_formatting(self, text: str) -> str:
        """
        Heuristic speech replacements for numbers, currencies, and dates.
        """
        # Convert Rs. X or Rs X to X rupees
        text = re.sub(r'Rs\.?\s*(\d+)', r'\1 rupees', text)
        text = re.sub(r'(\d+)\s*rupees', lambda m: f"{m.group(1)} rupees", text)
        
        # Convert simple YYYY-MM-DD dates to spoken dates (roughly)
        date_pattern = r'\b(\d{4})-(\d{2})-(\d{2})\b'
        months = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        
        def date_repl(match):
            _, m, d = match.groups()
            m_idx = int(m)
            d_val = int(d)
            m_name = months[m_idx] if 0 < m_idx <= 12 else ""
            suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
            suffix = suffixes.get(d_val % 10, 'th') if d_val not in [11, 12, 13] else 'th'
            return f"{m_name} {d_val}{suffix}"
            
        text = re.sub(date_pattern, date_repl, text)
        
        # Strip remaining formatting hyphens or bullet items
        text = text.replace("-", " ").replace("|", " ")
        return text
