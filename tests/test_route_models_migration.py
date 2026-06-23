from datetime import date

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db import get_sessionmaker
from app.main import create_app
from app.models import RouteAlternative, RouteContextSummary, RouteRequest, RouteSegment


def test_route_models_persist_with_relationship_ids(tmp_path):
    create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    session = get_sessionmaker()()

    request = RouteRequest(
        user_id_hash="route-user",
        origin_label="Capitol Hill",
        origin_latitude=47.623,
        origin_longitude=-122.321,
        destination_label="Downtown Seattle",
        destination_latitude=47.609,
        destination_longitude=-122.335,
        mode="transit",
        provider="mock",
        privacy_level="generalized",
        status="ready",
    )
    session.add(request)
    session.flush()

    alternative = RouteAlternative(
        route_request_id=request.id,
        user_id_hash="route-user",
        provider_route_id="mock-1",
        route_label="Transit via Westlake",
        rank=1,
        duration_minutes=18,
        distance_m=2500,
        transfer_count=0,
        walking_distance_m=600,
        mode_mix="walk,transit",
        provider="mock",
    )
    session.add(alternative)
    session.flush()

    segment = RouteSegment(
        route_alternative_id=alternative.id,
        user_id_hash="route-user",
        sequence=1,
        segment_type="access",
        mode="walk",
        start_label="Capitol Hill",
        start_latitude=47.623,
        start_longitude=-122.321,
        end_label="Capitol Hill Station",
        end_latitude=47.619,
        end_longitude=-122.321,
    )
    session.add(segment)
    session.commit()

    assert request.id
    assert alternative.route_request_id == request.id
    assert segment.route_alternative_id == alternative.id

    session.close()


def test_route_context_summary_persists_for_segment(tmp_path):
    create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    session = get_sessionmaker()()

    request = RouteRequest(
        user_id_hash="route-user",
        origin_label="Capitol Hill",
        origin_latitude=47.623,
        origin_longitude=-122.321,
        destination_label="Downtown Seattle",
        destination_latitude=47.609,
        destination_longitude=-122.335,
        mode="transit",
    )
    session.add(request)
    session.flush()

    alternative = RouteAlternative(
        route_request_id=request.id,
        user_id_hash="route-user",
        provider_route_id="mock-1",
        route_label="Transit via Westlake",
        rank=1,
        mode_mix="walk,transit",
    )
    session.add(alternative)
    session.flush()

    segment = RouteSegment(
        route_alternative_id=alternative.id,
        user_id_hash="route-user",
        sequence=1,
        segment_type="access",
        mode="walk",
        start_label="Capitol Hill",
        start_latitude=47.623,
        start_longitude=-122.321,
        end_label="Capitol Hill Station",
        end_latitude=47.619,
        end_longitude=-122.321,
    )
    session.add(segment)
    session.flush()

    summary = RouteContextSummary(
        user_id_hash="route-user",
        route_alternative_id=alternative.id,
        route_segment_id=segment.id,
        context_label="Capitol Hill Station access",
        context_type="segment",
        radius_m=250,
        analysis_start_date=date(2026, 1, 1),
        analysis_end_date=date(2026, 1, 31),
        incident_count=2,
        nearest_incident_m=95.5,
        incidents_per_route=2.0,
    )
    session.add(summary)
    session.commit()

    assert summary.id
    assert summary.route_alternative_id == alternative.id
    assert summary.route_segment_id == segment.id

    session.close()


def test_sqlite_foreign_keys_reject_orphan_route_alternatives(tmp_path):
    create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'mca.sqlite3'}")
    session = get_sessionmaker()()

    session.add(
        RouteAlternative(
            route_request_id="missing",
            user_id_hash="route-user",
            provider_route_id="mock-1",
            route_label="Transit via Westlake",
            rank=1,
            mode_mix="walk,transit",
        ),
    )

    with pytest.raises(IntegrityError):
        session.commit()

    session.close()


def test_route_alembic_migration_creates_tables_columns_fks_and_indexes(tmp_path, monkeypatch):
    db_path = tmp_path / "route-migration.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("MCA_DATABASE_URL", database_url)

    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert {
        "route_requests",
        "route_alternatives",
        "route_segments",
        "route_context_summaries",
    }.issubset(set(inspector.get_table_names()))

    request_columns = {column["name"] for column in inspector.get_columns("route_requests")}
    assert {
        "id",
        "user_id_hash",
        "origin_label",
        "destination_label",
        "preferences_json",
        "analysis_start_date",
        "analysis_end_date",
        "radii_m_json",
        "created_at",
    }.issubset(request_columns)

    alternative_columns = {
        column["name"] for column in inspector.get_columns("route_alternatives")
    }
    assert {
        "route_request_id",
        "user_id_hash",
        "summary_geometry",
        "provider_metadata_json",
    }.issubset(alternative_columns)

    segment_columns = {column["name"] for column in inspector.get_columns("route_segments")}
    assert {"route_alternative_id", "user_id_hash", "geometry"}.issubset(segment_columns)

    context_columns = {
        column["name"] for column in inspector.get_columns("route_context_summaries")
    }
    assert {
        "route_alternative_id",
        "route_segment_id",
        "user_id_hash",
        "incidents_per_route",
    }.issubset(context_columns)

    alternative_fks = inspector.get_foreign_keys("route_alternatives")
    assert any(fk["referred_table"] == "route_requests" for fk in alternative_fks)

    segment_fks = inspector.get_foreign_keys("route_segments")
    assert any(fk["referred_table"] == "route_alternatives" for fk in segment_fks)

    context_fks = inspector.get_foreign_keys("route_context_summaries")
    assert {fk["referred_table"] for fk in context_fks} == {
        "route_alternatives",
        "route_segments",
    }

    request_indexes = {index["name"] for index in inspector.get_indexes("route_requests")}
    assert "ix_route_requests_user_id_hash" in request_indexes

    alternative_indexes = {
        index["name"] for index in inspector.get_indexes("route_alternatives")
    }
    assert "ix_route_alternatives_route_request_id" in alternative_indexes
    assert "ix_route_alternatives_user_id_hash" in alternative_indexes

    context_indexes = {
        index["name"] for index in inspector.get_indexes("route_context_summaries")
    }
    assert "ix_route_context_summaries_route_alternative_id" in context_indexes
    assert "ix_route_context_summaries_route_segment_id" in context_indexes
    assert "ix_route_context_summaries_user_id_hash" in context_indexes
