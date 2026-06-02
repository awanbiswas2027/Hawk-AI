"""Verify GpsTelemetry properties, conversions, and protocol contracts."""
from collections.abc import Iterator
from datetime import UTC, datetime

from hawk_edge.gps.types import GpsProvider, GpsTelemetry


def test_gps_telemetry_properties():
    """Verify units conversions for speed and basic coordinate formatting."""
    timestamp = datetime.now(UTC)
    tel = GpsTelemetry(
        latitude=12.9784,
        longitude=77.6408,
        altitude=920.0,
        speed_mps=10.0,  # 10 m/s = 36 km/h, ~19.43 knots
        bearing=180.0,
        timestamp=timestamp,
        hdop=1.2,
        num_satellites=10,
        fix_quality=1,
    )

    assert tel.latitude == 12.9784
    assert tel.longitude == 77.6408
    assert tel.altitude == 920.0
    assert tel.bearing == 180.0
    assert tel.timestamp == timestamp
    assert tel.hdop == 1.2
    assert tel.num_satellites == 10
    assert tel.fix_quality == 1

    # Speed assertions
    assert abs(tel.speed_kmh - 36.0) < 1e-5
    assert abs(tel.speed_knots - 19.4384) < 1e-5


def test_gps_provider_protocol():
    """Verify that a class implementing GpsProvider satisfies static typing."""

    class MockGpsProvider(GpsProvider):
        def get_telemetry(self) -> GpsTelemetry | None:
            return None

        def __iter__(self) -> Iterator[GpsTelemetry]:
            return iter([])

    provider: GpsProvider = MockGpsProvider()
    assert provider.get_telemetry() is None
