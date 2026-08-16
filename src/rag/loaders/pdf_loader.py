import os

from pypdf import PdfReader

from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class PDFLoader:
    """
    Loader for parsing binary PDF files page-by-page into standardized Document objects.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        logger.info(f"Loading PDF file from: {file_path}")

    def load(self) -> list[Document]:
        """
        Loads the PDF page-by-page, returning a Document object for each page.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")

        documents = []
        try:
            reader = PdfReader(self.file_path)
            filename = os.path.basename(self.file_path)
            parent_dir = os.path.basename(os.path.dirname(os.path.abspath(self.file_path)))

            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text or not text.strip():
                    continue

                metadata = {
                    "source": filename,
                    "category": parent_dir,
                    "type": "handbook",
                    "page": i + 1,
                    "clinic_id": None,
                    "department_id": None
                }

                documents.append(Document(page_content=text.strip(), metadata=metadata))
            logger.success(f"Successfully extracted {len(documents)} pages from PDF: {filename}")

        except Exception as e:
            logger.error(f"Failed to read PDF file {self.file_path}: {e}")
            raise ValueError(f"Failed to read PDF file {self.file_path}: {e}")

        return documents
