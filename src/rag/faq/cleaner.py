import re

from src.rag.faq.validator import FAQItemSchema
from src.utils.logger import custom_logger as logger


class FAQCleaner:
    """
    Cleaner to sanitize and normalize text fields of validated FAQ items.
    """
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans whitespaces, handles line breaks, and strips leading/trailing spacing.
        """
        if not text:
            return ""
        
        # 1. Replace multiple spaces, tabs, or newlines with a single space
        text = re.sub(r"\s+", " ", text)
        
        # 2. Strip leading/trailing whitespaces
        return text.strip()

    def clean_item(self, item: FAQItemSchema) -> FAQItemSchema:
        """
        Returns a new FAQItemSchema with cleaned question, answer, and keywords.
        """
        item.question = self.clean_text(item.question)
        item.answer = self.clean_text(item.answer)
        
        # Clean keywords to lowercase and trim spaces
        cleaned_keywords = []
        for kw in item.keywords:
            cleaned_kw = self.clean_text(kw).lower()
            if cleaned_kw:
                cleaned_keywords.append(cleaned_kw)
        
        item.keywords = cleaned_keywords
        return item

    def clean_all(self, items: list[FAQItemSchema]) -> list[FAQItemSchema]:
        """
        Cleans a list of FAQItemSchema items in place.
        """
        cleaned_items = []
        for item in items:
            cleaned_items.append(self.clean_item(item))
        logger.info(f"Successfully cleaned and normalized {len(cleaned_items)} FAQ items.")
        return cleaned_items
