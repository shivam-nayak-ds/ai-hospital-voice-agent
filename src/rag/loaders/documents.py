"""
documents.py
------------
Shared data model for all RAG loaders.

Every loader (JSON, Markdown, etc.) returns a list of `Document` objects
so the rest of the ingestion pipeline only needs to know about one type.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """
    A single unit of text ready for embedding and storage in the vector store.

    Attributes
    ----------
    page_content : str
        The textual content that will be embedded.
    metadata : dict
        Arbitrary key/value pairs attached to the chunk (source file, category,
        document ID, priority, etc.).  Stored alongside the embedding and
        returned with every retrieval result.
    """

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:  # pragma: no cover
        preview = self.page_content[:80].replace("\n", " ")
        return f"Document(preview={preview!r}, metadata={self.metadata})"
