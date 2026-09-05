"""Secret redaction helper for provider error paths (Rule R12).

Secrets, keys, or credentials must never enter error messages or logs.
"""

from typing import Any


def redact_secret(text_or_exc: Any, secret: str | None) -> str:
    """Redact a secret string from an exception or message string.

    If secret is empty or None, returns the string representation unmodified.
    Otherwise replaces all occurrences of secret with [REDACTED_API_KEY].
    """
    msg = str(text_or_exc)
    if not secret:
        return msg
    return msg.replace(secret, "[REDACTED_API_KEY]")
