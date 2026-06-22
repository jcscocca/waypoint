# Three Input Modes Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three supported input modes and dashboard summary APIs so community users can use personal timelines, generalized recurring places, or public commute scenarios.

**Architecture:** Extend the existing parser/service pipeline instead of creating a parallel dashboard pipeline. Personal timeline inputs continue through staging observations and normalization; generalized recurring-place and public commute scenario CSV inputs create generalized `PlaceCluster` rows directly through an import service boundary. New metadata and dashboard routes expose frontend-ready mode descriptions and dashboard summaries.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, ruff.

---

## File Structure

- Create `app/input_modes.py`: returns metadata for the three input modes and sample CSV snippets.
- Create `app/parsers/recurring_places.py`: parses generalized recurring-place CSV rows into `DirectPlaceClusterInput`.
- Create `app/parsers/commute_scenario.py`: parses public commute scenario CSV rows into `DirectPlaceClusterInput` rows using a Seattle area fixture.
- Create `app/services/direct_places_service.py`: persists direct generalized place clusters for Mode 2 and Mode 3 imports.
- Create `app/services/dashboard_service.py`: builds dashboard-ready summaries for the current demo user.
- Create `app/api/routes_input_modes.py`: serves `GET /input-modes`.
- Create `app/api/routes_dashboard.py`: serves `GET /dashboard/summary`.
- Modify `app/schemas.py`: add `DirectPlaceClusterInput` and `DirectPlaceImportResult`.
- Modify `app/services/import_service.py`: detect direct place parsers, create `ImportBatch`, and persist clusters directly.
- Modify `app/main.py`: include new routers.
- Modify `README.md`: document the three input modes.
- Add fixtures under `tests/fixtures/`.
- Add tests in `tests/test_input_modes.py`, `tests/test_recurring_places_parser.py`, `tests/test_commute_scenario_parser.py`, and `tests/test_dashboard_summary.py`.

### Task 1: Input Mode Metadata

**Files:**
- Create: `app/input_modes.py`
- Create: `app/api/routes_input_modes.py`
- Modify: `app/main.py`
- Test: `tests/test_input_modes.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_input_modes_endpoint_describes_all_three_modes(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    client = TestClient(app)

    response = client.get("/input-modes")

    assert response.status_code == 200
    payload = response.json()
    ids = [mode["id"] for mode in payload["modes"]]
    assert ids == ["personal_timeline", "recurring_places_csv", "public_commute_scenario"]
    recurring = payload["modes"][1]
    assert recurring["privacy_level"] == "low"
    assert "display_label" in recurring["required_columns"]
    assert "latitude" in recurring["sample_csv"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_input_modes.py -q`

Expected: FAIL with `ModuleNotFoundError` or 404 because `/input-modes` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `app/input_modes.py`:

```python
from __future__ import annotations


def supported_input_modes() -> list[dict[str, object]]:
    return [
        {
            "id": "personal_timeline",
            "label": "Personal timeline upload",
            "privacy_level": "high",
            "description": "Google Timeline JSON, raw point CSV, GeoJSON, or GPX.",
            "required_columns": [],
            "optional_columns": [],
            "sample_csv": "",
        },
        {
            "id": "recurring_places_csv",
            "label": "Generalized recurring places CSV",
            "privacy_level": "low",
            "description": "Upload only recurring places or areas to analyze.",
            "required_columns": ["display_label", "latitude", "longitude"],
            "optional_columns": [
                "visit_count",
                "total_dwell_minutes",
                "median_dwell_minutes",
                "typical_days",
                "typical_hours",
                "sensitivity_class",
            ],
            "sample_csv": (
                "display_label,latitude,longitude,visit_count,total_dwell_minutes\\n"
                "Downtown transfer stop,47.609,-122.333,12,360\\n"
            ),
        },
        {
            "id": "public_commute_scenario",
            "label": "Public commute scenario",
            "privacy_level": "very_low",
            "description": "Model a commute using generalized Seattle areas.",
            "required_columns": ["origin_area", "destination_area", "mode"],
            "optional_columns": ["usual_departure_time", "frequency_per_week"],
            "sample_csv": (
                "origin_area,destination_area,mode,usual_departure_time,frequency_per_week\\n"
                "Capitol Hill,Downtown Seattle,transit,08:00,4\\n"
            ),
        },
    ]
```

Implement `app/api/routes_input_modes.py`:

```python
from __future__ import annotations

from fastapi import APIRouter

from app.input_modes import supported_input_modes

router = APIRouter()


@router.get("/input-modes")
def input_modes() -> dict[str, object]:
    return {"modes": supported_input_modes()}
```

Modify `app/main.py` to import and include the router:

```python
from app.api.routes_input_modes import router as input_modes_router

app.include_router(input_modes_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_input_modes.py -q`

