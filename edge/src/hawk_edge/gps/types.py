"""Type definitions and interfaces for GPS telemetry."""
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GpsTelemetry:
    """Complete GPS telemetry matching NMEA $GPRMC + $GPGGA field requirements."""

    latitude: float  # Decimal degrees, WGS84
    longitude: float  # Decimal degrees, WGS84
    altitude: float  # Meters above mean sea level
    speed_mps: float  # Meters per second (SI unit)
    bearing: float  # Degrees true north, 0.0 - 359.99
    timestamp: datetime  # UTC datetime
    hdop: float  # Horizontal Dilution of Precision
    num_satellites: int  # Number of satellites visible
    fix_quality: int  # 0 = invalid, 1 = GPS fix, 2 = DGPS

    @property
    def speed_knots(self) -> float:
        """Speed in knots for NMEA generation."""
        return self.speed_mps * 1.94384

    @property
    def speed_kmh(self) -> float:
        """Speed in km/h for display and databases."""
        return self.speed_mps * 3.6


class GpsProvider(Protocol):
    """Interface contract shared between GPS sensors and emulators."""

    def get_telemetry(self) -> GpsTelemetry | None:
        """Fetch the most recent GPS telemetry reading."""
        ...

    def __iter__(self) -> Iterator[GpsTelemetry]:
        """Support iterating over stream coordinates."""
        ...
