"""Unit and integration tests for VideoFileFeed and generate_synthetic_traffic_video."""
from pathlib import Path

import cv2
import numpy as np
import pytest

from hawk_edge.sim.config import SyntheticVideoConfig
from hawk_edge.sim.media_feed import (
    VideoFileFeed,
    generate_synthetic_traffic_video,
)
from hawk_edge.video.types import FramePacket


@pytest.fixture
def temp_video_path(tmp_path: Path) -> Path:
    """Fixture to provide a clean temp path for generated test videos."""
    return tmp_path / "test_traffic.mp4"


def test_generate_synthetic_video(temp_video_path: Path) -> None:
    """Verify that generate_synthetic_traffic_video creates a valid, readable video."""
    width, height, fps, duration = 320, 180, 5, 2
    path = generate_synthetic_traffic_video(
        file_path=temp_video_path,
        duration_sec=duration,
        fps=fps,
        width=width,
        height=height,
        seed=42
    )
    
    assert path.exists()
    assert path == temp_video_path
    
    # Verify readability with cv2.VideoCapture directly
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened()
    
    cap_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_fps = float(cap.get(cv2.CAP_PROP_FPS))
    cap_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    assert cap_w == width
    assert cap_h == height
    assert cap_fps == fps
    assert cap_count == duration * fps
    
    cap.release()


def test_generate_synthetic_video_codec_fallback(tmp_path: Path) -> None:
    """Verify that synthetic generation falls back to avi/MJPG if primary codec fails."""
    target_path = tmp_path / "test_fallback.mp4"
    # Using an invalid codec name 'invalid_codec' to trigger fallback
    path = generate_synthetic_traffic_video(
        file_path=target_path,
        duration_sec=1,
        fps=5,
        width=160,
        height=90,
        codec="XYZW"
    )
    
    # Ensure it rewrote extension to .avi and successfully wrote the file
    assert path.exists()
    assert path.suffix == ".avi"
    
    # Check that the file is readable
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 160
    cap.release()


def test_generate_validation_errors(temp_video_path: Path) -> None:
    """Ensure negative or zero bounds raise ValueError during generation."""
    with pytest.raises(ValueError, match="duration_sec must be positive"):
        generate_synthetic_traffic_video(temp_video_path, duration_sec=0)
        
    with pytest.raises(ValueError, match="fps must be positive"):
        generate_synthetic_traffic_video(temp_video_path, fps=-1)
        
    with pytest.raises(ValueError, match="width must be positive"):
        generate_synthetic_traffic_video(temp_video_path, width=0)
        
    with pytest.raises(ValueError, match="height must be positive"):
        generate_synthetic_traffic_video(temp_video_path, height=-10)


def test_video_file_feed_metadata(temp_video_path: Path) -> None:
    """Verify VideoFileFeed exposes correct metadata fields."""
    width, height, fps, duration = 320, 180, 10, 1
    generate_synthetic_traffic_video(
        file_path=temp_video_path,
        duration_sec=duration,
        fps=fps,
        width=width,
        height=height
    )
    
    feed = VideoFileFeed(temp_video_path, loop=False)
    assert feed.video_path == temp_video_path
    assert feed.width == width
    assert feed.height == height
    assert feed.fps == fps
    assert feed.frame_count == duration * fps
    assert feed.current_frame_index == 0
    assert feed.loop_count == 0
    assert feed.is_open is True
    
    feed.release()
    assert feed.is_open is False


def test_video_file_feed_get_frame_sequential(temp_video_path: Path) -> None:
    """Verify reading frames sequentially from VideoFileFeed using get_frame."""
    width, height, fps, duration = 320, 180, 5, 1
    total_frames = duration * fps  # 5 frames
    generate_synthetic_traffic_video(
        file_path=temp_video_path,
        duration_sec=duration,
        fps=fps,
        width=width,
        height=height
    )
    
    with VideoFileFeed(temp_video_path, loop=False) as feed:
        for idx in range(total_frames):
            assert feed.current_frame_index == idx
            frame = feed.get_frame()
            assert frame is not None
            assert frame.shape == (height, width, 3)
            assert feed.current_frame_index == idx + 1
            
        # The next read should hit EOF
        frame = feed.get_frame()
        assert frame is None


def test_video_file_feed_no_loop(temp_video_path: Path) -> None:
    """Verify that loop=False returns None after EOF."""
    generate_synthetic_traffic_video(temp_video_path, duration_sec=1, fps=5, width=320, height=180)
    
    with VideoFileFeed(temp_video_path, loop=False) as feed:
        # Read all 5 frames
        for _ in range(5):
            frame = feed.get_frame()
            assert frame is not None
            
        # Subsequent reads return None
        frame = feed.get_frame()
        assert frame is None


def test_video_file_feed_loop(temp_video_path: Path) -> None:
    """Verify that loop=True rewinds correctly at EOF and increments loop count."""
    generate_synthetic_traffic_video(temp_video_path, duration_sec=1, fps=5, width=320, height=180)
    
    with VideoFileFeed(temp_video_path, loop=True) as feed:
        # Read 5 frames
        for idx in range(5):
            frame = feed.get_frame()
            assert frame is not None
            assert feed.loop_count == 0
            assert feed.current_frame_index == idx + 1
            
        # 6th read should trigger looping
        frame = feed.get_frame()
        assert frame is not None
        assert feed.loop_count == 1
        assert feed.current_frame_index == 1
        
        # Read remaining 4 frames of second loop
        for idx in range(1, 5):
            frame = feed.get_frame()
            assert frame is not None
            assert feed.loop_count == 1
            assert feed.current_frame_index == idx + 1
            
        # 11th read should loop again
        frame = feed.get_frame()
        assert frame is not None
        assert feed.loop_count == 2
        assert feed.current_frame_index == 1


