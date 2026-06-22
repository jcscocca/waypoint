from __future__ import annotations

from typing import Annotated

from fastapi import Header

from app.services.users import hash_demo_user


def current_user_hash(x_demo_user_id: Annotated[str | None, Header()] = None) -> str:
    return hash_demo_user(x_demo_user_id)
