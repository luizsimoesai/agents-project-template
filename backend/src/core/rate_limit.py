"""Rate limiter shared across auth routes.

slowapi binds limits per-IP via get_remote_address; storage is in-process so
each instance counts independently. For multi-instance deployments configure
slowapi with a Redis backend (storage_uri="redis://...").
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.settings import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
