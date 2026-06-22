from __future__ import annotations

from hashlib import sha256

from app.config import get_settings


def hash_demo_user(user_id: str | None) -> str:
    stable_user = user_id or "demo_user"
    salt = get_settings().user_hash_salt
    return sha256(f"{salt}:{stable_user}".encode()).hexdigest()
