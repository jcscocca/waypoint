from __future__ import annotations

import json
from typing import Any

from app.normalization.geo import is_valid_coordinate
from app.parsers.base import SourceParser, parse_datetime, stable_record_hash
from app.schemas import LocationObservation, ParseResult


class GeoJsonPointsParser(SourceParser):
    source_type = "geojson"

    def can_parse(self, payload: bytes, filename: str) -> bool:
        return (
            filename.lower().endswith((".geojson", ".json"))
            and b'"FeatureCollection"' in payload[:2000]
        )

    def parse_bytes(self, payload: bytes, filename: str) -> ParseResult:
        data = json.loads(payload.decode("utf-8"))
        observations: list[LocationObservation] = []
        for feature in data.get("features", []):
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            coordinates = geometry.get("coordinates")
            if geometry.get("type") == "Point":
                observations.extend(_point_observations(coordinates, properties, feature))
            elif geometry.get("type") == "LineString":
                for point in coordinates or []:
                    observations.extend(_point_observations(point, properties, feature))
        return ParseResult(
            source_type=self.source_type,
            detected_schema="geojson_points",
            parser_version=self.parser_version,
            observations=observations,
        )


def _point_observations(
    coordinates: Any,
    properties: dict[str, Any],
    source: dict[str, Any],
) -> list[LocationObservation]:
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return []
    longitude = float(coordinates[0])
    latitude = float(coordinates[1])
    if not is_valid_coordinate(latitude, longitude):
        return []
    return [
        LocationObservation(
            source_type="geojson",
            source_record_type="point",
            source_record_hash=stable_record_hash(source),
            observed_at_utc=parse_datetime(properties.get("timestamp") or properties.get("time")),
            latitude=latitude,
            longitude=longitude,
            accuracy_m=_float_or_none(properties.get("accuracy_m")),
            activity_type=properties.get("activity_type"),
        )
    ]


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
