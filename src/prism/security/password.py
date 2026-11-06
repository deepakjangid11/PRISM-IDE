import hashlib
import hmac
import os
from typing import Literal

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

ITERATIONS = 600_000
ALGORITHM = "sha256"

# Argon2id OWASP recommended parameters
ARGON2_MEMORY_COST = 65536  # 64 MB
ARGON2_ITERATIONS = 1
ARGON2_LANES = 4
ARGON2_KEY_LEN = 32


def hash_password_argon2id(password: str) -> str:
    """Hash password using genuine OWASP-recommended Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = os.urandom(16)
    kdf = Argon2id(
        salt=salt,
        length=ARGON2_KEY_LEN,
        iterations=ARGON2_ITERATIONS,
        lanes=ARGON2_LANES,
        memory_cost=ARGON2_MEMORY_COST,
    )
    derived = kdf.derive(password.encode("utf-8"))
    return f"argon2id$v=19$m={ARGON2_MEMORY_COST},t={ARGON2_ITERATIONS},p={ARGON2_LANES}${salt.hex()}${derived.hex()}"


def hash_password_pbkdf2(password: str) -> str:
    """Hash plaintext password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
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


def hash_password(
    password: str,
    algorithm: Literal["pbkdf2_sha256", "argon2id"] = "pbkdf2_sha256",
) -> str:
    """Hash password with selected algorithm (default pbkdf2_sha256 with argon2id supported)."""
    if algorithm == "argon2id":
        return hash_password_argon2id(password)
    return hash_password_pbkdf2(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against stored hash (supporting both Argon2id and PBKDF2)."""
    if not plain_password or not hashed_password:
        return False
    try:
        # Check for Argon2id hash
        if hashed_password.startswith("argon2id$"):
            parts = hashed_password.split("$")
            if len(parts) != 5:
                return False
            salt = bytes.fromhex(parts[3])
            stored_key = bytes.fromhex(parts[4])
            kdf = Argon2id(
                salt=salt,
                length=len(stored_key),
                iterations=ARGON2_ITERATIONS,
                lanes=ARGON2_LANES,
                memory_cost=ARGON2_MEMORY_COST,
            )
            try:
                kdf.verify(plain_password.encode("utf-8"), stored_key)
                return True
            except InvalidKey:
                return False

        # Check for PBKDF2 hash
        if hashed_password.startswith(f"pbkdf2_{ALGORITHM}$"):
            parts = hashed_password.split("$")
            if len(parts) != 4:
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

        return False
    except ValueError, TypeError, IndexError:
        return False
