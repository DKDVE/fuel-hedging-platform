"""Password hashing and verification using bcrypt.

Uses bcrypt directly (no passlib) for production-grade password security.
Bcrypt is industry-standard, well-audited, and avoids passlib/bcrypt version conflicts.
"""

import bcrypt

# Bcrypt work factor: 12 = ~250ms per hash (OWASP recommended minimum for 2024+)
BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    """Hash a plain password using bcrypt.

    Args:
        plain_password: The password to hash.

    Returns:
        The hashed password string (bcrypt format).
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash.

    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password from storage.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
