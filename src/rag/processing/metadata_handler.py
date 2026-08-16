import os

from src.rag.config.constants import VALID_DEPARTMENTS
from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class MetadataExtractor:
    """
    Standardizes, validates, and enriches document metadata fields before chunking.
    """
    @staticmethod
    def extract(doc: Document, root_dir: str = "data/raw/internal") -> Document:
        """
        Enriches and standardizes document metadata in-place.
        """
        # Ensure metadata dict exists
        if doc.metadata is None:
            doc.metadata = {}

        # 1. Determine file_name and source_type
        source_path_str = doc.metadata.get("source", "")
        # If source is a full path, get basename, otherwise default to source field
        file_name = os.path.basename(source_path_str) if source_path_str else "unknown"
        doc.metadata["file_name"] = file_name

        # Source type mapping by extension
        ext = file_name.split(".")[-1].lower() if "." in file_name else "txt"
        if ext == "md":
            doc.metadata["source_type"] = "markdown"
        elif ext == "json":
            doc.metadata["source_type"] = "json"
        elif ext == "pdf":
            doc.metadata["source_type"] = "pdf"
        else:
            doc.metadata["source_type"] = ext

        # 2. Extract Category (folder name) and Relative Path
        # Category is usually already set, but let's double check or set it
        if "category" not in doc.metadata or not doc.metadata["category"]:
            doc.metadata["category"] = "general"

        doc.metadata["relative_path"] = doc.metadata.get("relative_path", file_name)

        # 3. Standardize and normalize Department ID
        dept_id = doc.metadata.get("department_id")
        if dept_id:
            dept_lower = str(dept_id).strip().lower()
            # Check if department matches VALID_DEPARTMENTS
            if dept_lower in VALID_DEPARTMENTS:
                doc.metadata["department_id"] = dept_lower
            else:
                # Try partial matching
                matched = False
                for valid_dept in VALID_DEPARTMENTS:
                    if valid_dept in dept_lower or dept_lower in valid_dept:
                        doc.metadata["department_id"] = valid_dept
                        matched = True
                        break
                if not matched:
                    doc.metadata["department_id"] = "general"
        else:
            # Fallback based on filename or category
            file_stem = os.path.splitext(file_name)[0].lower()
            if file_stem in VALID_DEPARTMENTS:
                doc.metadata["department_id"] = file_stem
            else:
                doc.metadata["department_id"] = "general"

        # 4. Standardize Document Type
        doc_type = doc.metadata.get("type", "general")
        doc.metadata["type"] = doc_type

        # 5. Version Control
        doc.metadata["version"] = doc.metadata.get("version", "1.0")

        return doc

    def process_all(self, docs: list[Document], root_dir: str = "data/raw/internal") -> list[Document]:
        """
        Enriches metadata for all documents in-place.
        """
        for doc in docs:
            self.extract(doc, root_dir)
        logger.info(f"Successfully processed metadata for {len(docs)} documents.")
        return docs
