import os
import sys
import httpx
from sqlalchemy import text
from config.settings import settings
from src.db.session import engine
from src.utils.logger import custom_logger as logger

def check_postgres() -> bool:
    logger.info("Checking PostgreSQL Connection...")
    try:
        with engine.connect() as conn:
            # 1. Basic Ping
            result = conn.execute(text("SELECT 1")).scalar()
            if result != 1:
                logger.error("PostgreSQL: Ping query failed to return expected value.")
                return False
            
            # 2. Verify Table existence
            tables_query = conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in tables_query.fetchall()]
            logger.info(f"Found tables: {', '.join(tables)}")
            
            required_tables = ["DEPARTMENTS", "DOCTORS", "DOCTOR_SCHEDULES", "PATIENTS", "APPOINTMENTS", "BILLING_CATALOG", "INSURANCE_PROVIDERS", "WARD_MANAGEMENT", "LAB_REPORTS", "CONVERSATION_LOGS", "AGENT_EVENTS"]
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                logger.warning(f"PostgreSQL: The following required tables are missing: {', '.join(missing)}")
                logger.warning("Run 'scripts/db_seed.py' to initialize and seed all tables.")
            else:
                logger.success("PostgreSQL: Connected successfully. All tables exist!")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL: Connection failed: {e}")
        return False

def check_redis() -> bool:
    logger.info("Checking Redis Connection...")
    try:
        import redis
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=2
        )
        r.ping()
        
        # Test basic Set/Get
        test_key = "asha:boot_check_test"
        r.set(test_key, "working", ex=5)
        val = r.get(test_key)
        if val and val.decode("utf-8") == "working":
            logger.success("Redis: Connected successfully. Cache operations verified!")
            return True
        else:
            logger.error("Redis: Cache read/write verification failed.")
            return False
    except Exception as e:
        logger.error(f"Redis: Connection failed: {e}")
        return False

def check_qdrant() -> bool:
    logger.info("Checking Qdrant Vector DB Connection...")
    try:
        from src.rag.vectordb.qdrant_client import get_qdrant_client
        from src.rag.config.settings import rag_settings
        client = get_qdrant_client()
        
        # Get collections
        collections_resp = client.get_collections()
        collections = [col.name for col in collections_resp.collections]
        logger.info(f"Found Qdrant collections: {', '.join(collections)}")
        
        missing = []
        for col in [rag_settings.FAQ_COLLECTION, rag_settings.MARKDOWN_COLLECTION]:
            if col not in collections:
                missing.append(col)
                
        if missing:
            logger.warning(f"Qdrant: The following collections are missing: {', '.join(missing)}")
            logger.warning("Run ingestion to create and populate these collections.")
        else:
            logger.success("Qdrant: Connected successfully. Active collections verified!")
        return True
    except Exception as e:
        logger.error(f"Qdrant: Connection failed: {e}")
        return False

def check_api_keys() -> bool:
    logger.info("Checking API Keys and Credentials...")
    has_errors = False
    
    # 1. Groq Check
    if not settings.GROQ_API_KEY:
        logger.error("API Keys: GROQ_API_KEY is missing or empty.")
        has_errors = True
    elif not settings.GROQ_API_KEY.startswith("gsk_"):
        logger.warning("API Keys: GROQ_API_KEY format looks suspicious (should start with gsk_).")
    else:
        logger.success("API Keys: GROQ_API_KEY configured!")

    # 2. Google Gemini Check
    if not settings.GOOGLE_API_KEY:
        logger.error("API Keys: GOOGLE_API_KEY is missing or empty.")
        has_errors = True
    else:
        logger.success("API Keys: GOOGLE_API_KEY configured!")

    # 3. Deepgram STT Check
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    if not dg_key:
        logger.error("API Keys: DEEPGRAM_API_KEY is missing or empty.")
        has_errors = True
    else:
        logger.success("API Keys: DEEPGRAM_API_KEY configured!")

    # 4. Sarvam API Check
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if not sarvam_key:
        logger.warning("API Keys: SARVAM_API_KEY is missing (required for regional voice synthesis).")
    else:
        logger.success("API Keys: SARVAM_API_KEY configured!")

    return not has_errors

def main():
    logger.info("=========================================")
    logger.info("ASHA SYSTEM BOOT VERIFICATION SYSTEM")
    logger.info("=========================================")
    
    postgres_ok = check_postgres()
    redis_ok = check_redis()
    qdrant_ok = check_qdrant()
    apis_ok = check_api_keys()
    
    logger.info("=========================================")
    logger.info("SUMMARY RESULTS:")
    logger.info(f"PostgreSQL Connection: {'PASS' if postgres_ok else 'FAIL'}")
    logger.info(f"Redis Cache Connection: {'PASS' if redis_ok else 'FAIL'}")
    logger.info(f"Qdrant Vector Database: {'PASS' if qdrant_ok else 'FAIL'}")
    logger.info(f"Required API Keys:     {'PASS' if apis_ok else 'FAIL'}")
    logger.info("=========================================")
    
    if postgres_ok and redis_ok and qdrant_ok and apis_ok:
        logger.success("SYSTEM BOOT CHECK PASSED! All services are healthy.")
        sys.exit(0)
    else:
        logger.critical("SYSTEM BOOT CHECK FAILED! Please resolve the connection errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
