import os
from typing import List
from src.rag.loaders.documents import Document

class MarkdownLoader:
    """
    Loader for parsing plain-text markdown files into standardized Document objects.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        """
        Loads the markdown file content and wraps it in a single Document object.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Markdown file not found: {self.file_path}")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                return []

            filename = os.path.basename(self.file_path)
            
            # Determine category and type from the directory structure
            abs_path = os.path.abspath(self.file_path)
            parent_dir = os.path.basename(os.path.dirname(abs_path))
            
            # Clean up directory names like 'department_info.md' to 'department_info'
            category = parent_dir
            if category.endswith(".md"):
                category = category[:-3]

            # Map category to standard document type
            doc_type = "general"
            if "policy" in category:
                doc_type = "policy"
            elif "guideline" in category:
                doc_type = "guidelines"
            elif "knowledge" in category:
                doc_type = "knowledge"
            elif "department" in category:
                doc_type = "department_info"
            elif "facilities" in category:
                doc_type = "facilities"

            # Check if we can infer department_id from filename (e.g., cardiology.md -> Cardiology)
            department_id = None
            if doc_type == "department_info":
                department_id = os.path.splitext(filename)[0].capitalize()

            metadata = {
                "source": filename,
                "category": category,
                "type": doc_type,
                "clinic_id": None,
                "department_id": department_id
            }

            return [Document(page_content=content, metadata=metadata)]

        except Exception as e:
            raise ValueError(f"Failed to read markdown file {self.file_path}: {e}")
