import sys
import os
import re
from loguru import logger
from src.core.config import settings

# Mask patterns for compliance (PII protection)
PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

def pii_compliance_filter(record) -> bool:
    try:
        if not settings.ENABLE_PII_MASKING:
            return True
            
        msg = record.get("message", "")
        if isinstance(msg, str):
            msg = PHONE_PATTERN.sub("[PHONE_MASKED]", msg)
            msg = EMAIL_PATTERN.sub("[EMAIL_MASKED]", msg)
            record["message"] = msg
            
        # Mask custom fields inside bound record metadata
        extra = record.get("extra", {})
        for k, v in extra.items():
            if isinstance(v, str):
                v_clean = PHONE_PATTERN.sub("[PHONE_MASKED]", v)
                v_clean = EMAIL_PATTERN.sub("[EMAIL_MASKED]", v)
                record["extra"][k] = v_clean
    except Exception as e:
        sys.stderr.write(f"PII filtering failure: {e}\n")
    return True

def setup_app_logger():
    logger.remove()
    
    # Custom format matching timestamp | level | request_id | module | message
    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]}</cyan> | "
        "<cyan>{name}:{function}:{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Bind request_id fallback context
    logger.configure(extra={"request_id": "system_startup"})
    
    # Console Output
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=log_format,
        filter=pii_compliance_filter
    )
    
    # File Output (Production audit trail)
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/app.log",
        rotation="20 MB",
        retention="14 days",
        compression="zip",
        level="INFO",
        encoding="utf-8",
        format=log_format,
        filter=pii_compliance_filter
    )
    return logger

custom_logger = setup_app_logger()
