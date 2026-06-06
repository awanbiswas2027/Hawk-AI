"""Integration tests for EdgePipeline compositor."""
import time
from pathlib import Path

import numpy as np
import pytest

from hawk_edge.config import EdgeConfig
from hawk_edge.sim.media_feed import generate_synthetic_traffic_video
from hawk_edge.video.pipeline import EdgePipeline


@pytest.fixture
def sample_video_path(tmp_path: Path) -> Path:
    """Fixture to generate a small synthetic video clip for pipeline tests."""
    video_file = tmp_path / "pipeline_source.mp4"
    # 2 seconds at 10 FPS = 20 frames, resolution 320x180
    generate_synthetic_traffic_video(
        video_file,
        duration_sec=2,
        fps=10,
        width=320,
        height=180
    )
    return video_file


def test_pipeline_basic_flow(sample_video_path: Path) -> None:
    """Verify that get_frame() automatically feeds the ring buffer."""
    with EdgePipeline(
        source=sample_video_path,
        target_fps=15,
        buffer_capacity=10,
        realtime=False
    ) as pipeline:
        # Give a small window for background thread to read frames
        time.sleep(0.15)
        
        # Pull 3 frames
        frame1 = pipeline.get_frame()
        frame2 = pipeline.get_frame()
        frame3 = pipeline.get_frame()
        
        assert frame1 is not None
        assert frame2 is not None
        assert frame3 is not None
        
        # Verify shape and type consistency
        for f in [frame1, frame2, frame3]:
            assert f.shape == (180, 320, 3)
            assert f.dtype == np.uint8
            
        # Get evidence frames
        evidence = pipeline.get_evidence(3)
        assert len(evidence) == 3
        assert np.array_equal(evidence[0], frame1)
        assert np.array_equal(evidence[1], frame2)
        assert np.array_equal(evidence[2], frame3)


def test_pipeline_from_config(sample_video_path: Path) -> None:
    """Verify that from_config() correctly instantiates EdgePipeline."""
    config = EdgeConfig(
        target_fps=20,
        buffer_capacity=8,
    )
    with EdgePipeline.from_config(
        source=sample_video_path,
        config=config,
        realtime=False
    ) as pipeline:
        assert pipeline.fps == 20.0
        # Wait for a frame to verify dimensions
        time.sleep(0.1)
        frame = pipeline.get_frame()
        assert frame is not None
        assert pipeline.width == 320
        assert pipeline.height == 180
        
        # Verify buffer capacity is correct
        assert pipeline._buffer.capacity == 8


def test_pipeline_realtime_drop_rate(sample_video_path: Path) -> None:
    """Verify frame drop rate under moderate realtime load is minimal (TC-PR-01)."""
    # Grab frames at 15 FPS
    with EdgePipeline(
        source=sample_video_path,
        target_fps=15,
        buffer_capacity=15,
        max_queue_size=10,
        realtime=True
    ) as pipeline:
        # Paced reads to simulate YOLO processing
        start_time = time.time()
        frames_retrieved = 0
        while time.time() - start_time < 1.0:
            frame = pipeline.get_frame()
            if frame is not None:
                frames_retrieved += 1
                # Sleep briefly (e.g. 20ms) to simulate work
                time.sleep(0.02)
            else:
                time.sleep(0.01)
                
        # Drop rate = dropped / (retrieved + dropped)
        dropped = pipeline.frames_dropped
        total = frames_retrieved + dropped
        drop_rate = (dropped / total) if total > 0 else 0.0
        assert drop_rate < 0.10, f"Frame drop rate too high: {drop_rate * 100:.2f}%"


def test_pipeline_concurrent_consumer(sample_video_path: Path) -> None:
    """Verify concurrent reads from multiple consumer threads are safe."""
    import threading
    
    with EdgePipeline(
        source=sample_video_path,
        target_fps=20,
        buffer_capacity=10,
        realtime=False
    ) as pipeline:
        time.sleep(0.15)
        
        results: list[np.ndarray] = []
        lock = threading.Lock()
        
        def consumer() -> None:
            for _ in range(5):
                frame = pipeline.get_frame()
                if frame is not None:
                    with lock:
                        results.append(frame)
                time.sleep(0.01)
                
        threads = [threading.Thread(target=consumer) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Verify that we consumed frames safely
        assert len(results) > 0
        for f in results:
            assert f.shape == (180, 320, 3)
