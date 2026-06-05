"""Unit and integration tests for CameraGrabber background streams."""
import time
from pathlib import Path

import numpy as np
import pytest

from hawk_edge.sim.media_feed import generate_synthetic_traffic_video
from hawk_edge.video.camera_stream import CameraGrabber


@pytest.fixture
def sample_video_path(tmp_path: Path) -> Path:
    """Fixture to generate a small synthetic video clip for camera stream tests."""
    video_file = tmp_path / "stream_source.mp4"
    # 2 seconds at 10 FPS = 20 frames, resolution 320x180
    generate_synthetic_traffic_video(
        video_file, 
        duration_sec=2, 
        fps=10, 
        width=320, 
        height=180
    )
    return video_file


def test_camera_grabber_initialization_bounds(sample_video_path: Path) -> None:
    """Verify initialization checks for bounds and type errors."""
    with pytest.raises(ValueError, match="target_fps must be positive"):
        CameraGrabber(sample_video_path, target_fps=0)
        
    with pytest.raises(ValueError, match="max_queue_size must be positive"):
        CameraGrabber(sample_video_path, max_queue_size=-1)
        
    with pytest.raises(TypeError, match="Source must be"):
        CameraGrabber(dict())  # type: ignore[arg-type]


def test_camera_grabber_lifecycle(sample_video_path: Path) -> None:
    """Verify thread start, stop, and double-stop lifecycles are safe."""
    grabber = CameraGrabber(sample_video_path, target_fps=10)
    assert grabber.is_running is False
    
    grabber.start()
    assert grabber.is_running is True
    
    # Starting again should be safe and logged
    grabber.start()
    assert grabber.is_running is True
    
    grabber.stop()
    assert grabber.is_running is False
    
    # Stopping again is safe (idempotent)
    grabber.stop()
    assert grabber.is_running is False


def test_camera_grabber_context_manager(sample_video_path: Path) -> None:
    """Verify that context manager controls lifecycle and resource releases."""
    with CameraGrabber(sample_video_path, target_fps=10) as grabber:
        assert grabber.is_running is True
        
    assert grabber.is_running is False


def test_camera_grabber_sequential_read(sample_video_path: Path) -> None:
    """Verify paced sequential read operations and metadata calculations."""
    # Read paced at 20 FPS (50ms interval)
    with CameraGrabber(
        sample_video_path, target_fps=20, max_queue_size=10, realtime=False
    ) as grabber:
        # Give a small window for the thread to buffer a couple frames
        time.sleep(0.15)
        
        # Read the first few frames
        pkt1 = grabber.get_packet()
        assert pkt1 is not None
        assert pkt1.ok is True
        assert pkt1.frame is not None
        assert pkt1.frame.shape == (180, 320, 3)
        assert pkt1.frame_index == 0
        assert pkt1.loop_count == 0
        assert pkt1.source_timestamp_ms == 0.0
        
        pkt2 = grabber.get_packet()
        assert pkt2 is not None
        assert pkt2.frame_index == 1
        assert pkt2.source_timestamp_ms == 50.0  # 1 frame at 20fps = 50ms


def test_camera_grabber_realtime_frame_drop(sample_video_path: Path) -> None:
    """Verify that CameraGrabber drops oldest frames in realtime mode."""
    # Set queue limit to 2 frames, target FPS = 50 (fast producer)
    with CameraGrabber(
        sample_video_path, target_fps=50, max_queue_size=2, realtime=True
    ) as grabber:
        # Sleep to let producer fill and overflow the queue
        # In 0.2 seconds at 50 FPS, it will produce ~10 frames.
        # Queue capacity is 2, so it should drop ~8 frames.
        time.sleep(0.25)
        
        assert grabber.queue_size == 2
        assert grabber.frames_dropped > 0
        
        # The consumer retrieves the LATEST frame index (not index 0, which was evicted)
        pkt = grabber.get_packet()
        assert pkt is not None
        assert pkt.frame_index > 0
        assert grabber.queue_size == 1


def test_camera_grabber_non_realtime_block(sample_video_path: Path) -> None:
    """Verify non-realtime mode does not drop frames and blocks producer instead."""
    # Set queue limit to 2 frames, target FPS = 50 (fast producer), realtime = False
    with CameraGrabber(
        sample_video_path, target_fps=50, max_queue_size=2, realtime=False
    ) as grabber:
        # Sleep to let queue fill. Since realtime is False, it should block rather than drop.
        time.sleep(0.15)
        
        assert grabber.queue_size == 2
        assert grabber.frames_dropped == 0
        
        # The first frame retrieved must still be index 0
        pkt1 = grabber.get_packet()
        assert pkt1 is not None
        assert pkt1.frame_index == 0
        
        # Next frame is index 1
        pkt2 = grabber.get_packet()
        assert pkt2 is not None
        assert pkt2.frame_index == 1
        
        # Queue should now be empty (or has 1 if producer resumed after dequeue)
        assert grabber.frames_dropped == 0


def test_camera_grabber_get_frame_wrapper(sample_video_path: Path) -> None:
    """Verify that get_frame returns only the frame array directly."""
    with CameraGrabber(sample_video_path, target_fps=10) as grabber:
        time.sleep(0.1)
        frame = grabber.get_frame()
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (180, 320, 3)


def test_camera_grabber_inactive_read_raises(sample_video_path: Path) -> None:
    """Verify that calling reads on inactive grabbers raises RuntimeError."""
    grabber = CameraGrabber(sample_video_path, target_fps=10)
    
    with pytest.raises(RuntimeError, match="CameraGrabber is not running"):
        grabber.get_packet()
