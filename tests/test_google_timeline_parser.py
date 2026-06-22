from pathlib import Path

from app.parsers.google_timeline import GoogleTimelineParser, google_e7_to_decimal

FIXTURES = Path(__file__).parent / "fixtures"


def test_google_e7_to_decimal_converts_signed_coordinates():
    assert google_e7_to_decimal(476095000) == 47.6095
    assert google_e7_to_decimal(-1223331000) == -122.3331


def test_google_semantic_place_visits_parse_as_source_stops():
    parser = GoogleTimelineParser()
    result = parser.parse_bytes((FIXTURES / "google_semantic.json").read_bytes(), "semantic.json")

    assert result.detected_schema == "google_semantic_location_history"
    assert len(result.source_stops) == 2
    assert result.source_stops[0].display_label == "Coffee Shop"
    assert result.source_stops[0].start_time_utc.isoformat() == "2024-01-02T15:00:00+00:00"
    assert result.source_stops[0].latitude == 47.60951
    assert result.source_stops[0].longitude == -122.33309
    assert any(obs.source_record_type == "activitySegment" for obs in result.observations)


def test_google_records_locations_parse_as_observations():
    parser = GoogleTimelineParser()
    result = parser.parse_bytes((FIXTURES / "google_records.json").read_bytes(), "Records.json")

    assert result.detected_schema == "google_records_locations"
    assert len(result.observations) == 2
    assert result.observations[0].latitude == 47.6095
    assert result.observations[0].longitude == -122.3331
    assert result.observations[0].activity_type == "STILL"
    assert result.observations[0].confidence_score == 85
