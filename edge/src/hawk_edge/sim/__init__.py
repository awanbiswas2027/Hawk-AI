"""Hawk-AI Simulation Submodule."""
from hawk_edge.sim.noise import GpsNoiseModel
from hawk_edge.sim.speed_profile import TrapezoidalSpeedProfile

__all__ = ["GpsNoiseModel", "TrapezoidalSpeedProfile"]
