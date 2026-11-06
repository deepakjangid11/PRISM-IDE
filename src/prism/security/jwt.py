import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from prism.config.settings import settings

_REVOCATION_FILE = Path(".prism/revoked_tokens.json")
_revoked_tokens: set[str] = set()


def _load_revoked_tokens() -> set[str]:
    """Load persisted revoked tokens from disk if present."""
    if _REVOCATION_FILE.exists():
        try:
            content = _REVOCATION_FILE.read_text(encoding="utf-8").strip()
            if content:
                loaded = json.loads(content)
                if isinstance(loaded, list):
                    return set(loaded)
        except OSError, json.JSONDecodeError, ValueError:
            pass
    return set()


# Initialize in-memory cache with persisted revoked tokens
_revoked_tokens.update(_load_revoked_tokens())


def revoke_token(token_or_jti: str) -> None:
    """Add a token or JTI identifier to the revocation set and persist across restarts."""
    if token_or_jti:
        cleaned = token_or_jti.strip()
        _revoked_tokens.add(cleaned)
        try:
            _REVOCATION_FILE.parent.mkdir(parents=True, exist_ok=True)
            _REVOCATION_FILE.write_text(
                json.dumps(list(_revoked_tokens)),
                encoding="utf-8",
            )
        except OSError, ValueError:
            pass


def is_token_revoked(token_or_jti: str) -> bool:
    """Check if token or JTI identifier has been revoked (checking in-memory and disk)."""
    if not token_or_jti:
        return False
    cleaned = token_or_jti.strip()
    if cleaned in _revoked_tokens:
        return True
    # Synchronize from persistence file (multi-worker coordination)
    persisted = _load_revoked_tokens()
    if persisted:
        _revoked_tokens.update(persisted)
    return cleaned in _revoked_tokens


def _base64url_encode(data: bytes) -> str:
    """Encode bytes into URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    """Decode URL-safe base64 string with restored padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("ascii"))


def create_token(
    payload: dict[str, Any],
    expires_delta: timedelta,
    token_type: str = "access",
) -> str:
    """Generate a signed RFC 7519 HMAC-SHA256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = datetime.now(UTC)
    claims = {
        **payload,
        "jti": payload.get("jti") or f"jti_{uuid.uuid4().hex}",
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    claims_bytes = json.dumps(claims, separators=(",", ":")).encode("utf-8")

    encoded_header = _base64url_encode(header_bytes)
    encoded_claims = _base64url_encode(claims_bytes)
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")

    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_claims}.{encoded_signature}"


def create_access_token(
    developer_id: str,
    role: str = "developer",
    expires_minutes: int | None = None,
) -> str:
    """Create a short-lived access token."""
    delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    return create_token({"sub": developer_id, "role": role}, delta, "access")


def create_refresh_token(
    developer_id: str,
    expires_days: int | None = None,
) -> str:
    """Create a long-lived refresh token."""
    delta = timedelta(days=expires_days or settings.refresh_token_expire_days)
    return create_token({"sub": developer_id}, delta, "refresh")


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Verify and decode a signed JWT token."""
    cleaned_token = token.strip()
    if is_token_revoked(cleaned_token):
        raise ValueError("Token has been revoked")

    parts = cleaned_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    encoded_header, encoded_claims, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")

    expected_sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    provided_sig = _base64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Invalid token signature")

    claims_raw = _base64url_decode(encoded_claims)
    claims: dict[str, Any] = json.loads(claims_raw.decode("utf-8"))

    if is_token_revoked(claims.get("jti", "")):
        raise ValueError("Token has been revoked")

    now_ts = int(datetime.now(UTC).timestamp())
    exp = claims.get("exp")
    if exp is not None and now_ts > exp:
        raise ValueError("Token has expired")

    if expected_type and claims.get("type") != expected_type:
        raise ValueError(
            f"Expected token of type '{expected_type}', got '{claims.get('type')}'"
        )

    return claims
