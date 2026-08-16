import glob
import os

from src.rag.faq.cleaner import FAQCleaner
from src.rag.faq.loader import FAQLoader
from src.rag.faq.validator import FAQValidator
from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class FAQPipeline:
    """
    Orchestration pipeline to load, validate, clean, and format FAQ JSON datasets
    into standardized Document objects ready for embedding and indexing.
    """
    def __init__(self, faqs_dir: str = "data/raw/internal/faqs"):
        self.faqs_dir = faqs_dir
        self.loader_class = FAQLoader
        self.validator = FAQValidator()
        self.cleaner = FAQCleaner()

    def run(self) -> list[Document]:
        """
        Runs the full FAQ processing pipeline on all JSON files in the faqs_dir.
        Returns a list of standardized Document objects.
        """
        if not os.path.exists(self.faqs_dir):
            logger.error(f"FAQ directory does not exist: {self.faqs_dir}")
            return []

        # Find all JSON FAQ files in the directory
        json_pattern = os.path.join(self.faqs_dir, "*.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            logger.warning(f"No JSON FAQ files found in: {self.faqs_dir}")
            return []

        logger.info(f"Starting FAQ pipeline. Found {len(json_files)} JSON files to process.")
        all_documents: list[Document] = []

        for file_path in json_files:
            filename = os.path.basename(file_path)
            try:
                # 1. Load raw dictionary records
                loader = self.loader_class(file_path)
                raw_records = loader.load()

                # 2. Validate records against schema
                validated_records = self.validator.validate_all(raw_records)

                # 3. Clean and normalize text fields
                cleaned_records = self.cleaner.clean_all(validated_records)

                # 4. Format into Document objects
                for item in cleaned_records:
                    # Context formatting (Option 1: Labels + Keywords)
                    keywords_str = ", ".join(item.keywords) if item.keywords else ""
                    page_content = f"Question: {item.question}\nAnswer: {item.answer}"
                    if keywords_str:
                        page_content += f"\nKeywords: {keywords_str}"

                    # Build standardized metadata
                    metadata = item.to_metadata(source_file=filename)

                    doc = Document(page_content=page_content, metadata=metadata)
                    all_documents.append(doc)

                logger.success(f"Successfully processed and formatted {len(cleaned_records)} documents from {filename}")

            except Exception as e:
                logger.error(f"Failed to process FAQ file {filename}: {e}")

        logger.success(f"FAQ Ingestion Pipeline finished. Compiled {len(all_documents)} total Document blocks.")
        return all_documents
