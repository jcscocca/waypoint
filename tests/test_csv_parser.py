from pathlib import Path

from app.parsers.csv_points import CsvPointsParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_parser_reads_canonical_points():
    parser = CsvPointsParser()
    result = parser.parse_bytes((FIXTURES / "stop_points.csv").read_bytes(), "stop_points.csv")

    assert result.detected_schema == "csv_points"
    assert len(result.observations) == 4
    assert result.observations[0].observed_at_utc.isoformat() == "2024-01-02T08:00:00+00:00"
    assert result.observations[0].accuracy_m == 10
    assert result.observations[0].activity_type == "still"
