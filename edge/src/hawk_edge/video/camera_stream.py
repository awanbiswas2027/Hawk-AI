"""Threaded camera stream capture and background frame grabber."""
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from hawk_edge.sim.media_feed import VideoFileFeed
from hawk_edge.video.types import FramePacket, FrameProvider

logger = logging.getLogger(__name__)


class CameraGrabber(FrameProvider):
    """Threaded background frame grabber.
    
    Ingests frames in a dedicated thread to decouple decoding latency
    from YOLO processing. Implements the FrameProvider Protocol.
    """

    def __init__(
        self,
        source: int | str | Path | FrameProvider,
        target_fps: float = 15.0,
        max_queue_size: int = 10,
        realtime: bool = True,
    ) -> None:
        if target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")

        self._target_fps = target_fps
        self._max_queue_size = max_queue_size
        self._realtime = realtime
        self._is_running = False
        
        self._width: int = 1920
        self._height: int = 1080
        self._fps: float = 30.0
        
        # Determine and initialize the frame source
        self._managed_source: FrameProvider | None = None
        self._cap: cv2.VideoCapture | None = None
        
        # Check if the source is already a FrameProvider
        # (Using hasattr as isinstance check with Protocol can be tricky)
        if hasattr(source, "get_frame") and hasattr(source, "release"):
            self._source: Any = source
        elif isinstance(source, (str, Path)):
            # Open video file using our auto-looping VideoFileFeed
            logger.info("Instantiating VideoFileFeed for file source: %s", source)
            self._managed_source = VideoFileFeed(source, loop=True, auto_generate=False)
            self._source = self._managed_source
        elif isinstance(source, int):
            # Open camera device directly
            logger.info("Opening hardware camera device ID: %d", source)
            self._cap = cv2.VideoCapture(source)
            if not self._cap.isOpened():
                raise RuntimeError(f"Failed to open hardware camera device ID: {source}")
            self._source = None
        else:
            raise TypeError(
                "Source must be a FrameProvider instance, a file path (str/Path), "
                "or an integer camera ID."
            )

        # Retrieve dimensions and metadata properties from underlying source
        if self._source:
            self._width = self._source.width
            self._height = self._source.height
            self._fps = self._source.fps
        else:
            assert self._cap is not None
            self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._fps = float(self._cap.get(cv2.CAP_PROP_FPS))
            # Validate properties. Hardware captures might return 0 initially, set fallback defaults
            if self._width <= 0:
                self._width = 1920
            if self._height <= 0:
                self._height = 1080
            if self._fps <= 0:
                self._fps = 30.0

        # Threading and Queue storage setup
        self._queue: queue.Queue[FramePacket] = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        
        # Statistics counters
        self._frames_dropped = 0
        self._frames_read = 0

        logger.info(
            "CameraGrabber initialized [Res: %dx%d, Ingestion Target: %.2f FPS, Realtime: %s]",
            self._width, self._height, self._target_fps, self._realtime
        )

    def start(self) -> None:
        """Starts the background worker thread for frame ingestion."""
        with self._lock:
            if self._is_running:
                logger.warning("CameraGrabber is already running.")
                return
            
            self._is_running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="CameraGrabberWorker",
                daemon=True
            )
            self._thread.start()
            logger.info("Background grabber thread started.")

    def stop(self) -> None:
        """Stops the background grabber thread and releases source capture handles."""
        with self._lock:
            if not self._is_running:
                return
                
            self._is_running = False
            self._stop_event.set()
            
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
            
        # Release resource handles
        if self._cap:
            self._cap.release()
            self._cap = None
        if self._managed_source:
            self._managed_source.release()
            self._managed_source = None
            
        logger.info("CameraGrabber background thread stopped and resources released.")

    def release(self) -> None:
        """Release wrapper matching LLD contract and FrameProvider interface."""
        self.stop()

    def _worker_loop(self) -> None:
        """Dedicated worker thread loop that paces and queues frames."""
        interval = 1.0 / self._target_fps
        next_tick = time.perf_counter()
        
        frame_idx = 0
        loop_cnt = 0

        while not self._stop_event.is_set():
            ok = False
            frame: np.ndarray | None = None
            
            # 1. Fetch the raw frame from the source
            if self._source:
                # Source is a FrameProvider (e.g. VideoFileFeed)
                packet = self._source.get_packet()
                if packet:
                    ok = packet.ok
                    frame = packet.frame
                    frame_idx = packet.frame_index
                    loop_cnt = packet.loop_count
            else:
                # Source is a direct cv2.VideoCapture UVC stream
                assert self._cap is not None
                ok, frame = self._cap.read()
                if ok:
                    frame_idx += 1

            if not ok or frame is None:
                # Hit EOF without looping enabled, or hardware error
                logger.warning(
                    "Failed to grab frame from video source. Stopping background worker."
                )
                break

            # 2. Package the frame
            ts_ms = (frame_idx * 1000.0) / self._target_fps
            pkt = FramePacket(
                ok=True,
                frame=frame,
                frame_index=frame_idx,
                loop_count=loop_cnt,
                source_timestamp_ms=ts_ms,
                width=self._width,
                height=self._height
            )

            # 3. Buffer management (thread-safe queue insert)
            if self._queue.full():
                if self._realtime:
                    try:
                        # Drop the oldest frame to preserve low latency
                        self._queue.get_nowait()
                        self._frames_dropped += 1
                        logger.debug("Realtime queue full: oldest frame dropped.")
                    except queue.Empty:
                        pass
                    self._queue.put(pkt)
                else:
                    # Non-realtime mode: blocks until slot opens or shutdown is requested
                    try:
                        while not self._stop_event.is_set():
                            self._queue.put(pkt, timeout=0.1)
                            break
                    except queue.Full:
                        pass
            else:
                self._queue.put(pkt)
                
            self._frames_read += 1

            # 4. Pace calculations (dynamic sleeping to lock target frame rate)
            next_tick += interval
            sleep_time = next_tick - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # Reset clock tick if decoding lag exceeds target rate
                next_tick = time.perf_counter()

    def get_frame(self) -> np.ndarray | None:
        """Retrieves the next decoded frame array from the queue buffer."""
        pkt = self.get_packet()
        return pkt.frame if pkt else None

    def get_packet(self) -> FramePacket | None:
        """Retrieves the next FramePacket containing frame arrays and sync metadata."""
        if not self._is_running:
            raise RuntimeError("CameraGrabber is not running. Call start() first.")
            
        try:
            # Pop next item. Don't block forever to allow graceful cleanup
            return self._queue.get(timeout=0.2)
        except queue.Empty:
            return None

    def __enter__(self) -> "CameraGrabber":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    @property
    def is_running(self) -> bool:
        """True if the background ingestion worker is running."""
        return self._is_running

    @property
    def width(self) -> int:
        """Width of the video stream."""
        return self._width

    @property
    def height(self) -> int:
        """Height of the video stream."""
        return self._height

    @property
    def fps(self) -> float:
        """Target processing frame rate of the video stream."""
        return self._target_fps

    @property
    def queue_size(self) -> int:
        """Current count of frames stored in the buffer queue."""
        return self._queue.qsize()

    @property
    def frames_dropped(self) -> int:
        """Cumulative count of frames dropped to maintain realtime limits."""
        return self._frames_dropped

    @property
    def total_frames_processed(self) -> int:
        """Cumulative count of frames read from source."""
        return self._frames_read


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Hawk-AI CameraStream Ingestion & Workload Simulator"
    )
    parser.add_argument(
        "--simulate-workload",
        action="store_true",
        help="Run real-time consumer queue workload simulation"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="",
        help="Video file path for simulator input (leaves empty to autogenerate)"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=15.0,
        help="Target ingestion rate"
    )
    parser.add_argument(
        "--latency",
        type=float,
        default=0.1,
        help="Consumer processing sleep latency in seconds (YOLO simulator)"
    )
    
    args = parser.parse_args()
    
    if args.simulate_workload:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
        
        # Resolve target source file path
        source_path = Path(args.source) if args.source else Path(".tmp/simulation_demo.mp4")
        if not source_path.exists():
            from hawk_edge.sim.media_feed import generate_synthetic_traffic_video
            print(
                f"Generating synthetic video clip at {source_path} for simulation workload..."
            )
            generate_synthetic_traffic_video(
                source_path, duration_sec=5, fps=15, width=640, height=360
            )
            
        print(f"Starting CameraGrabber with source: {source_path} at {args.fps} FPS")
        print(f"Simulating consumer processing latency: {args.latency * 1000.0:.1f}ms per frame")
        
        try:
            with CameraGrabber(
                source_path,
                target_fps=args.fps,
                max_queue_size=5,
                realtime=True
            ) as grabber:
                time.sleep(1.0)  # Wait for buffer to fill
                
                start_time = time.time()
                frames_consumed = 0
                
                # Consume for 5 seconds
                while time.time() - start_time < 5.0:
                    pkt = grabber.get_packet()
                    if pkt and pkt.ok:
                        frames_consumed += 1
                        # Simulate YOLO load
                        time.sleep(args.latency)
                        print(
                            f"Consumed frame #{pkt.frame_index} (Loop {pkt.loop_count}) | "
                            f"Queue Size: {grabber.queue_size} | "
                            f"Dropped: {grabber.frames_dropped} | "
                            f"Processed: {grabber.total_frames_processed}"
                        )
                    else:
                        time.sleep(0.01)
                        
                print("\nWorkload Simulation Summary:")
                print(f"  Frames Consumed: {frames_consumed}")
                print(f"  Total Ingested: {grabber.total_frames_processed}")
                print(f"  Total Dropped: {grabber.frames_dropped}")
                sys.exit(0)
        except Exception as e:
            print(f"ERROR: Simulation failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
