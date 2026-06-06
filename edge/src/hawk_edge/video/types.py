"""Type definitions and protocols for the video ingestion subsystem."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class FramePacket:
    """Richer container for frame data and synchronization telemetry.

    NOTE: The 'frame' field contains a numpy array, which is a shared mutable reference.
    Modify it with care to avoid side-effects in buffer histories or concurrent reads.
    """
    ok: bool
    frame: np.ndarray | None
    frame_index: int
    loop_count: int
    source_timestamp_ms: float
    width: int
    height: int


@runtime_checkable
class FrameProvider(Protocol):
    """Interface contract shared between CameraGrabber and VideoFileFeed."""

    def get_frame(self) -> np.ndarray | None:
        """Return the next frame or None if unavailable.

        Matches LLD: CameraGrabber.get_frame() -> Frame
        """
        ...

    def get_packet(self) -> FramePacket | None:
        """Return the next frame packet with metadata, or None if unavailable."""
        ...

    def release(self) -> None:
        """Release underlying resources (VideoCapture or file handle).

        Matches LLD: CameraGrabber.release()
        """
        ...

    @property
    def width(self) -> int:
        """Width of the video stream."""
        ...

    @property
    def height(self) -> int:
        """Height of the video stream."""
        ...

    @property
    def fps(self) -> float:
        """Frame rate of the video stream."""
        ...
