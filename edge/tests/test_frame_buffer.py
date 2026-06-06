"""Unit and integration tests for FrameRingBuffer."""
import threading
import time

import numpy as np
import pytest

from hawk_edge.video.frame_buffer import FrameRingBuffer


def test_frame_buffer_initialization() -> None:
    """Verify that the frame buffer initializes correctly and validates inputs."""
    buf = FrameRingBuffer(capacity=5)
    assert buf.capacity == 5
    assert buf.size == 0
    assert buf.total_frames_processed == 0
    assert buf.memory_usage_mb == 0.0

    with pytest.raises(ValueError, match="Buffer capacity must be positive"):
        FrameRingBuffer(capacity=0)

    with pytest.raises(ValueError, match="Buffer capacity must be positive"):
        FrameRingBuffer(capacity=-10)


def test_frame_buffer_default_capacity() -> None:
    """Verify that the default capacity of FrameRingBuffer is 15."""
    buf = FrameRingBuffer()
    assert buf.capacity == 15


def test_frame_buffer_push_type_validation() -> None:
    """Verify that the buffer strictly enforces numpy ndarrays."""
    buf = FrameRingBuffer(capacity=5)
    
    with pytest.raises(TypeError, match="Frame must be a numpy.ndarray"):
        buf.push("not a numpy array")  # type: ignore[arg-type]


def test_frame_buffer_eviction() -> None:
    """Verify circular queue eviction policies when capacity is exceeded."""
    buf = FrameRingBuffer(capacity=3)
    
    frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 1
    frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 2
    frame3 = np.ones((100, 100, 3), dtype=np.uint8) * 3
    frame4 = np.ones((100, 100, 3), dtype=np.uint8) * 4
    
    buf.push(frame1)
    buf.push(frame2)
    buf.push(frame3)
    
    assert buf.size == 3
    assert buf.total_frames_processed == 3
    
    # Check that frames in memory match
    stored = buf.get_evidence_frames(3)
    assert len(stored) == 3
    assert np.array_equal(stored[0], frame1)
    assert np.array_equal(stored[2], frame3)
    
    # Push 4th frame, evicting the 1st
    buf.push(frame4)
    assert buf.size == 3
    assert buf.total_frames_processed == 4
    
    stored = buf.get_evidence_frames(3)
    assert np.array_equal(stored[0], frame2)  # frame1 evicted
    assert np.array_equal(stored[2], frame4)


def test_frame_buffer_get_evidence_frames_slicing() -> None:
    """Verify that get_evidence_frames slices the correct count."""
    buf = FrameRingBuffer(capacity=10)
    
    for i in range(5):
        frame = np.ones((10, 10, 3), dtype=np.uint8) * i
        buf.push(frame)
        
    assert buf.size == 5
    
    # Request last 2 frames
    last_two = buf.get_evidence_frames(2)
    assert len(last_two) == 2
    assert np.mean(last_two[0]) == 3.0
    assert np.mean(last_two[1]) == 4.0
    
    # Requesting more frames than size returns all available
    all_five = buf.get_evidence_frames(10)
    assert len(all_five) == 5
    assert np.mean(all_five[0]) == 0.0
    
    # Invalid argument checks
    with pytest.raises(ValueError, match="n must be positive"):
        buf.get_evidence_frames(0)
        
    with pytest.raises(ValueError, match="n must be positive"):
        buf.get_evidence_frames(-1)


def test_frame_buffer_memory_calculation() -> None:
    """Verify memory footprint size calculation equations."""
    buf = FrameRingBuffer(capacity=10)
    assert buf.memory_usage_mb == 0.0
    
    # 100 x 100 x 3 bytes = 30,000 bytes = ~0.0286 MB
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    expected_per_frame_mb = float(frame.nbytes) / (1024.0 * 1024.0)
    
    for i in range(5):
        buf.push(frame)
        assert pytest.approx(buf.memory_usage_mb, rel=1e-5) == (i + 1) * expected_per_frame_mb


def test_frame_buffer_thread_safety() -> None:
    """Verify thread-safety guarantees under concurrent read/write loads."""
    buf = FrameRingBuffer(capacity=100)
    num_threads = 8
    pushes_per_thread = 50
    
    def producer():
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        for _ in range(pushes_per_thread):
            buf.push(frame)
            time.sleep(0.001)

    threads = [
        threading.Thread(target=producer) for _ in range(num_threads)
    ]
    
    # Start all producers
    for t in threads:
        t.start()
        
    # Wait for completion
    for t in threads:
        t.join()
        
    # Verify exact totals
    assert buf.total_frames_processed == num_threads * pushes_per_thread
    assert buf.size == buf.capacity  # Buffer reached capacity and wrapped
