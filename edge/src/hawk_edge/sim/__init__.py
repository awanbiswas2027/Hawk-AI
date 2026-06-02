"""Hawk-AI Simulation Submodule."""
from hawk_edge.sim.config import SyntheticVideoConfig
from hawk_edge.sim.media_feed import FramePacket, VideoFileFeed, generate_synthetic_traffic_video
from hawk_edge.sim.noise import GpsNoiseModel
from hawk_edge.sim.speed_profile import TrapezoidalSpeedProfile

__all__ = [
    "GpsNoiseModel",
    "TrapezoidalSpeedProfile",
    "SyntheticVideoConfig",
    "FramePacket",
    "VideoFileFeed",
    "generate_synthetic_traffic_video",
]