Expected: PASS.

### Task 2: Generalized Recurring Places CSV

**Files:**
- Create: `app/parsers/recurring_places.py`
- Modify: `app/schemas.py`
- Modify: `app/services/import_service.py`
- Create: `app/services/direct_places_service.py`
- Create: `tests/fixtures/recurring_places.csv`
- Test: `tests/test_recurring_places_parser.py`

- [ ] **Step 1: Write the failing parser and import test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.parsers.recurring_places import RecurringPlacesParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_recurring_places_parser_creates_direct_place_inputs():
    result = RecurringPlacesParser().parse_bytes(
        (FIXTURES / "recurring_places.csv").read_bytes(),
        "recurring_places.csv",
    )

    assert result.detected_schema == "recurring_places_csv"
    assert len(result.direct_place_clusters) == 2
    assert result.direct_place_clusters[0].display_label == "Downtown transfer stop"
    assert result.direct_place_clusters[0].visit_count == 12
    assert result.direct_place_clusters[0].display_latitude == 47.609


def test_recurring_places_upload_creates_places_without_normalize(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    client = TestClient(app)

    response = client.post(
        "/imports",
        headers={"X-Demo-User-Id": "demo@example.com"},
        files={
            "file": (
                "recurring_places.csv",
                (FIXTURES / "recurring_places.csv").read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["detected_schema"] == "recurring_places_csv"
    assert response.json()["place_cluster_count"] == 2

    places = client.get("/places", headers={"X-Demo-User-Id": "demo@example.com"})
    assert places.json()["count"] == 2
```

Fixture `tests/fixtures/recurring_places.csv`:

```csv
display_label,latitude,longitude,visit_count,total_dwell_minutes,median_dwell_minutes,typical_days,typical_hours,sensitivity_class
Downtown transfer stop,47.609,-122.333,12,360,30,weekday,8-9,normal
Library area,47.621,-122.321,6,420,70,weekend,afternoon,normal
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_recurring_places_parser.py -q`

Expected: FAIL because `app.parsers.recurring_places` and direct-place support do not exist.

- [ ] **Step 3: Implement minimal schema/parser/service support**

Add to `app/schemas.py`:

```python
class DirectPlaceClusterInput(BaseModel):
    source_type: str
    display_label: str
    latitude: float
    longitude: float
    display_latitude: float | None = None
    display_longitude: float | None = None
    visit_count: int = 1
    total_dwell_minutes: float | None = None
    median_dwell_minutes: float | None = None
    dominant_days: str | None = None
    dominant_hours: str | None = None
    inferred_place_type: str = "unknown"
    sensitivity_class: str = "normal"
    source_record_hash: str | None = None


class DirectPlaceImportResult(BaseModel):
    source_type: str
    detected_schema: str
    parser_version: str
    direct_place_clusters: list[DirectPlaceClusterInput] = Field(default_factory=list)
```

Implement `RecurringPlacesParser` with `can_parse()` checking CSV headers for
`display_label`, `latitude`, and `longitude`, and `parse_bytes()` returning a
`DirectPlaceImportResult`.

Implement `direct_places_service.persist_direct_place_import()` to create an `ImportBatch`
and `PlaceCluster` rows with display coordinates rounded to three decimals when absent.

Update `import_service.create_import_batch()` to try direct place parsers before observation
parsers and return `place_cluster_count`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_recurring_places_parser.py -q`

Expected: PASS.

### Task 3: Public Commute Scenario CSV

**Files:**
- Create: `app/parsers/commute_scenario.py`
- Create: `app/data/seattle_area_centroids.py`
- Modify: `app/services/import_service.py`
- Create: `tests/fixtures/commute_scenario.csv`
- Test: `tests/test_commute_scenario_parser.py`

- [ ] **Step 1: Write the failing parser and import test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.parsers.commute_scenario import CommuteScenarioParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_commute_scenario_parser_resolves_seattle_area_fixture():
    result = CommuteScenarioParser().parse_bytes(
        (FIXTURES / "commute_scenario.csv").read_bytes(),
        "commute_scenario.csv",
    )

    assert result.detected_schema == "public_commute_scenario_csv"
    labels = [place.display_label for place in result.direct_place_clusters]
    assert labels == ["Capitol Hill origin area", "Downtown Seattle destination area"]
    assert result.direct_place_clusters[0].source_type == "public_commute_scenario"


def test_commute_scenario_upload_creates_dashboard_places(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    client = TestClient(app)

    response = client.post(
        "/imports",
        headers={"X-Demo-User-Id": "demo@example.com"},
        files={
            "file": (
                "commute_scenario.csv",
                (FIXTURES / "commute_scenario.csv").read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["detected_schema"] == "public_commute_scenario_csv"
    assert response.json()["place_cluster_count"] == 2
```

Fixture `tests/fixtures/commute_scenario.csv`:

```csv
origin_area,destination_area,mode,usual_departure_time,frequency_per_week
Capitol Hill,Downtown Seattle,transit,08:00,4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_commute_scenario_parser.py -q`

Expected: FAIL because `app.parsers.commute_scenario` does not exist.

- [ ] **Step 3: Implement minimal parser and area fixture**

Implement `app/data/seattle_area_centroids.py`:

```python
SEATTLE_AREA_CENTROIDS = {
    "capitol hill": (47.623, -122.320),
    "downtown seattle": (47.609, -122.333),
    "rainier valley": (47.548, -122.289),
    "university district": (47.661, -122.313),
}
```

Implement `CommuteScenarioParser` with `can_parse()` checking CSV headers for
`origin_area`, `destination_area`, and `mode`. `parse_bytes()` should create origin and
destination `DirectPlaceClusterInput` rows from the fixture. Use `visit_count` from
`frequency_per_week` when present and `sensitivity_class="normal"`.

Register the parser in `import_service.DIRECT_PLACE_PARSERS`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_commute_scenario_parser.py -q`

Expected: PASS.

### Task 4: Dashboard Summary API

**Files:**
- Create: `app/services/dashboard_service.py`
- Create: `app/api/routes_dashboard.py`
- Modify: `app/main.py`
- Test: `tests/test_dashboard_summary.py`

- [ ] **Step 1: Write the failing dashboard summary test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


def test_dashboard_summary_returns_places_totals_privacy_and_exports(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    client = TestClient(app)
    headers = {"X-Demo-User-Id": "demo@example.com"}

    client.post(
        "/imports",
        headers=headers,
        files={
            "file": (
                "recurring_places.csv",
                (FIXTURES / "recurring_places.csv").read_bytes(),
                "text/csv",
            )
        },
    )
    client.post("/crime/ingest/sample")
    client.post(
        "/crime/summarize",
        headers=headers,
        json={
            "analysis_start_date": "2024-01-01",
            "analysis_end_date": "2024-01-31",
            "radii_m": [250],
        },
    )

    response = client.get("/dashboard/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["place_count"] == 2
    assert payload["privacy"]["normal"] == 2
    assert payload["exports"]["tableau_place_summary_csv"].endswith(
        "/exports/tableau/place-summary.csv"
    )
    assert payload["places"][0]["display_label"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_dashboard_summary.py -q`

Expected: FAIL because `/dashboard/summary` does not exist.

- [ ] **Step 3: Implement minimal dashboard service and route**

Implement `dashboard_service.dashboard_summary()` to query user `PlaceCluster` rows and
`PlaceCrimeSummary` rows. Return:

```python
{
    "totals": {"place_count": int, "visit_count": int, "incident_count": int},
    "privacy": {"normal": int, "home_candidate": int, "work_candidate": int},
    "places": [...],
    "crime_summaries": [...],
    "analysis": {"available_radii_m": settings.crime_radii_m},
    "exports": {"tableau_place_summary_csv": "/exports/tableau/place-summary.csv"},
}
```

Implement `routes_dashboard.py` and include it in `app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_dashboard_summary.py -q`

Expected: PASS.

### Task 5: Tableau Export Compatibility And Docs

**Files:**
- Modify: `README.md`
- Test: `tests/test_tableau_export.py`

- [ ] **Step 1: Add a failing compatibility test**

Extend `tests/test_tableau_export.py` with:

```python
def test_tableau_export_accepts_direct_input_mode_clusters():
    cluster = PlaceClusterData(
        id="scenario-cluster",
        user_id_hash="user-hash",
        cluster_version="direct-1",
        cluster_method="direct_user_input",
        centroid_latitude=47.609,
        centroid_longitude=-122.333,
        display_latitude=47.609,
        display_longitude=-122.333,
        cluster_radius_m=100,
        visit_count=4,
        total_dwell_minutes=None,
        median_dwell_minutes=None,
        display_label="Downtown Seattle destination area",
    )

    csv_text = build_place_summary_csv([cluster], [], tableau_safe=True)

    assert "Downtown Seattle destination area" in csv_text
    assert "scenario-cluster" in csv_text
```

- [ ] **Step 2: Run test to verify behavior**

Run: `.venv/bin/python -m pytest tests/test_tableau_export.py -q`

Expected: PASS if existing exporter already supports direct clusters. If it fails, adjust only
`app/exports/tableau.py` to support nullable dwell values.

- [ ] **Step 3: Update README**

Add a "Three input modes" section documenting the personal timeline, recurring places CSV, and
public commute scenario CSV formats.

- [ ] **Step 4: Run full verification**

Run:

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check .
```

Expected: all tests and lint pass.
