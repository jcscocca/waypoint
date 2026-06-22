from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.parsers.base import parse_datetime
from app.schemas import CrimeIncidentData


class SeattleSocrataClient:
    def __init__(self, base_url: str, dataset_id: str, app_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.dataset_id = dataset_id
        self.app_token = app_token

    def fetch_page(self, limit: int = 5000, offset: int = 0) -> list[CrimeIncidentData]:
        query = urlencode({"$limit": limit, "$offset": offset})
        request = Request(f"{self.base_url}/{self.dataset_id}.json?{query}")
        if self.app_token:
            request.add_header("X-App-Token", self.app_token)
        with urlopen(request, timeout=30) as response:
            rows = json.loads(response.read().decode("utf-8"))
        return [crime_incident_from_mapping(row) for row in rows]


def load_crime_csv(path: Path) -> list[CrimeIncidentData]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [crime_incident_from_mapping(row) for row in reader]


def load_crime_csv_text(text: str) -> list[CrimeIncidentData]:
    reader = csv.DictReader(StringIO(text))
    return [crime_incident_from_mapping(row) for row in reader]


def crime_incident_from_mapping(row: dict[str, Any]) -> CrimeIncidentData:
    offense_id = _first(row, "offense_id", "offense")
    report_number = _first(row, "report_number", "report_num")
    latitude = _float_or_none(_first(row, "latitude", "lat", "y"))
    longitude = _float_or_none(_first(row, "longitude", "lon", "lng", "x"))
    return CrimeIncidentData(
        external_incident_id=offense_id or report_number,
        report_number=report_number,
        offense_id=offense_id,
        offense_start_utc=parse_datetime(
            _first(row, "offense_start_datetime", "offense_start_utc", "offense_start")
        ),
        offense_end_utc=parse_datetime(
            _first(row, "offense_end_datetime", "offense_end_utc", "offense_end")
        ),
        report_utc=parse_datetime(_first(row, "report_datetime", "report_utc")),
        offense_category=_first(row, "crime_against_category", "offense_category"),
        offense_subcategory=_first(row, "offense_parent_group", "offense_subcategory", "offense"),
        nibrs_group=_first(row, "nibrs_group", "nibrs_group_a_b"),
        precinct=_first(row, "precinct"),
        sector=_first(row, "sector"),
        beat=_first(row, "beat"),
        mcpp=_first(row, "mcpp"),
        block_address=_first(row, "100_block_address", "block_address"),
        latitude=latitude,
        longitude=longitude,
        snapshot_at=parse_datetime(_first(row, "snapshot_at"))
        or parse_datetime("2024-01-01T00:00:00Z"),
    )


def _first(row: dict[str, Any], *keys: str) -> Any:
    lowered = {key.lower(): value for key, value in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
