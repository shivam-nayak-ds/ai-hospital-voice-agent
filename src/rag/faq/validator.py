from typing import Any

from pydantic import BaseModel, Field, ValidationError

# pyrefly: ignore [missing-import]
from src.utils.logger import custom_logger as logger


class FAQItemSchema(BaseModel):
    id: str
    category: str
    department: str | None = "general"
    question: str
    answer: str
    keywords: list[str] = Field(default_factory=list)
    priority: str | None = "medium"
    language: str | None = "en"

    model_config = {
        "extra": "ignore"  # Ignore internal fields like _source_file during schema validation
    }

    def to_metadata(self, source_file: str) -> dict:
        """
        Serializes the model fields into a standardized metadata dictionary.
        """
        return {
            "id": self.id,
            "category": self.category,
            "department": self.department,
            "type": "faq",
            "source": source_file,
            "priority": self.priority,
            "language": self.language
        }

class FAQValidator:
    """
    Validator to check the structure and content of raw FAQ items.
    """
    @staticmethod
    def validate_item(item: dict[str, Any]) -> FAQItemSchema | None:
        """
        Validates a single raw FAQ dictionary. Returns FAQItemSchema if valid, else None.
        """
        # 1. Pydantic Schema check
        try:
            validated_item = FAQItemSchema(**item)
        except ValidationError as e:
            logger.warning(f" Validation Failed (Schema Error): {e.errors()} for item: {item.get('id', 'Unknown')}")
            return None

        # 2. Content completeness check
        if not validated_item.question.strip() or not validated_item.answer.strip():
            logger.warning(f" Validation Failed (Empty text) for item: {validated_item.id}")
            return None

        if len(validated_item.answer.strip()) < 10:
            logger.warning(f" Validation Failed (Answer too short) for item: {validated_item.id}")
            return None

        # 3. Category completeness check
        if not validated_item.category.strip():
            logger.warning(f" Validation Failed (Empty category) for item: {validated_item.id}")
            return None

        return validated_item

    def validate_all(self, items: list[dict[str, Any]]) -> list[FAQItemSchema]:
        """
        Filters and validates a list of raw FAQ dictionaries.
        """
        valid_items = []
        for item in items:
            validated = self.validate_item(item)
            if validated:
                valid_items.append(validated)
        logger.info(f"Successfully validated {len(valid_items)} / {len(items)} FAQ items.")
        return valid_items
