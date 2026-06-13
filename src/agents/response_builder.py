"""
response_builder.py
-------------------
Implements the Response Builder (Speech Formatter) layer.
Cleans and formats agent responses to be warm, voice-friendly, and natural
for playback over telephony/TTS pipelines (e.g. converting "Rs. 500" to "five hundred rupees").
Includes try-except guards and trace logging.
"""

import re
from config.settings import settings
from src.utils.logger import custom_logger as logger

class AshaResponseBuilder:
    """
    Transforms text-based database and LLM outputs into friendly spoken text.
    Supports exception safety and logging.
    """
    def __init__(self):
        logger.success("AshaResponseBuilder initialized.")

    def format_speech(self, raw_text: str, session_id: str = "default") -> str:
        """
        Formats text for spoken playback.
        Uses the LLM formatter first, then applies backup regex rules.
        """
        log = logger.bind(session_id=session_id)
        if not raw_text:
            return ""

        try:
            # Remove markdown characters
            clean_text = re.sub(r'[*#_`\[\]\(\)]', '', raw_text)
            
            # 1. Try LLM formatting first
            from src.agents.ananya_agent import get_groq_client, get_gemini_client
            groq_client = get_groq_client()
            gemini_client = get_gemini_client()
            
            from src.agents.prompts import SPEECH_FORMATTER_PROMPT
            
            formatted_speech = ""
            
            if groq_client:
                try:
                    response = groq_client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": SPEECH_FORMATTER_PROMPT},
                            {"role": "user", "content": clean_text}
                        ]
                    )
                    formatted_speech = response.choices[0].message.content.strip()
                    log.info("Speech formatted successfully via Groq.")
                except Exception as e:
                    log.warning(f"Groq speech formatter failed: {e}")
                    
            if not formatted_speech and gemini_client:
                try:
                    response = gemini_client.chat.completions.create(
                        model=settings.GEMINI_MODEL,
                        messages=[
                            {"role": "system", "content": SPEECH_FORMATTER_PROMPT},
                            {"role": "user", "content": clean_text}
                        ]
                    )
                    formatted_speech = response.choices[0].message.content.strip()
                    log.info("Speech formatted successfully via Gemini fallback.")
                except Exception as e:
                    log.warning(f"Gemini speech formatter failed: {e}")

            # If LLM failed, fallback to local heuristic regex replacements
            if not formatted_speech:
                log.info("Using local heuristic speech formatting rules.")
                formatted_speech = self._local_heuristic_formatting(clean_text)

            # Final sanitization
            formatted_speech = re.sub(r'\s+', ' ', formatted_speech).strip()
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
