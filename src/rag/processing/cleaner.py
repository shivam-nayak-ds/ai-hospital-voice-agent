"""
cleaner.py
----------
Text cleaning utilities for RAG document pre-processing.

Applied BEFORE chunking to remove noise that would pollute embeddings:
  - Strips repeated whitespace and blank lines
  - Removes common Markdown formatting artifacts (horizontal rules, HTML tags)
  - Normalises Unicode quotation marks and dashes
  - Collapses excessive punctuation runs
"""

import re
import unicodedata

from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger

# ─── Compiled Regex Patterns ──────────────────────────────────────────────────

# Horizontal rules: ---, ***, ===
_HR_PATTERN = re.compile(r"^[-*=]{3,}\s*$", re.MULTILINE)

# HTML/XML tags
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Consecutive blank lines → single blank line
_MULTI_BLANK_PATTERN = re.compile(r"\n{3,}")

# Trailing whitespace on each line
_TRAILING_WS_PATTERN = re.compile(r"[ \t]+$", re.MULTILINE)

# Unicode fancy quotes → ASCII equivalents
_FANCY_QUOTES = str.maketrans({
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u2026": "...",  # ellipsis
})

# Repeated punctuation: e.g. "!!!" → "!" or "..." is fine (see ellipsis above)
_REPEATED_PUNCT = re.compile(r"([!?,;])\1{2,}")


# ─── Core Cleaning Function ───────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Applies a deterministic cleaning pipeline to a raw text string.

    Steps:
      1. Normalise Unicode to NFC form.
      2. Translate fancy quotes and dashes to ASCII.
      3. Remove HTML/XML tags.
      4. Remove Markdown horizontal rules.
      5. Strip trailing whitespace from each line.
      6. Collapse 3+ consecutive blank lines to 1.
      7. Collapse repeated punctuation runs.
      8. Final strip.

    Returns:
        Cleaned text string.
    """
    if not text:
        return ""

    # 1. Unicode normalisation
    text = unicodedata.normalize("NFC", text)

    # 2. Fancy quote / dash substitution
    text = text.translate(_FANCY_QUOTES)

    # 3. Remove HTML tags
    text = _HTML_TAG_PATTERN.sub(" ", text)

    # 4. Remove horizontal rules
    text = _HR_PATTERN.sub("", text)

    # 5. Strip trailing whitespace per line
    text = _TRAILING_WS_PATTERN.sub("", text)

    # 6. Collapse multiple blank lines
    text = _MULTI_BLANK_PATTERN.sub("\n\n", text)

    # 7. Collapse repeated punctuation
    text = _REPEATED_PUNCT.sub(r"\1", text)

    return text.strip()


# ─── Document-Level Cleaner ───────────────────────────────────────────────────

class DocumentCleaner:
    """
    Applies `clean_text` to a list of `Document` objects in place.
    Documents whose content becomes empty after cleaning are dropped.
    """

    def clean_all(self, documents: list[Document]) -> list[Document]:
        """
        Cleans and filters a list of documents.

        Returns:
            List of documents with cleaned `page_content`, empty docs removed.
        """
        cleaned: list[Document] = []
        dropped = 0

        for doc in documents:
            cleaned_content = clean_text(doc.page_content)
            if not cleaned_content:
                dropped += 1
                continue
            cleaned.append(Document(page_content=cleaned_content, metadata=doc.metadata))

        if dropped:
            logger.warning(f"DocumentCleaner: dropped {dropped} empty documents after cleaning.")

        logger.info(f"DocumentCleaner: cleaned {len(cleaned)} documents.")
        return cleaned
