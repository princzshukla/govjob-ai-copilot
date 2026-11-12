from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Per-IP limiter. get_remote_address uses request.client.host; run uvicorn with
# --proxy-headers behind a reverse proxy so the real client IP is used.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
)
