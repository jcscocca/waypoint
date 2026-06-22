from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from app.parsers.base import SourceParser, parse_datetime, stable_record_hash
from app.schemas import LocationObservation, ParseResult


class GpxPointsParser(SourceParser):
    source_type = "gpx"

    def can_parse(self, payload: bytes, filename: str) -> bool:
        return filename.lower().endswith(".gpx") or b"<gpx" in payload[:500].lower()

    def parse_bytes(self, payload: bytes, filename: str) -> ParseResult:
        root = ET.fromstring(payload.decode("utf-8"))
        observations = []
        for point in root.iter():
            if not point.tag.endswith("trkpt"):
                continue
            latitude = _float_or_none(point.attrib.get("lat"))
            longitude = _float_or_none(point.attrib.get("lon"))
            observed_at = None
            for child in point:
                if child.tag.endswith("time"):
                    observed_at = parse_datetime(child.text)
                    break
            observations.append(
                LocationObservation(
                    source_type=self.source_type,
                    source_record_type="trkpt",
                    source_record_hash=stable_record_hash(ET.tostring(point, encoding="unicode")),
                    observed_at_utc=observed_at,
                    latitude=latitude,
                    longitude=longitude,
                )
            )
        return ParseResult(
            source_type=self.source_type,
            detected_schema="gpx_track_points",
            parser_version=self.parser_version,
            observations=observations,
        )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
