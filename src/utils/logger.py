import sys
import re
from loguru import logger
from config.settings import settings 


PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

def pii_filter(record):
    """
    Healthcare Compliance: Masks sensitive data before it reaches the logs.
    """
    if not settings.ENABLE_PII_MASKING:
        return True
        
    msg = record["message"]
    
    # Masking logic
    msg = PHONE_PATTERN.sub("[PHONE_MASKED]", msg)
    msg = EMAIL_PATTERN.sub("[EMAIL_MASKED]", msg)
    
    record["message"] = msg
    return True

def setup_logger():
    """
    Configures standard logging for both Console and File.
    """
    
    logger.remove()


    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        filter=pii_filter
    )

    
    logger.add(
        "logs/app.log",
        rotation="10 MB",    
        retention="10 days", 
        compression="zip",   
        level="INFO",
        filter=pii_filter
    )
    
    return logger

custom_logger = setup_logger()
