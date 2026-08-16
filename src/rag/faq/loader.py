import json
import os
from typing import Any

from src.utils.logger import custom_logger as logger


class FAQLoader:
    """
    Loader for parsing structured FAQ JSON files into raw dictionary records.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[dict[str, Any]]:
        """
        Loads and parses a single JSON FAQ file. Returns a list of raw dictionaries.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"FAQ file not found: {self.file_path}")
            raise FileNotFoundError(f"FAQ file not found: {self.file_path}")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = [data]

            filename = os.path.basename(self.file_path)
            for item in data:
                item["_source_file"] = filename

            logger.info(f"Loaded {len(data)} raw FAQ records from {filename}")
            return data

        except Exception as e:
            logger.error(f"Failed to load JSON file {self.file_path}: {e}")
            raise ValueError(f"Failed to load JSON file {self.file_path}: {e}")
