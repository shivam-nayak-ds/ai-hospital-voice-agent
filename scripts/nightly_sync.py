import time
import schedule
import datetime
from src.rag.pipeline import RAGIngestionPipeline
from src.utils.logger import custom_logger as logger

def sync_knowledge_base():
    """Runs the RAG embedding pipeline to update ChromaDB with new markdown data."""
    logger.info(f"[{datetime.datetime.now()}] Initiating Nightly Knowledge Base Sync...")
    try:
        pipeline = RAGIngestionPipeline()
        pipeline.run()
        logger.success(f"[{datetime.datetime.now()}] Nightly Sync Completed Successfully! AI is up-to-date.")
    except Exception as e:
        logger.error(f"[{datetime.datetime.now()}] Nightly Sync FAILED: {e}")

def start_scheduler():
    logger.info("Nightly Sync Daemon Started. RAG will update every night at 12:00 AM (Midnight).")
    
    # Schedule the sync at midnight every day
    schedule.every().day.at("00:00").do(sync_knowledge_base)
    
    # For testing purposes, you can uncomment the line below to run it every minute
    # schedule.every(1).minutes.do(sync_knowledge_base)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60) # Check every 60 seconds
    except KeyboardInterrupt:
        logger.info("Nightly Sync Daemon Stopped manually.")

if __name__ == "__main__":
    # If someone just runs this file directly, we ask them if they want to run it NOW or start the daemon
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        sync_knowledge_base()
    else:
        start_scheduler()
