"""Validate speed profiles, stopping logic, and deceleration limits."""
from hawk_edge.sim.speed_profile import TrafficStopModel, TrapezoidalSpeedProfile


def test_acceleration_limits():
    """Verify speed increases smoothly within acceleration limits."""
    profile = TrapezoidalSpeedProfile(max_accel_mps2=1.5, max_decel_mps2=2.0)
    assert profile.current_speed_mps == 0.0

    # Accelerating to 5.0 m/s
    speed = profile.update(target_speed_mps=5.0, dt=1.0)
    assert speed == 1.5
    speed = profile.update(target_speed_mps=5.0, dt=2.0)
    assert speed == 4.5
    speed = profile.update(target_speed_mps=5.0, dt=1.0)
    assert speed == 5.0


def test_deceleration_limits():
    """Verify speed decreases smoothly within deceleration limits."""
    profile = TrapezoidalSpeedProfile(
        max_accel_mps2=1.5, max_decel_mps2=2.0, initial_speed_mps=10.0
    )

    # Decelerating to 5.0 m/s
    speed = profile.update(target_speed_mps=5.0, dt=1.0)
    assert speed == 8.0
    speed = profile.update(target_speed_mps=5.0, dt=2.0)
    assert speed == 5.0


def test_stopping_distance_rule():
    """Verify physics stopping distance limits current speed limits."""
    profile = TrapezoidalSpeedProfile(
        max_accel_mps2=1.5, max_decel_mps2=2.0, initial_speed_mps=10.0
    )

    # Safe stop target (dist=5m, decel=2.0m/s^2).
    # safe_speed = (2.0 * 2.0 * (5 - 0.5))**0.5 = (4.0 * 4.5)**0.5 = 18.0**0.5 ~ 4.24 m/s
    # Target speed limit is 10.0 m/s, but stopping requirement limits it to ~4.24.
    speed = profile.update(target_speed_mps=10.0, distance_to_stop_m=5.0, dt=1.0)
    assert speed < 10.0
    assert speed <= 8.0  # Decelerates from 10.0


def test_traffic_stop_countdown():
    """Verify stop models control signal downtime countdowns."""
    model = TrafficStopModel(stop_duration_s=5.0, active=True)
    assert model.active

    # Elapsed countdowns
    assert model.check_stop(current_speed_mps=0.0, dt=2.0) is True
    assert model.active

    assert model.check_stop(current_speed_mps=0.0, dt=4.0) is False
    assert not model.active
