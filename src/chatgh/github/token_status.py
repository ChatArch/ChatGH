"""Read-only PAT authentication and expiration checks against GitHub."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict


class TokenStatus(TypedDict):
    status: Literal["valid", "expiring", "expired", "invalid", "missing", "error"]
    valid: bool | None
    expires_at: str | None
    days_remaining: float | None
    http_status: int | None
    message: str


def _preserve_bearer_auth(request):
    """Explicit auth prevents netrc from replacing the selected PAT.

    Keep requests' environment proxy and CA support; disabling trust_env would
    also disable those settings. Authorization is set on the request below.
    """
    return request


def _parse_expiration(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace(" UTC", "+00:00").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def check_token(
    token: str | None, *, warning_days: float = 7, now: datetime | None = None
) -> TokenStatus:
    """Check one PAT without resolving/replacing credentials or returning secrets.

    An absent/unparseable expiration is unknown, not proof of no expiration.
    Permission, rate-limit and network failures leave validity unknown. A 401
    cannot distinguish expiry, revocation and incorrect credentials.
    """
    import requests

    if warning_days < 0:
        raise ValueError("warning_days must not be negative")
    checked_at = now if now is not None else datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        raise ValueError("now must include a timezone")
    result: TokenStatus = {
        "status": "missing", "valid": False, "expires_at": None,
        "days_remaining": None, "http_status": None,
        "message": "GITHUB_ACCESS_TOKEN is not configured for this profile.",
    }
    if not token or not token.strip():
        return result
    if not token.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in token):
        result.update(
            status="invalid",
            message="Token format is invalid. Check GITHUB_ACCESS_TOKEN for whitespace or non-ASCII characters.",
        )
        return result
    result.update(status="error", valid=None)
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=(5, 15),
            allow_redirects=False,
            auth=_preserve_bearer_auth,
        )
    except requests.RequestException:
        # Exceptions can include request headers or credential-derived strings.
        result["message"] = "GitHub request failed; token validity is unknown. Check the network or proxy."
        return result
    result["http_status"] = response.status_code
    if response.status_code == 401:
        result.update(status="invalid", valid=False, message="Token is invalid: it may be expired, revoked, or incorrect. Replace or regenerate it.")
        return result
    if response.status_code != 200:
        result["message"] = f"GitHub returned HTTP {response.status_code}; token validity is unknown. Check permissions, access policy, rate limits, or service availability."
        return result
    result.update(status="valid", valid=True, message="Token is currently valid. Expiration is unknown (GitHub did not return a usable expiration header).")
    expires_at = _parse_expiration(response.headers.get("GitHub-Authentication-Token-Expiration"))
    if expires_at is None:
        return result
    remaining = (expires_at - checked_at).total_seconds() / 86400
    result.update(
        expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        days_remaining=round(remaining, 6),
        message="Token is currently valid.",
    )
    if remaining <= 0:
        result.update(status="expired", valid=False, message="The reported token expiration has passed. Replace or regenerate the token.")
    elif remaining <= warning_days:
        result.update(status="expiring", message=f"Token expires within {warning_days:g} days. Renew or replace it soon.")
    return result


__all__ = ["TokenStatus", "check_token"]
