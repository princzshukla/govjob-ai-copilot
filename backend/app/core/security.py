import hashlib
import secrets
import threading

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# PasswordHasher() defaults to Argon2id (the PHC winner): memory-hard, resists
# GPU/ASIC cracking. Never used for anything but passwords.
_password_hasher = PasswordHasher()

# Bound concurrent Argon2 work: Starlette's threadpool defaults to 40 threads,
# so 40 simultaneous logins would otherwise allocate 40 x 64 MiB = ~2.5 GiB.
_argon2_semaphore = threading.Semaphore(4)

# Verified when the email is unknown, so login takes ~the same time whether or
# not the account exists (blocks user enumeration via response timing).
DUMMY_PASSWORD_HASH = _password_hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    with _argon2_semaphore:
        return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        with _argon2_semaphore:
            return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def generate_session_token() -> str:
    # 32 random bytes -> 43-char URL-safe string. High entropy: unguessable.
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    # SHA-256 is appropriate here (unlike passwords): the token is 256-bit
    # random, so a fast one-way hash is enough to protect a DB leak.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
