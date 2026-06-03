from src.utils.logger import custom_logger as logger
from src.rag.loaders.documents import Document

class DocumentValidator:
    """
    Validator to check the integrity, size, and formatting of raw loaded Documents.
    """
    @staticmethod
    def validate(doc: Document) -> bool:
        """
        Validates a single Document object. Returns True if valid, False otherwise.
        Normalizes internal whitespaces in-place.
        """
        if not doc:
            logger.warning("Validation failed: Document object is None.")
            return False

        # 1. Check page content presence
        if not doc.page_content or not isinstance(doc.page_content, str):
            logger.warning(f"Validation failed: Document has empty or non-string page_content. Source: {doc.metadata.get('source', 'unknown')}")
            return False

        content_stripped = doc.page_content.strip()

        # 2. Check length constraints
        if len(content_stripped) < 10:
            logger.warning(f"Validation failed: Document content is too short (< 10 chars). Source: {doc.metadata.get('source', 'unknown')}")
            return False

        # 3. Normalize newlines and whitespaces
        # Convert CRLF (\r\n) to LF (\n)
        normalized_content = content_stripped.replace("\r\n", "\n")
        doc.page_content = normalized_content

        return True

    def validate_all(self, docs: list[Document]) -> list[Document]:
        """
        Filters out invalid Document objects from a list.
        """
        valid_docs = []
        for doc in docs:
            if self.validate(doc):
                valid_docs.append(doc)
        
        logger.info(f"Validated documents: {len(valid_docs)} / {len(docs)} passed verification checks.")
        return valid_docs
