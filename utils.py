import re

MAX_SIZE_FILE_NAME_LIMIT = 200
RETRYABLE_403_REASONS = {"userRateLimitExceeded", "rateLimitExceeded"}

def sanitize_filename(filename: str, *, fallback: str = "track") -> str:
    """Sanitize a filename for safe use in the OS and ffmpeg"""
    sanitized = re.sub(r'[ #<>:"/\\|&?*;()$\[\]\'\n\t%]', '_', filename)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    sanitized = sanitized.strip('._ ')  # strips dots too

    if sanitized in {"", ".", ".."}:
        sanitized = fallback

    # Clamp length for filesystem limits
    return sanitized[:MAX_SIZE_FILE_NAME_LIMIT]