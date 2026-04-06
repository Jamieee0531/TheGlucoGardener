"""
Integration tests for Google Maps Places API.

These tests make real HTTP calls — run them manually to verify API connectivity.
They are excluded from the default test suite via the `integration` mark.

Run with:
    pytest task_agent/tests/test_map_api.py -v -s -m integration
"""
import pytest
from task_agent.agent.map_tool import find_nearby_parks


@pytest.mark.asyncio
@pytest.mark.integration
async def test_find_parks_bishan():
    """
    Given Bishan GPS (Auntie Lin's home), expect ≥1 real park from Google Maps.
    Verifies: API key works, results are real (not fallback), distance > 0.
    """
    parks = await find_nearby_parks(db=None, lat=1.3526, lng=103.8352, user_id="test")

    print("\nParks returned:")
    for p in parks:
        print(f"  {p['name']} — {p['distance_m']}m  ({p['lat']:.4f}, {p['lng']:.4f})")

    assert len(parks) >= 1, "Expected at least 1 park"
    assert parks[0]["name"] != "Fallback Park", "Got fallback — check API key or quota"
    for p in parks:
        assert p["distance_m"] > 0, f"Fallback park has distance_m=0: {p}"
        assert "lat" in p and "lng" in p


@pytest.mark.asyncio
@pytest.mark.integration
async def test_find_parks_cbd():
    """
    Given Marina Bay CBD coordinates, expect real parks (Gardens by the Bay area).
    Verifies the API works for a different area of Singapore.
    """
    parks = await find_nearby_parks(db=None, lat=1.2838, lng=103.8511, user_id="test")

    print("\nParks returned:")
    for p in parks:
        print(f"  {p['name']} — {p['distance_m']}m")

    assert len(parks) >= 1
    assert parks[0]["name"] != "Fallback Park"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_returns_at_most_3_parks():
    """Result is capped at 3 parks regardless of how many Google returns."""
    parks = await find_nearby_parks(db=None, lat=1.3526, lng=103.8352, user_id="test")
    assert len(parks) <= 3
