import os
import json
from typing import List
from src.rag.loaders.documents import Document

class JSONLoader:
    """
    Loader for parsing structured FAQ JSON files into standardized Document objects.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        """
        Loads and parses the JSON file. Each FAQ entry is converted into a Document object.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"JSON file not found: {self.file_path}")

        documents = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                # If root is not a list, wrap it to handle it cleanly
                data = [data]

            filename = os.path.basename(self.file_path)

            for item in data:
                # Extract and clean text content
                question = item.get("question", "").strip()
                answer = item.get("answer", "").strip()
                keywords = item.get("keywords", [])
                keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

                if not question or not answer:
                    continue

                # Standardize format for embedding semantic search
                page_content = f"Question: {question}\nAnswer: {answer}"
                if keywords_str:
                    page_content += f"\nKeywords: {keywords_str}"

                # Standardize metadata structure (RAG Audit Compliant)
                metadata = {
                    "source": filename,
                    "category": item.get("category", "general"),
                    "clinic_id": item.get("clinic_id"),
                    "department_id": item.get("department"),
                    "type": "faq",
                    "priority": item.get("priority"),
                    "language": item.get("language", "en")
                }

                documents.append(Document(page_content=page_content, metadata=metadata))

        except Exception as e:
            raise ValueError(f"Failed to parse JSON file {self.file_path}: {e}")

        return documents
