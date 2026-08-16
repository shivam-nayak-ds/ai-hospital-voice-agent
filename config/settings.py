# ═══════════════════════════════════════════════════════════════════
# config/settings.py — Settings Proxy
# ═══════════════════════════════════════════════════════════════════
# All settings are defined in src/core/config.py (single source of truth)
# This file re-exports them so legacy imports like:
#   from config.settings import settings
# continue to work alongside:
#   from src.core.config import settings
# ═══════════════════════════════════════════════════════════════════
from src.core.config import settings, Settings, AppEnvironment

__all__ = ["settings", "Settings", "AppEnvironment"]
