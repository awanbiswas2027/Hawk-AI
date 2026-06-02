"""GPS Route Emulator implementing the GpsProvider interface."""
import json
import math
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from hawk_edge.gps.types import GpsProvider, GpsTelemetry
from hawk_edge.sim.noise import GpsNoiseModel
from hawk_edge.sim.speed_profile import TrafficStopModel, TrapezoidalSpeedProfile

EARTH_RADIUS_M = 6371000.0


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the bearing between two GPS coordinates in degrees."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    d_lon_r = math.radians(lon2 - lon1)

    y = math.sin(d_lon_r) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(
        d_lon_r
    )
    bearing_rad = math.atan2(y, x)
    return (math.degrees(bearing_rad) + 360.0) % 360.0


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance in meters between two GPS coordinates."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    d_lat_r = math.radians(lat2 - lat1)
    d_lon_r = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat_r / 2.0) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lon_r / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


def project_coordinate(
    lat: float, lon: float, distance_m: float, bearing_deg: float
) -> tuple[float, float]:
    """Project a coordinate along a bearing for a given distance."""
    lat_r = math.radians(lat)
    bearing_r = math.radians(bearing_deg)

    # Flat earth approximation for rapid/accurate small offsets
    d_lat = (distance_m * math.cos(bearing_r)) / EARTH_RADIUS_M
    d_lon = (distance_m * math.sin(bearing_r)) / (EARTH_RADIUS_M * math.cos(lat_r))

    return lat + math.degrees(d_lat), lon + math.degrees(d_lon)


