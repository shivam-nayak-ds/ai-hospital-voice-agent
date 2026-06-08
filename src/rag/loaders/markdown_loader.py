import os 
from typing import List
from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger

class MarkdownLoader:

    def __init__(self , file_path : str):
        self.file_path = file_path

        logger.info(f"Loading Markdown file from : {file_path}")

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found at {self.file_path}")

    def load(self) -> List[Document]:
        """
        Loads the markdown file content and splits it into Document sections.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                return []

            filename = os.path.basename(self.file_path)
            abs_path = os.path.abspath(self.file_path)
            parent_dir = os.path.basename(os.path.dirname(abs_path))
            
            category = parent_dir
            if category.endswith(".md"):
                category = category[:-3]

            # Determine document type based on parent directory name
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

            # Infer department_id from filename for department specific documents
            department_id = None
            if doc_type == "department_info":
                department_id = os.path.splitext(filename)[0].capitalize()

            metadata_base = {
                "source": filename,
                "category": category,
                "type": doc_type,
                "clinic_id": None,
                "department_id": department_id
            }

            # Split content by level-1 and level-2 markdown headings
            sections = self._split_by_headers(content)
            
            documents = []
            for section_title, section_content in sections:
                if not section_content.strip():
                    continue
                meta = metadata_base.copy()
                if section_title:
                    meta["section_title"] = section_title
                documents.append(Document(page_content=section_content, metadata=meta))
                
            logger.success(f"Successfully loaded {len(documents)} chunks from {filename}")
            return documents

        except Exception as e:
            raise ValueError(f"Failed to read markdown file {self.file_path}: {e}")

    def _split_by_headers(self, content: str) -> List[tuple[str, str]]:
        """
        Splits markdown content by '# ' and '## ' headers.
        Returns a list of tuples: (header_title, section_content)
        """
        lines = content.split("\n")
        sections = []
        current_header = ""
        current_block = []

        for line in lines:
            if line.startswith("# ") or line.startswith("## "):
                # Save the active block before starting the new heading section
                if current_block:
                    sections.append((current_header, "\n".join(current_block).strip()))
                    current_block = []
                current_header = line.lstrip("#").strip()
            else:
                current_block.append(line)

        # Save remaining block
        if current_block or current_header:
            sections.append((current_header, "\n".join(current_block).strip()))

        # If no headings found, fall back to returning whole document content
        if not sections:
            return [("", content)]
            
        return sections
