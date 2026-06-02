"""Validate GpsNoiseModel Ornstein-Uhlenbeck drift properties."""
from hawk_edge.sim.noise import GpsNoiseModel


def test_noise_determinism():
    """Verify that using the same seed produces identical drift profiles."""
    model1 = GpsNoiseModel(seed=42)
    model2 = GpsNoiseModel(seed=42)

    for _ in range(10):
        lat1, lon1, speed1 = model1.step()
        lat2, lon2, speed2 = model2.step()
        assert lat1 == lat2
        assert lon1 == lon2
        assert speed1 == speed2


def test_noise_mean_reversion():
    """Verify that biases revert towards zero over long steps in absence of infinite walk."""
    model = GpsNoiseModel(seed=123, theta_coord=0.5, sigma_coord=0.0)
    model.lat_bias = 0.005
    model.lon_bias = -0.005

    # With sigma=0, theta=0.5, the bias should contract exponentially toward zero
    lat, lon, _ = model.step(dt=2.0)
    assert abs(lat) < 0.005
    assert abs(lon) < 0.005
    assert abs(model.lat_bias) < 0.005


def test_noise_canyon_adjustment():
    """Verify canyon adjustments increase coordinate noise standard deviation."""
    model = GpsNoiseModel(seed=99)
    assert model.sigma_coord == 0.00001

    model.adjust_for_canyon(True)
    assert model.sigma_coord == 0.00008

    model.adjust_for_canyon(False)
    assert model.sigma_coord == 0.00001
