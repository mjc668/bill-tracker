"""Helpers for keeping PII (emails) out of server logs."""

_MASK = "***"


def mask_email(value: str) -> str:
    """Mask an email for logging: keep the first local char and the domain.

    ``alice@example.com`` becomes ``a***@example.com``. Values that are not
    shaped like an email (missing/empty local part or domain) collapse to
    ``***`` so a malformed value can never leak verbatim into a log line.
    """
    local, sep, domain = value.partition("@")
    if not sep or not local or not domain:
        return _MASK
    return f"{local[0]}***@{domain}"
