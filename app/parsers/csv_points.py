from __future__ import annotations

import csv
from io import StringIO

from app.parsers.base import SourceParser, parse_datetime, stable_record_hash
from app.schemas import LocationObservation, ParseResult


class CsvPointsParser(SourceParser):
    source_type = "csv"

    def can_parse(self, payload: bytes, filename: str) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        header = payload[:500].decode("utf-8", errors="ignore").lower()
        return "timestamp" in header and "latitude" in header and "longitude" in header

    def parse_bytes(self, payload: bytes, filename: str) -> ParseResult:
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        observations: list[LocationObservation] = []
        for row in reader:
            latitude = _float_or_none(row.get("latitude"))
            longitude = _float_or_none(row.get("longitude"))
            observations.append(
                LocationObservation(
                    source_type=self.source_type,
                    source_record_type="point",
                    source_record_hash=stable_record_hash(row),
                    observed_at_utc=parse_datetime(row.get("timestamp")),
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_m=_float_or_none(row.get("accuracy_m")),
                    activity_type=_empty_to_none(row.get("activity_type")),
                )
            )
        return ParseResult(
            source_type=self.source_type,
            detected_schema="csv_points",
            parser_version=self.parser_version,
            observations=observations,
        )


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
