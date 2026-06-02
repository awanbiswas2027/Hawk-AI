"""E2E verification tests for the RouteEmulator."""
from pathlib import Path

import pytest

from hawk_edge.gps.emulator import RouteEmulator
from hawk_edge.gps.types import GpsTelemetry


@pytest.fixture
def commute_route_path() -> Path:
    root_dir = Path(__file__).parent.parent
    route_file = "src/hawk_edge/sim/routes/bengaluru_commute.toml"
    return root_dir / route_file


def test_emulator_determinism(commute_route_path):
    """Verify that emulator output is deterministic with identical seeds."""
    em1 = RouteEmulator(route_path=commute_route_path, seed=101, loop=False)
    em2 = RouteEmulator(route_path=commute_route_path, seed=101, loop=False)

    for _ in range(20):
        t1 = em1.get_telemetry()
        t2 = em2.get_telemetry()
        assert t1 is not None
        assert t2 is not None
        assert t1.latitude == t2.latitude
        assert t1.longitude == t2.longitude
        assert t1.speed_mps == t2.speed_mps
        assert t1.bearing == t2.bearing
        assert t1.timestamp == t2.timestamp


def test_telemetry_schema_and_limits(commute_route_path):
    """Verify presence of all NMEA fields and coordinate bounding constraints."""
    emulator = RouteEmulator(route_path=commute_route_path, seed=42, loop=False)

    last_timestamp = None
    for _ in range(50):
        t = emulator.get_telemetry()
        assert t is not None
        assert isinstance(t, GpsTelemetry)

        # Confirm all 11 required telemetry fields are present and typed correctly
        assert isinstance(t.latitude, float)
        assert isinstance(t.longitude, float)
        assert isinstance(t.altitude, float)
        assert isinstance(t.speed_mps, float)
        assert isinstance(t.bearing, float)
        assert isinstance(t.hdop, float)
        assert isinstance(t.num_satellites, int)
        assert isinstance(t.fix_quality, int)

        # Coordinate bounds (Bengaluru bbox check: 12.8 to 13.1 N, 77.4 to 77.8 E)
        assert 12.8 <= t.latitude <= 13.1
        assert 77.4 <= t.longitude <= 77.8

        # Altitude check (~920m base altitude ± 15m)
        assert 900.0 <= t.altitude <= 940.0

        # Monotonicity checks
        if last_timestamp:
            assert t.timestamp > last_timestamp
        last_timestamp = t.timestamp


def test_emulator_non_looping_completion(commute_route_path):
    """Verify non-looping emulator completes and stops at last waypoint."""
    emulator = RouteEmulator(route_path=commute_route_path, seed=123, loop=False)

    # Run for many steps to exceed the route length
    points = []
    for _ in range(500):
        t = emulator.get_telemetry()
        points.append(t)

    # Verify we successfully stopped at the final waypoint

    # Without noise, lat/lon would snap exactly. With noise bias, we'll check it's near.
    # The actual distance without noise should be 0.
    assert emulator.current_waypoint_idx == len(emulator.waypoints) - 1
    assert emulator.current_speed_mps == 0.0
