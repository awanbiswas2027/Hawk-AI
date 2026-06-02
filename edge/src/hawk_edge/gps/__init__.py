"""Hawk-AI GPS Submodule."""
from hawk_edge.gps.daemon import GpsDaemon
from hawk_edge.gps.nmea import telemetry_to_gpgga, telemetry_to_gprmc
from hawk_edge.gps.types import GpsProvider, GpsTelemetry

__all__ = [
    "GpsTelemetry",
    "GpsProvider",
    "telemetry_to_gprmc",
    "telemetry_to_gpgga",
    "GpsDaemon",
]
