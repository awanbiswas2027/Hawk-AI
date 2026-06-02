"""Mock video streaming reader and synthetic media generation."""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from hawk_edge.sim.config import SyntheticVideoConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FramePacket:
    """Richer container for frame data and synchronization telemetry."""
    ok: bool
    frame: np.ndarray | None
    frame_index: int
    loop_count: int
    source_timestamp_ms: float
    width: int
    height: int


def generate_synthetic_traffic_video(
    file_path: Path | str,
    duration_sec: int = 5,
    fps: int = 15,
    width: int = 1920,
    height: int = 1080,
    seed: int = 42,
    codec: str = "mp4v",
) -> Path:
    """Generates a deterministic synthetic video of traffic for simulation and testing.
    
    Draws a highway roadway with lanes and simple colored rectangles moving down to represent cars.
    """
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    if width <= 0:
        raise ValueError("width must be positive")
    if height <= 0:
        raise ValueError("height must be positive")
    
    file_path = Path(file_path)
    
    # Safely create parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    total_frames = int(duration_sec * fps)
    
    # Initialize deterministic random number generator
    rng = np.random.default_rng(seed)
    
    # Layout of the road
    road_left = width // 4
    road_right = 3 * width // 4
    road_width = road_right - road_left
    lane_width = road_width // 3
    lane_centers = [road_left + lane_width // 2 + i * lane_width for i in range(3)]
    
    # Setup standard BGR color palette
    road_color = (50, 50, 50)  # Dark Gray
    shoulder_color = (120, 120, 120)  # Medium Gray
    line_color = (255, 255, 255)  # White
    yellow_line_color = (0, 200, 255)  # Yellow
    
    # Spawn deterministic vehicles
    vehicles: list[dict[str, Any]] = []
    num_vehicles = 6
    for i in range(num_vehicles):
        lane = i % 3
        # Speed range chosen to cross height in about 40%-80% of video duration
        speed = rng.uniform(
            height / (duration_sec * fps * 0.8),
            height / (duration_sec * fps * 0.4)
        )
        # Stagger initial y positions
        y_init = rng.uniform(-height, 0)
        w_veh = int(lane_width * 0.5)
        h_veh = int(w_veh * 1.5)
        # Harmonious BGR color tuple
        color = tuple(int(x) for x in rng.integers(70, 240, size=3))
        vehicles.append({
            "lane": lane,
            "y": y_init,
            "speed": speed,
            "width": w_veh,
            "height": h_veh,
            "color": color
        })

    fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore[attr-defined]
    logger.info("Opening VideoWriter for %s (codec: %s)", file_path, codec)
    
    out = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))
    if not out.isOpened():
        raise RuntimeError(
            f"Failed to open VideoWriter for path '{file_path}' using codec '{codec}'. "
            "Please check OpenCV installation and codec availability."
        )
        
    try:
        for f in range(total_frames):
            # 1. Base canvas (green scenery)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (34, 139, 34)  # Forest green (BGR: ForestGreen is 34, 139, 34)
            
            # 2. Draw highway road
            cv2.rectangle(frame, (road_left, 0), (road_right, height), road_color, -1)
            
            # 3. Draw shoulder borders
            cv2.rectangle(frame, (road_left - 10, 0), (road_left, height), shoulder_color, -1)
            cv2.rectangle(frame, (road_right, 0), (road_right + 10, height), shoulder_color, -1)
            
            #  solid yellow boundary line
            cv2.line(frame, (road_left, 0), (road_left, height), yellow_line_color, 2)
            cv2.line(frame, (road_right, 0), (road_right, height), yellow_line_color, 2)
            
            # 4. Draw lane divider dashes (dashed white lines)
            dash_length = 30
            gap_length = 30
            for lane_idx in range(1, 3):
                x_divider = road_left + lane_idx * lane_width
                y_offset = (f * 5) % (dash_length + gap_length)  # scrolling effect
                y = -y_offset
                while y < height:
                    cv2.line(
                        frame, 
                        (x_divider, int(y)), 
                        (x_divider, int(min(y + dash_length, height))), 
                        line_color, 
                        2
                    )
                    y += dash_length + gap_length
                    
            # 5. Render moving vehicles
            for veh in vehicles:
                veh["y"] += veh["speed"]
                # Wrap vehicle back above the screen if it passes the bottom
                if veh["y"] - veh["height"] > height:
                    veh["y"] = -veh["height"]
                
                x_center = lane_centers[veh["lane"]]
                y_pos = int(veh["y"])
                w_v = veh["width"]
                h_v = veh["height"]
                
                # Draw vehicle body rectangle
                cv2.rectangle(
                    frame, 
                    (x_center - w_v // 2, y_pos - h_v), 
                    (x_center + w_v // 2, y_pos), 
                    veh["color"], 
                    -1
                )
                # Border outline
                cv2.rectangle(
                    frame, 
                    (x_center - w_v // 2, y_pos - h_v), 
                    (x_center + w_v // 2, y_pos), 
                    (0, 0, 0), 
                    1
                )
                
                # Draw windshield / windows
                win_w = int(w_v * 0.8)
                cv2.rectangle(
                    frame, 
                    (x_center - win_w // 2, y_pos - int(h_v * 0.8)), 
                    (x_center + win_w // 2, y_pos - int(h_v * 0.6)), 
                    (200, 200, 200), 
                    -1
                )
                
                # Draw license plate mockup
                plate_w = int(w_v * 0.4)
                cv2.rectangle(
                    frame, 
                    (x_center - plate_w // 2, y_pos - int(h_v * 0.15)), 
                    (x_center + plate_w // 2, y_pos - int(h_v * 0.05)), 
                    (255, 255, 255), 
                    -1
                )
                
            # 6. Add dynamic watermark text
            timestamp_str = f"Time: {f / fps:.2f}s"
            frame_str = f"Frame: {f}/{total_frames}"
            cv2.putText(
                frame, 
                f"{timestamp_str} | {frame_str}", 
                (30, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (255, 255, 255), 
                2, 
                cv2.LINE_AA
            )
            
            out.write(frame)
    finally:
        out.release()
        
    logger.info("Successfully generated synthetic video file at %s", file_path)
    return file_path


class VideoFileFeed:
    """Wrapper around cv2.VideoCapture that reads frames and handles continuous looping."""

    def __init__(
        self,
        video_path: Path | str,
        loop: bool = True,
        auto_generate: bool = False,
        generator: Callable[..., Path] | None = None,
        generation_config: SyntheticVideoConfig | None = None,
    ) -> None:
        self._video_path = Path(video_path)
        self._loop = loop
        self._is_open = False
        
        # Check and optionally generate synthetic video
        if not self._video_path.exists():
            if auto_generate:
                logger.info(
                    "Video file %s not found. Auto-generating synthetic clip.",
                    self._video_path
                )
                gen_func = generator or generate_synthetic_traffic_video
                config = generation_config or SyntheticVideoConfig()
                gen_func(
                    file_path=self._video_path,
                    duration_sec=config.duration_sec,
                    fps=config.fps,
                    width=config.width,
                    height=config.height,
                    seed=config.seed,
                    codec=config.codec,
                )
            else:
                raise FileNotFoundError(f"Video file not found at path: '{self._video_path}'")
                
        # Open source capture
        self._cap = cv2.VideoCapture(str(self._video_path))
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Failed to open video source at '{self._video_path}'. "
                "Verify file validity, path, and OpenCV video backend configuration."
            )
            
        self._is_open = True
        
        # Resolve dimensions and metadata properties
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Validate metadata properties
        if self._width <= 0 or self._height <= 0 or self._fps <= 0 or self._frame_count <= 0:
            self.close()
            raise ValueError(
                f"Invalid video metadata: width={self._width}, height={self._height}, "
                f"fps={self._fps}, frame_count={self._frame_count}. "
                "All values must be positive."
            )
            
        self._current_frame_index = 0
        self._loop_count = 0
        
        logger.info(
            "Opened video feed '%s' [Res: %dx%d, FPS: %.2f, Frames: %d]",
            self._video_path, self._width, self._height, self._fps, self._frame_count
        )

    def read(self) -> tuple[bool, np.ndarray | None]:
        """Reads the next BGR frame from the video stream.
        
        If EOF is hit and loop=True, automatically rewinds to frame 0 and reads again.
        Returns (success, frame).
        """
        if not self._is_open:
            raise RuntimeError("VideoFileFeed is closed.")
            
        ok, frame = self._cap.read()
        if not ok:
            if self._loop:
                logger.debug(
                    "EOF reached. Looping video source '%s' back to frame 0.",
                    self._video_path
                )
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
                if not ok:
                    # Reread failed even after seek (could be corrupted file)
                    logger.error(
                        "Failed to rewind and read frame 0 for looped source '%s'.",
                        self._video_path
                    )
                    return False, None
                    
                self._loop_count += 1
                self._current_frame_index = 0
            else:
                logger.debug("EOF reached for non-looping source '%s'.", self._video_path)
                return False, None
                
        if ok:
            self._current_frame_index += 1
            
        return ok, frame

    def read_packet(self) -> FramePacket:
        """Reads the next frame and bundles it with detailed sync metadata in a FramePacket."""
        ok, frame = self.read()
        
        # Timestamp based on frame index and fps (monotonic simulation time)
        if ok:
            idx = self._current_frame_index - 1
            source_timestamp_ms = (idx * 1000.0) / self._fps
        else:
            idx = -1
            source_timestamp_ms = 0.0
            
        return FramePacket(
            ok=ok,
            frame=frame,
            frame_index=idx,
            loop_count=self._loop_count,
            source_timestamp_ms=source_timestamp_ms,
            width=self._width,
            height=self._height,
        )

    def close(self) -> None:
        """Idempotently releases standard OpenCV video capture resources."""
        if self._is_open:
            self._cap.release()
            self._is_open = False
            logger.info("Closed video feed for source '%s'", self._video_path)

    def __enter__(self) -> "VideoFileFeed":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        """Checks if the video reader is open."""
        return self._is_open

    @property
    def video_path(self) -> Path:
        """Path of the target video source file."""
        return self._video_path

    @property
    def width(self) -> int:
        """Width of the video frames."""
        return self._width

    @property
    def height(self) -> int:
        """Height of the video frames."""
        return self._height

    @property
    def fps(self) -> float:
        """Frames per second of the video feed."""
        return self._fps

    @property
    def frame_count(self) -> int:
        """Total frame count of the video source."""
        return self._frame_count

    @property
    def current_frame_index(self) -> int:
        """The 0-based index of the next frame to be read."""
        return self._current_frame_index

    @property
    def loop_count(self) -> int:
        """The total number of loop iterations completed."""
        return self._loop_count


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Hawk-AI Video Stream Demo Generation Utility"
    )
    parser.add_argument(
        "--generate-demo",
        action="store_true",
        help="Generate a synthetic 1080p demo video clip"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".media/traffic_sample.mp4",
        help="Output path for the generated file"
    )
    
    args = parser.parse_args()
    
    if args.generate_demo:
        # Standard logging format to stdout
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
        out_path = Path(args.output)
        try:
            generate_synthetic_traffic_video(out_path)
            print(f"SUCCESS: Synthetic traffic video created at {out_path.resolve()}")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: Failed to generate video: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
