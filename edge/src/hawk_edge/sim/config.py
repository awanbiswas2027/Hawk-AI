"""Configuration resolution for simulation media."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyntheticVideoConfig:
    """Configuration for synthetic video generation."""
    duration_sec: int = 5
    fps: int = 15
    width: int = 1920
    height: int = 1080
    seed: int = 42
    codec: str = "mp4v"


def get_media_dir() -> Path:
    """Resolve media directory.
    
    Checks HAWK_SIM_MEDIA_DIR env variable, falling back to a `.media` folder
    at the repository root directory.
    """
    env_dir = os.getenv("HAWK_SIM_MEDIA_DIR")
    if env_dir:
        return Path(env_dir)
    
    # Try resolving relative to package files first
    try:
        project_root = Path(__file__).resolve().parents[4]
        return project_root / ".media"
    except IndexError:
        return Path(".media").resolve()


def get_default_codec() -> str:
    """Get the default video codec for simulation generation."""
    return os.getenv("HAWK_SIM_VIDEO_CODEC", "mp4v")


def should_autogenerate_media() -> bool:
    """Check if simulation media should be auto-generated if missing."""
    env_val = os.getenv("HAWK_SIM_AUTOGENERATE_MEDIA", "false").lower()
    return env_val in ("true", "1", "yes")