def test_get_packet(temp_video_path: Path) -> None:
    """Verify get_packet returns correct FramePacket metadata."""
    width, height, fps = 320, 180, 5
    generate_synthetic_traffic_video(
        temp_video_path, duration_sec=1, fps=fps, width=width, height=height
    )
    
    with VideoFileFeed(temp_video_path, loop=True) as feed:
        # First packet
        pkt = feed.get_packet()
        assert isinstance(pkt, FramePacket)
        assert pkt.ok is True
        assert pkt.frame is not None
        assert pkt.frame.shape == (height, width, 3)
        assert pkt.frame_index == 0
        assert pkt.loop_count == 0
        assert pkt.source_timestamp_ms == 0.0
        assert pkt.width == width
        assert pkt.height == height
        
        # Second packet
        pkt2 = feed.get_packet()
        assert pkt2.frame_index == 1
        assert pkt2.source_timestamp_ms == 1000.0 / fps  # 200ms
        
        # Read up to loop
        for _ in range(3):
            feed.get_packet()
            
        # 6th packet triggers loop
        pkt6 = feed.get_packet()
        assert pkt6.ok is True
        assert pkt6.frame_index == 0
        assert pkt6.loop_count == 1
        assert pkt6.source_timestamp_ms == 0.0


def test_missing_file_errors(tmp_path: Path) -> None:
    """Ensure missing file raises FileNotFoundError when auto_generate is False."""
    fake_path = tmp_path / "does_not_exist.mp4"
    with pytest.raises(FileNotFoundError, match="Video file not found at path"):
        VideoFileFeed(fake_path, auto_generate=False)


def test_auto_generate_with_injected_generator(tmp_path: Path) -> None:
    """Ensure auto-generation calls custom generator if file is missing."""
    fake_path = tmp_path / "autogen.mp4"
    called = False
    
    def dummy_generator(file_path, **kwargs):
        nonlocal called
        called = True
        # Actually generate a small video so initialization succeeds
        return generate_synthetic_traffic_video(
            file_path, duration_sec=1, fps=5, width=160, height=90
        )
        
    config = SyntheticVideoConfig(duration_sec=1, fps=5, width=160, height=90)
    feed = VideoFileFeed(
        fake_path, 
        auto_generate=True, 
        generator=dummy_generator, 
        generation_config=config
    )
    
    assert called is True
    # In case generator returns fallback .avi, look for either
    assert Path(feed.video_path).exists()
    assert feed.width == 160
    assert feed.height == 90
    feed.release()


def test_deterministic_generation(tmp_path: Path) -> None:
    """Ensure traffic rendering is identical for same seeds, and different for different seeds."""
    path1 = tmp_path / "seed42_a.mp4"
    path2 = tmp_path / "seed42_b.mp4"
    path3 = tmp_path / "seed100.mp4"
    
    width, height, fps, duration = 160, 90, 5, 1
    generate_synthetic_traffic_video(path1, duration, fps, width, height, seed=42)
    generate_synthetic_traffic_video(path2, duration, fps, width, height, seed=42)
    generate_synthetic_traffic_video(path3, duration, fps, width, height, seed=100)
    
    # Read first frames
    f1 = VideoFileFeed(path1, loop=False)
    f2 = VideoFileFeed(path2, loop=False)
    f3 = VideoFileFeed(path3, loop=False)
    
    frame1 = f1.get_frame()
    frame2 = f2.get_frame()
    frame3 = f3.get_frame()
    
    assert frame1 is not None and frame2 is not None and frame3 is not None
    
    # Seed 42 instances must match exactly
    assert np.array_equal(frame1, frame2)
    
    # Seed 100 frame should differ from Seed 42
    assert not np.array_equal(frame1, frame3)
    
    f1.release()
    f2.release()
    f3.release()


def test_invalid_metadata_errors(monkeypatch, temp_video_path: Path) -> None:
    """Ensure ValueError is raised if VideoCapture returns invalid metadata."""
    generate_synthetic_traffic_video(temp_video_path, duration_sec=1, fps=5, width=160, height=90)
    
    # Mock cv2.VideoCapture.get to return 0 for width
    orig_get = cv2.VideoCapture.get
    
    def mock_get(self, prop_id):
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return 0
        return orig_get(self, prop_id)
        
    monkeypatch.setattr(cv2.VideoCapture, "get", mock_get)
    
    with pytest.raises(ValueError, match="Invalid video metadata"):
        VideoFileFeed(temp_video_path, loop=False)


def test_close_idempotent(temp_video_path: Path) -> None:
    """Verify that calling release multiple times is safe and a no-op."""
    generate_synthetic_traffic_video(temp_video_path, duration_sec=1, fps=5, width=160, height=90)
    feed = VideoFileFeed(temp_video_path, loop=False)
    assert feed.is_open is True
    
    feed.release()
    assert feed.is_open is False
    
    # Calling release again should not raise errors
    feed.release()
    assert feed.is_open is False


def test_read_on_closed_feed_raises(temp_video_path: Path) -> None:
    """Verify that reading from a closed feed raises RuntimeError."""
    generate_synthetic_traffic_video(temp_video_path, duration_sec=1, fps=5, width=160, height=90)
    feed = VideoFileFeed(temp_video_path, loop=False)
    feed.release()
    
    with pytest.raises(RuntimeError, match="VideoFileFeed is closed"):
        feed.get_frame()
