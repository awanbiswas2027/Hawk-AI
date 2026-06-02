"""Ornstein-Uhlenbeck process models for GPS coordinate and speed noise."""
import random


class GpsNoiseModel:
    """Simulates autocorrelated GPS drift using Ornstein-Uhlenbeck mean reversion.

    This ensures consecutive GPS readings drift smoothly rather than jumping
    randomly (i.i.d.), matching the characteristics of real GPS errors.
    """

    def __init__(
        self,
        seed: int | None = None,
        theta_coord: float = 0.05,
        sigma_coord: float = 0.00001,
        theta_speed: float = 0.1,
        sigma_speed: float = 0.15,
    ) -> None:
        """Initialize parameters.

        Args:
            seed: Optional seed for deterministic reproducibility.
            theta_coord: Rate of mean reversion for coordinates.
            sigma_coord: Volatility coefficient for coordinates.
            theta_speed: Rate of mean reversion for speed bias.
            sigma_speed: Volatility coefficient for speed bias.
        """
        self.rng = random.Random(seed)
        self.theta_coord = theta_coord
        self.sigma_coord = sigma_coord
        self.theta_speed = theta_speed
        self.sigma_speed = sigma_speed

        self.lat_bias = 0.0
        self.lon_bias = 0.0
        self.speed_bias = 0.0

    def step(self, dt: float = 1.0) -> tuple[float, float, float]:
        """Advance the noise state by dt and return the current biases.

        Args:
            dt: Time step in seconds.

        Returns:
            Tuple of (latitude_bias, longitude_bias, speed_bias_mps).
        """
        # dx = -theta * x * dt + sigma * dW
        # Standard deviation of Wiener increment dW is sqrt(dt)
        std_coord = self.sigma_coord * (dt**0.5)
        std_speed = self.sigma_speed * (dt**0.5)

        self.lat_bias += -self.theta_coord * self.lat_bias * dt + self.rng.normalvariate(
            0.0, std_coord
        )
        self.lon_bias += -self.theta_coord * self.lon_bias * dt + self.rng.normalvariate(
            0.0, std_coord
        )
        self.speed_bias += -self.theta_speed * self.speed_bias * dt + self.rng.normalvariate(
            0.0, std_speed
        )

        return self.lat_bias, self.lon_bias, self.speed_bias

    def reset(self) -> None:
        """Reset biases to zero."""
        self.lat_bias = 0.0
        self.lon_bias = 0.0
        self.speed_bias = 0.0
        
    def adjust_for_canyon(self, is_canyon: bool) -> None:
        """Increase noise parameters to simulate urban canyons / flyovers."""
        if is_canyon:
            self.theta_coord = 0.02  # Drifts further
            self.sigma_coord = 0.00008  # Higher variance
        else:
            self.theta_coord = 0.05
            self.sigma_coord = 0.00001
