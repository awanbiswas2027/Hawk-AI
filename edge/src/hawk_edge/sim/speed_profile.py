"""Physical dynamics and speed profiling for realistic vehicle simulations."""
from dataclasses import dataclass


@dataclass
class TrafficStopModel:
    """Manages the lifecycle of a stop event at a traffic signal."""

    stop_duration_s: float
    elapsed_time_s: float = 0.0
    active: bool = False

    def check_stop(self, current_speed_mps: float, dt: float) -> bool:
        """Process traffic stop countdown.

        Returns True if the vehicle should remain stopped.
        """
        if not self.active:
            if current_speed_mps <= 0.05:
                self.active = True
                self.elapsed_time_s = 0.0
            return True

        self.elapsed_time_s += dt
        if self.elapsed_time_s >= self.stop_duration_s:
            self.active = False
            return False

        return True


class TrapezoidalSpeedProfile:
    """Controls acceleration and deceleration to model realistic vehicle speeds."""

    def __init__(
        self,
        max_accel_mps2: float = 1.5,  # Typical bike accel ~1.5 m/s^2
        max_decel_mps2: float = 2.5,  # Safe deceleration ~2.5 m/s^2
        initial_speed_mps: float = 0.0,
    ) -> None:
        self.accel = max_accel_mps2
        self.decel = max_decel_mps2
        self.current_speed_mps = initial_speed_mps

    def update(
        self,
        target_speed_mps: float,
        distance_to_stop_m: float | None = None,
        dt: float = 1.0,
    ) -> float:
        """Update current speed toward target speed limit, accounting for stops.

        Args:
            target_speed_mps: The speed limit of the current road.
            distance_to_stop_m: Distance to the next traffic light or waypoint stop.
            dt: Time delta in seconds.

        Returns:
            Updated speed in meters per second.
        """
        # Calculate safe stopping speed profile based on physics: v_limit^2 = 2 * a * d
        if distance_to_stop_m is not None:
            # Leave safety buffer of 0.5m
            effective_dist = max(0.0, distance_to_stop_m - 0.5)
            if effective_dist <= 0.0:
                effective_target = 0.0
            else:
                safe_speed = (2.0 * self.decel * effective_dist) ** 0.5
                effective_target = min(target_speed_mps, safe_speed)
        else:
            effective_target = target_speed_mps

        # Adjust speed based on acceleration/deceleration limits
        if self.current_speed_mps < effective_target:
            self.current_speed_mps = min(
                effective_target, self.current_speed_mps + self.accel * dt
            )
        elif self.current_speed_mps > effective_target:
            self.current_speed_mps = max(
                effective_target, self.current_speed_mps - self.decel * dt
            )

        if self.current_speed_mps < 0.05:
            self.current_speed_mps = 0.0

        return self.current_speed_mps
