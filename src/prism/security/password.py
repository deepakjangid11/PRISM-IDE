import hashlib
import hmac
import os

ITERATIONS = 600_000
ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with 600,000 iterations and random salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )
    return f"pbkdf2_{ALGORITHM}${ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash using constant-time comparison."""
    if not plain_password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != f"pbkdf2_{ALGORITHM}":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        stored_hash = bytes.fromhex(parts[3])

        computed_key = hashlib.pbkdf2_hmac(
            ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(stored_hash, computed_key)
    except ValueError, TypeError, IndexError:
        return False
