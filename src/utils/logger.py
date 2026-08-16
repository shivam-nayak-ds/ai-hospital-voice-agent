# ═══════════════════════════════════════════════════════════════════
# src/utils/logger.py — Logger Proxy
# ═══════════════════════════════════════════════════════════════════
# Logger is configured in src/core/logger.py (single source of truth)
# This file re-exports it so legacy imports like:
#   from src.utils.logger import custom_logger
# continue to work alongside:
#   from src.core.logger import custom_logger
# ═══════════════════════════════════════════════════════════════════
from src.core.logger import custom_logger

__all__ = ["custom_logger"]
