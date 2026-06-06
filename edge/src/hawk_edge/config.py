"""Edge device configuration."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EdgeConfig:
    frame_width: int = 1920
    frame_height: int = 1080
    target_fps: int = 15
    buffer_seconds: int = 5
    buffer_capacity: int = 15
    queue_timeout_factor: float = 1.5
    data_dir: Path = field(default_factory=lambda: Path("data"))
    db_path: Path = field(default_factory=lambda: Path("data/hawk.db"))
