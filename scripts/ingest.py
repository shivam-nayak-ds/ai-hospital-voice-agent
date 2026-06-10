import sys
import asyncio
from pathlib import Path

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
