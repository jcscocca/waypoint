from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from app.schemas import ParseResult


class UnsupportedFormatError(ValueError):
    """Raised when no source adapter can safely parse an upload."""


class SourceParser(ABC):
    source_type: str
    parser_version = "mvp-1"

    @abstractmethod
    def can_parse(self, payload: bytes, filename: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_bytes(self, payload: bytes, filename: str) -> ParseResult:
        raise NotImplementedError


def stable_record_hash(record: Any) -> str:
    return sha256(repr(record).encode("utf-8")).hexdigest()


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        number = int(text)
        if number > 10_000_000_000:
            return datetime.fromtimestamp(number / 1000, tz=UTC)
        return datetime.fromtimestamp(number, tz=UTC)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def confidence_to_score(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    normalized = str(value).strip().lower()
    mapping = {
        "high": 0.9,
        "high_confidence": 0.9,
        "medium": 0.6,
        "medium_confidence": 0.6,
        "low": 0.3,
        "low_confidence": 0.3,
    }
    return mapping.get(normalized)