class RouteEmulator(GpsProvider):
    """Simulates a vehicle's GPS receiver moving along a configured route."""

    def __init__(
        self,
        route_path: Path,
        seed: int | None = None,
        loop: bool = True,
        time_step: float = 1.0,
    ) -> None:
        """Initialize RouteEmulator.

        Args:
            route_path: Path to the TOML route configuration file.
            seed: Deterministic random seed for reproducibility.
            loop: Whether to loop back to the beginning of the route upon completion.
            time_step: Simulation tick rate in seconds (default 1.0s, matching 1Hz GPS).
        """
        self.route_path = route_path
        self.loop = loop
        self.dt = time_step

        # Load Route TOML
        with open(route_path, "rb") as f:
            data = tomllib.load(f)

        self.route_meta = data["route"]
        self.waypoints = data["route"]["waypoints"]

        if not self.waypoints:
            raise ValueError("Route must contain at least one waypoint.")

        # Setup Simulation Engine Components
        self.noise_model = GpsNoiseModel(seed=seed)
        self.speed_profile = TrapezoidalSpeedProfile()
        self.current_stop: TrafficStopModel | None = None

        # State Variables
        self.current_lat = self.waypoints[0]["lat"]
        self.current_lon = self.waypoints[0]["lon"]
        self.current_speed_mps = 0.0
        self.current_waypoint_idx = 0
        self.sim_time = datetime.now(UTC)

        # Pre-processed signal stops checklist to prevent stopping multiple times at same spot
        self.visited_stops: set[int] = set()

    def get_telemetry(self) -> GpsTelemetry | None:
        """Advance the emulator state by one step and return telemetry."""
        if len(self.waypoints) < 2:
            return self._build_telemetry(self.current_lat, self.current_lon, 0.0, 0.0)

        next_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
        # If not looping and we've reached the end
        if next_idx == 0 and self.current_waypoint_idx == len(self.waypoints) - 1 and not self.loop:
            if self.current_speed_mps > 0:
                # Decelerate to stop at final waypoint
                self.current_speed_mps = self.speed_profile.update(0.0, 0.0, self.dt)
            return self._build_telemetry(
                self.current_lat, self.current_lon, self.current_speed_mps, 0.0
            )

        target_wp = self.waypoints[next_idx]
        target_lat = target_wp["lat"]
        target_lon = target_wp["lon"]

        distance_to_wp = calculate_distance(
            self.current_lat, self.current_lon, target_lat, target_lon
        )
        bearing = calculate_bearing(self.current_lat, self.current_lon, target_lat, target_lon)

        # Route segment rules (speed limit, stop signals)
        speed_limit_mps = target_wp.get("speed_limit_kmh", 40.0) / 3.6
        has_signal = target_wp.get("has_signal", False)

        distance_to_stop: float | None = None
        if has_signal and next_idx not in self.visited_stops:
            distance_to_stop = distance_to_wp

        # Process active stops
        if self.current_stop and self.current_stop.active:
            is_stopped = self.current_stop.check_stop(self.current_speed_mps, self.dt)
            if is_stopped:
                self.current_speed_mps = 0.0
                return self._build_telemetry(self.current_lat, self.current_lon, 0.0, bearing)
            else:
                self.current_stop = None
                self.visited_stops.add(next_idx)

        # Update speed dynamically
        self.current_speed_mps = self.speed_profile.update(
            speed_limit_mps, distance_to_stop, self.dt
        )

        # Handle stopping trigger at signal
        if distance_to_stop is not None and self.current_speed_mps <= 0.05:
            self.current_stop = TrafficStopModel(stop_duration_s=15.0, active=True)
            self.current_speed_mps = 0.0
            return self._build_telemetry(self.current_lat, self.current_lon, 0.0, bearing)

        # Calculate coordinate advancement
        step_dist = self.current_speed_mps * self.dt

        if step_dist >= distance_to_wp and distance_to_wp > 0.0:
            # Snap to waypoint and advance
            self.current_lat = target_lat
            self.current_lon = target_lon
            self.current_waypoint_idx = next_idx
        else:
            # Linear projection along segment bearing
            self.current_lat, self.current_lon = project_coordinate(
                self.current_lat, self.current_lon, step_dist, bearing
            )

        return self._build_telemetry(
            self.current_lat, self.current_lon, self.current_speed_mps, bearing
        )

    def _build_telemetry(
        self, lat: float, lon: float, speed_mps: float, bearing: float
    ) -> GpsTelemetry:
        """Inject noise, increment clocks, and build the final GpsTelemetry model."""
        # Check canyon status based on speed limits (faster roads = flyovers = high noise)
        next_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
        target_wp = self.waypoints[next_idx]
        is_canyon = target_wp.get("speed_limit_kmh", 40.0) >= 50.0
        self.noise_model.adjust_for_canyon(is_canyon)

        # Add Ornstein-Uhlenbeck drift noise
        lat_bias, lon_bias, speed_bias = self.noise_model.step(self.dt)

        noisy_lat = lat + lat_bias
        noisy_lon = lon + lon_bias
        noisy_speed = max(0.0, speed_mps + speed_bias)

        # Simulated clock tick
        self.sim_time += timedelta(seconds=self.dt)

        # Simple elevation model: fluctuate base altitude with noise
        base_alt = self.route_meta.get("base_altitude_m", 920.0)
        noisy_alt = base_alt + (lat_bias * 1e5)  # scale coordinate noise to meters

        # Calculate NMEA metrics based on signal quality
        hdop = 3.5 if is_canyon else 1.2
        num_sats = 5 if is_canyon else 10
        fix_quality = 1 if num_sats >= 4 else 0

        return GpsTelemetry(
            latitude=noisy_lat,
            longitude=noisy_lon,
            altitude=noisy_alt,
            speed_mps=noisy_speed,
            bearing=bearing,
            timestamp=self.sim_time,
            hdop=hdop,
            num_satellites=num_sats,
            fix_quality=fix_quality,
        )

    def __iter__(self) -> Iterator[GpsTelemetry]:
        """Generate continuous stream of telemetry items."""
        while True:
            tel = self.get_telemetry()
            if tel is None:
                break
            # If not looping and we've stopped at the end of the route
            is_end = self.current_waypoint_idx == len(self.waypoints) - 1
            if not self.loop and is_end and self.current_speed_mps <= 0.05:
                yield tel
                break
            yield tel


if __name__ == "__main__":
    import time

    # CLI Entrypoint for manual verification
    default_route = (
        Path(__file__).parent.parent / "sim" / "routes" / "bengaluru_commute.toml"
    )
    print(f"Starting GPS Route Emulator using {default_route.name} at 1Hz...")

    try:
        emulator = RouteEmulator(route_path=default_route, seed=42)
        for telemetry in emulator:
            data = {
                "timestamp": telemetry.timestamp.isoformat(),
                "latitude": round(telemetry.latitude, 6),
                "longitude": round(telemetry.longitude, 6),
                "altitude_m": round(telemetry.altitude, 1),
                "speed_kmh": round(telemetry.speed_kmh, 1),
                "bearing_deg": round(telemetry.bearing, 2),
                "satellites": telemetry.num_satellites,
                "hdop": telemetry.hdop,
                "fix_quality": telemetry.fix_quality,
            }
            print(json.dumps(data), flush=True)
            time.sleep(0.1)  # slightly faster for console demonstration
    except KeyboardInterrupt:
        print("\nEmulator stopped.")
