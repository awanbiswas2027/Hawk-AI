"""Type definitions for persistence."""
from dataclasses import dataclass


@dataclass
class ViolationEvent:
    """Represents a traffic violation event logged to offline storage."""

    device_uuid: str
    timestamp: str  # ISO-8601 UTC format
    latitude: float
    longitude: float
    violation_type: str
    confidence: float
    image_blob: bytes
    speed: float | None = None
    sync_status: int = 0  # 0 = pending, 1 = synced, 2 = failed_retry
    id: int | None = None  # Populated after database insertion
