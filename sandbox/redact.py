"""Strip API keys out of text before it reaches a log.

Provider errors (notably Google, which passes the key as a URL query
parameter) embed credentials in exception messages, so any `str(e)` written
to a log can leak a live key.
"""

import os
import re

_PLACEHOLDER = "<REDACTED>"
_KEY_ENV_VARS = ("GROQ_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY")


def redact(text: str) -> str:
    """Remove known API keys and key-bearing query params from text."""
    if not text:
        return text
    for var in _KEY_ENV_VARS:
        value = os.getenv(var)
        if value and len(value) > 12:
            text = text.replace(value, _PLACEHOLDER)
    # Catch keys not present in this process's env (e.g. rotated since).
    text = re.sub(r"([?&]key=)[A-Za-z0-9._\-]{12,}", r"\1" + _PLACEHOLDER, text)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]{12,}", r"\1" + _PLACEHOLDER, text)
    return text


def safe_error(exc: BaseException) -> str:
    """Exception rendered as a log-safe string."""
    return redact(str(exc))
