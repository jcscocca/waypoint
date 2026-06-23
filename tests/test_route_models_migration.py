from app.db import get_sessionmaker
from app.main import create_app
from app.models import RouteAlternative, RouteRequest, RouteSegment


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
