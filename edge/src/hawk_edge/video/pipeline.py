"""Edge composition pipeline wiring CameraGrabber to FrameRingBuffer."""
import logging
from pathlib import Path
from types import TracebackType

import numpy as np

from hawk_edge.config import EdgeConfig
from hawk_edge.video.camera_stream import CameraGrabber
from hawk_edge.video.frame_buffer import FrameRingBuffer
from hawk_edge.video.types import FrameProvider

logger = logging.getLogger(__name__)


class EdgePipeline:
    """Composition pipeline wiring CameraGrabber to FrameRingBuffer.

    Provides a unified API to retrieve frames and extract evidence frame sets.
    """

    def __init__(
        self,
        source: int | str | Path | FrameProvider,
        target_fps: float = 15.0,
        buffer_capacity: int = 15,
        max_queue_size: int = 10,
        realtime: bool = True,
    ) -> None:
        self._grabber = CameraGrabber(
            source=source,
            target_fps=target_fps,
            max_queue_size=max_queue_size,
            realtime=realtime,
        )
        self._buffer = FrameRingBuffer(capacity=buffer_capacity)

    @classmethod
    def from_config(
        cls,
        source: int | str | Path | FrameProvider,
        config: EdgeConfig,
        realtime: bool = True,
    ) -> "EdgePipeline":
        """Factory method to construct pipeline from EdgeConfig."""
        return cls(
            source=source,
            target_fps=float(config.target_fps),
            buffer_capacity=config.buffer_capacity,
            max_queue_size=10,  # Default max queue size
            realtime=realtime,
        )

    def start(self) -> None:
        """Start background grabber."""
        self._grabber.start()

    def stop(self) -> None:
        """Stop background grabber."""
        self._grabber.stop()

    def release(self) -> None:
        """Release underlying resources."""
        self._grabber.release()

    def get_frame(self) -> np.ndarray | None:
        """Dequeues frame from grabber, pushes to ring buffer, returns frame."""
        frame = self._grabber.get_frame()
        if frame is not None:
            self._buffer.push(frame)
        return frame

    def get_evidence(self, n: int = 4) -> list[np.ndarray]:
        """Returns last n frames from ring buffer."""
        return self._buffer.get_evidence_frames(n)

    def __enter__(self) -> "EdgePipeline":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    @property
    def width(self) -> int:
        """Width of the video stream."""
        return self._grabber.width

    @property
    def height(self) -> int:
        """Height of the video stream."""
        return self._grabber.height

    @property
    def fps(self) -> float:
        """Ingestion target FPS."""
        return self._grabber.fps

    @property
    def frames_dropped(self) -> int:
        """Cumulative dropped frame count from grabber."""
        return self._grabber.frames_dropped

    @property
    def buffer_memory_mb(self) -> float:
        """Estimated RAM usage of the current buffer frames in Megabytes."""
        return self._buffer.memory_usage_mb
