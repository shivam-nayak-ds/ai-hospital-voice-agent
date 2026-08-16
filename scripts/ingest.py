import asyncio
import os
import sys
from pathlib import Path

# Set offline mode BEFORE any other imports to prevent HF network requests
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.rag.ingestion.ingest import run_full_ingestion
from src.utils.logger import custom_logger as logger


async def main():
    logger.info("Starting knowledge base ingestion pipeline...")
    try:
        await run_full_ingestion()
        logger.success("Knowledge base ingestion pipeline successfully finished.")
    except Exception as e:
        logger.critical(f"Ingestion runner failed with critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Standard event loop policy configuration for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
