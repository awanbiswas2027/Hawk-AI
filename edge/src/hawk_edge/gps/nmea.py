"""Utilities for formatting GpsTelemetry data into standard NMEA sentences."""
from datetime import UTC

from hawk_edge.gps.types import GpsTelemetry


def decimal_degrees_to_nmea_lat(dd: float) -> tuple[str, str]:
    """Convert decimal degrees latitude to NMEA degree-minutes format (DDMM.MMMM).

    Returns:
        Tuple of (formatted_string, direction_indicator).
    """
    direction = "N" if dd >= 0 else "S"
    dd = abs(dd)
    degrees = int(dd)
    minutes = (dd - degrees) * 60.0
    return f"{degrees:02d}{minutes:07.4f}", direction


def decimal_degrees_to_nmea_lon(dd: float) -> tuple[str, str]:
    """Convert decimal degrees longitude to NMEA degree-minutes format (DDDMM.MMMM).

    Returns:
        Tuple of (formatted_string, direction_indicator).
    """
    direction = "E" if dd >= 0 else "W"
    dd = abs(dd)
    degrees = int(dd)
    minutes = (dd - degrees) * 60.0
    return f"{degrees:03d}{minutes:07.4f}", direction


def calculate_nmea_checksum(sentence_body: str) -> str:
    """Calculate the NMEA-0183 2-digit uppercase hexadecimal XOR checksum."""
    val = 0
    for char in sentence_body:
        val ^= ord(char)
    return f"{val:02X}"


def telemetry_to_gprmc(t: GpsTelemetry, talker: str = "GP") -> str:
    """Format GpsTelemetry to a complete $xxRMC NMEA sentence."""
    # Format times: UTC HHMMSS.00
    time_str = t.timestamp.astimezone(UTC).strftime("%H%M%S.00")
    date_str = t.timestamp.astimezone(UTC).strftime("%d%m%y")

    status = "A" if t.fix_quality > 0 else "V"
    lat_str, lat_dir = decimal_degrees_to_nmea_lat(t.latitude)
    lon_str, lon_dir = decimal_degrees_to_nmea_lon(t.longitude)

    speed_knots = f"{t.speed_knots:.1f}"
    bearing = f"{t.bearing:.1f}"

    # Body contains: RMC,time,status,lat,N/S,lon,E/W,speed,bearing,date,mag_var,mag_dir,mode
    body = (
        f"{talker}RMC,{time_str},{status},{lat_str},{lat_dir},"
        f"{lon_str},{lon_dir},{speed_knots},{bearing},{date_str},,,A"
    )
    checksum = calculate_nmea_checksum(body)
    sentence = f"${body}*{checksum}\r\n"

    # NMEA specification requires max sentence length of 82 characters
    if len(sentence) > 82:
        raise ValueError(f"Generated RMC sentence too long: {len(sentence)} chars")

    return sentence


def telemetry_to_gpgga(t: GpsTelemetry, talker: str = "GP") -> str:
    """Format GpsTelemetry to a complete $xxGGA NMEA sentence."""
    time_str = t.timestamp.astimezone(UTC).strftime("%H%M%S.00")
    lat_str, lat_dir = decimal_degrees_to_nmea_lat(t.latitude)
    lon_str, lon_dir = decimal_degrees_to_nmea_lon(t.longitude)

    fix_quality = str(t.fix_quality)
    num_sats = f"{t.num_satellites:02d}"
    hdop = f"{t.hdop:.1f}"
    altitude = f"{t.altitude:.1f}"

    # Body contains: GGA,time,lat,N/S,lon,E/W,quality,sats,hdop,alt,M,geoid,M,dgps_age,dgps_id
    body = (
        f"{talker}GGA,{time_str},{lat_str},{lat_dir},{lon_str},{lon_dir},"
        f"{fix_quality},{num_sats},{hdop},{altitude},M,,M,,"
    )
    checksum = calculate_nmea_checksum(body)
    sentence = f"${body}*{checksum}\r\n"

    if len(sentence) > 82:
        raise ValueError(f"Generated GGA sentence too long: {len(sentence)} chars")

    return sentence
