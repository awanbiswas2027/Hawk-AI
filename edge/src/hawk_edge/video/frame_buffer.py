"""Thread-safe circular frame buffer for evidence retrieval."""
import threading
from collections import deque

import numpy as np


class FrameRingBuffer:
    """Thread-safe circular buffer for frame history.

    SRS-F-1.2: Must retain current frame + 3 preceding frames.
    HLD FrameBufferManager: Default capacity of 15 frames.
    """

    def __init__(self, capacity: int = 15) -> None:
        if capacity <= 0:
            raise ValueError("Buffer capacity must be positive")
        self._buffer: deque[np.ndarray] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._frame_count = 0

    def push(self, frame: np.ndarray) -> None:
        """Appends a new frame to the circular history buffer thread-safely."""
        if not isinstance(frame, np.ndarray):
            raise TypeError("Frame must be a numpy.ndarray")
        
        with self._lock:
            self._buffer.append(frame)
            self._frame_count += 1

    def get_evidence_frames(self, n: int = 4) -> list[np.ndarray]:
        """Retrieves the last n frames from the buffer history.

        Default n=4 satisfies SRS-F-1.2: current + 3 preceding frames.
        """
        if n <= 0:
            raise ValueError("n must be positive")
            
        with self._lock:
            size = len(self._buffer)
            start = max(0, size - n)
            return [self._buffer[i] for i in range(start, size)]

    @property
    def total_frames_processed(self) -> int:
        """Total count of frames pushed into this buffer instance since initialization."""
        with self._lock:
            return self._frame_count

    @property
    def capacity(self) -> int:
        """Maximum frame capacity of the buffer."""
        # maxlen is read-only and always available, but access within lock is safest
        with self._lock:
            return self._buffer.maxlen or 0

    @property
    def size(self) -> int:
        """Current frame count inside the buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def memory_usage_mb(self) -> float:
        """Estimated RAM usage of the current buffer frames in Megabytes."""
        with self._lock:
            if not self._buffer:
                return 0.0
            # nbytes retrieves total bytes consumed by elements
            frame_bytes = self._buffer[0].nbytes
            total_bytes = len(self._buffer) * frame_bytes
            return float(total_bytes) / (1024.0 * 1024.0)
