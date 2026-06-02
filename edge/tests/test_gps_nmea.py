"""Verify NMEA conversions, sentence structures, and pynmea2 parsing."""
from datetime import UTC, datetime

import pynmea2

from hawk_edge.gps.nmea import (
    calculate_nmea_checksum,
    decimal_degrees_to_nmea_lat,
    decimal_degrees_to_nmea_lon,
    telemetry_to_gpgga,
    telemetry_to_gprmc,
)
from hawk_edge.gps.types import GpsTelemetry


def test_coordinate_conversions():
    """Verify conversion of decimal degrees coordinates to NMEA degree-minutes."""
    # Test positive latitude (Northern hemisphere)
    lat_str, lat_dir = decimal_degrees_to_nmea_lat(12.9784)
    assert lat_str == "1258.7040"
    assert lat_dir == "N"

    # Test negative latitude (Southern hemisphere)
    lat_str, lat_dir = decimal_degrees_to_nmea_lat(-33.8688)
    assert lat_str == "3352.1280"
    assert lat_dir == "S"

    # Test longitude with leading zero padding (Eastern hemisphere)
    lon_str, lon_dir = decimal_degrees_to_nmea_lon(77.6408)
    assert lon_str == "07738.4480"
    assert lon_dir == "E"

    # Test negative longitude (Western hemisphere)
    lon_str, lon_dir = decimal_degrees_to_nmea_lon(-122.4194)
    assert lon_str == "12225.1640"
    assert lon_dir == "W"


def test_nmea_checksum():
    """Verify bitwise XOR checksum generation outputting 2-digit uppercase hex."""
    body = "GPRMC,123519.00,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W,A"
    checksum = calculate_nmea_checksum(body)
    assert checksum == "29"


def test_gprmc_generation_and_pynmea2_parsing():
    """Verify GPRMC sentence structure, max-length, and pynmea2 parse compatibility."""
    timestamp = datetime(2026, 6, 3, 14, 30, 5, tzinfo=UTC)
    tel = GpsTelemetry(
        latitude=12.9784,
        longitude=77.6408,
        altitude=920.0,
        speed_mps=8.33333,  # ~16.2 knots
        bearing=185.5,
        timestamp=timestamp,
        hdop=1.2,
        num_satellites=10,
        fix_quality=1,
    )

    sentence = telemetry_to_gprmc(tel)

    # NMEA structural constraints
    assert sentence.startswith("$GPRMC")
    assert sentence.endswith("\r\n")
    assert len(sentence) <= 82

    # Verify checksum separator
    assert "*" in sentence

    # Parse back using pynmea2
    msg = pynmea2.parse(sentence.strip())
    assert isinstance(msg, pynmea2.types.talker.RMC)

    # Assert parsed attributes match original telemetry coordinates
    assert abs(msg.latitude - tel.latitude) < 1e-4
    assert abs(msg.longitude - tel.longitude) < 1e-4
    assert msg.status == "A"
    assert abs(msg.spd_over_grnd - tel.speed_knots) < 0.1
    assert abs(msg.true_course - tel.bearing) < 0.1

    # Date/Time format checks
    assert msg.timestamp.hour == 14
    assert msg.timestamp.minute == 30
    assert msg.timestamp.second == 5
    assert msg.datestamp.day == 3
    assert msg.datestamp.month == 6


def test_gpgga_generation_and_pynmea2_parsing():
    """Verify GPGGA sentence structure, max-length, and pynmea2 parse compatibility."""
    timestamp = datetime(2026, 6, 3, 14, 30, 5, tzinfo=UTC)
    tel = GpsTelemetry(
        latitude=12.9784,
        longitude=77.6408,
        altitude=920.4,
        speed_mps=8.33333,
        bearing=185.5,
        timestamp=timestamp,
        hdop=1.2,
        num_satellites=10,
        fix_quality=1,
    )

    sentence = telemetry_to_gpgga(tel)

    assert sentence.startswith("$GPGGA")
    assert sentence.endswith("\r\n")
    assert len(sentence) <= 82

    # Parse back using pynmea2
    msg = pynmea2.parse(sentence.strip())
    assert isinstance(msg, pynmea2.types.talker.GGA)

    # Assert parsed attributes match original telemetry coordinates
    assert abs(msg.latitude - tel.latitude) < 1e-4
    assert abs(msg.longitude - tel.longitude) < 1e-4
    assert msg.gps_qual == 1
    assert msg.num_sats == "10"
    assert abs(float(msg.horizontal_dil) - tel.hdop) < 0.1
    assert abs(float(msg.altitude) - tel.altitude) < 0.1
    assert msg.altitude_units == "M"
