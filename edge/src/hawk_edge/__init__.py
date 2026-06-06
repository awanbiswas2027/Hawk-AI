"""Hawk-AI Edge Emulation Package."""
from hawk_edge.persistence import SQLiteBuffer, ViolationEvent
from hawk_edge.video import (
    CameraGrabber,
    EdgePipeline,
    FramePacket,
    FrameProvider,
    FrameRingBuffer,
)

__version__ = "0.1.0"

__all__ = [
    "CameraGrabber",
    "EdgePipeline",
    "FramePacket",
    "FrameProvider",
    "FrameRingBuffer",
    "SQLiteBuffer",
    "ViolationEvent",
]

