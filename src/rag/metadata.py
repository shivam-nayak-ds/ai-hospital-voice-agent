import os
from src.utils.logger import custom_logger as logger

class MetadataManager:
    """
    Metadata Enricher: Adds custom tags to documents for better filtering.
    """
    def enrich_metadata(self, documents):
        logger.info(f"Enriching metadata for {len(documents)} document pages...")
        
        for doc in documents:
            source = doc.metadata.get("source", "").lower()
            
            # Smart Tagging based on filename
            if "emergency" in source or "icu" in source:
                doc.metadata["category"] = "URGENT_CARE"
            elif "doctor" in source or "directory" in source:
                doc.metadata["category"] = "DOCTOR_INFO"
            elif "insurance" in source or "tpa" in source:
                doc.metadata["category"] = "BILLING_INSURANCE"
            elif "lab" in source or "surgical" in source:
                doc.metadata["category"] = "SERVICES_COST"
            else:
                doc.metadata["category"] = "GENERAL"
                
            # Add Hospital Name Tag
            doc.metadata["hospital"] = "City Care Hospital"
            
        logger.info("Metadata enrichment complete.")
        return documents

if __name__ == "__main__":
    # Test
    from langchain_core.documents import Document
    test_doc = Document(page_content="Test", metadata={"source": "city_care_emergency_icu.pdf"})
    manager = MetadataManager()
    enriched = manager.enrich_metadata([test_doc])
    print(f"Metadata: {enriched[0].metadata}")
