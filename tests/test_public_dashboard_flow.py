from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db import get_sessionmaker
from app.main import create_app
from app.models import CrimeIncident


def test_public_dashboard_flow_without_uploads(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    client = TestClient(app)
    client.post("/sessions")

    input_modes = client.get("/input-modes").json()["modes"]
    assert "personal_timeline" not in [mode["id"] for mode in input_modes]

    session = get_sessionmaker()()
    session.add(
        CrimeIncident(
            id="public-flow-incident",
            offense_start_utc=datetime(2024, 1, 10, tzinfo=UTC),
            offense_category="PROPERTY",
            latitude=47.609,
            longitude=-122.333,
        )
    )
    session.commit()
    session.close()

    create_response = client.post(
        "/places",
        json={
            "display_label": "Downtown transfer stop",
            "latitude": 47.609,
            "longitude": -122.333,
            "visit_count": 12,
        },
    )
    assert create_response.status_code == 201
    place_id = create_response.json()["id"]

    analyze_response = client.post(
        "/dashboard/analyze",
        json={
            "place_ids": [place_id],
            "analysis_start_date": "2024-01-01",
            "analysis_end_date": "2024-01-31",
            "radii_m": [250],
            "offense_category": "PROPERTY",
        },
    )
    assert analyze_response.status_code == 200
    assert analyze_response.json()["summary_count"] == 1

    summary = client.get("/dashboard/summary").json()
    assert summary["totals"]["place_count"] == 1
    assert summary["totals"]["incident_count"] == 1

    export_response = client.get("/exports/tableau/place-summary.csv")
    assert export_response.status_code == 200
    assert "Downtown transfer stop" in export_response.text
