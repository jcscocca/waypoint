from app.routing.place_resolver import UnknownRoutePlaceError, resolve_route_place


def test_resolve_route_place_supports_aliases_and_display_coordinates():
    place = resolve_route_place("Capitol Hill")
    alias_place = resolve_route_place("cap hill")

    assert place.label == "Capitol Hill"
    assert place.location_type == "neighborhood"
    assert round(place.latitude, 3) == 47.623
    assert round(place.longitude, 3) == -122.321
    assert place.display_latitude is not None
    assert place.display_longitude is not None
    assert alias_place.label == "Capitol Hill"
    assert alias_place.display_latitude == place.display_latitude
    assert alias_place.display_longitude == place.display_longitude


def test_resolve_route_place_rejects_unknown_places():
    try:
        resolve_route_place("Not A Seattle Place")
    except UnknownRoutePlaceError as exc:
        assert "Unknown route place" in str(exc)
    else:
        raise AssertionError("Expected UnknownRoutePlaceError")
