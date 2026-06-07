"""SQLite offline persistence buffer for caching traffic violations."""
import contextlib
import logging
import queue
import shutil
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Self

from hawk_edge.config import EdgeConfig
from hawk_edge.persistence.types import ViolationEvent

logger = logging.getLogger(__name__)


class InsertEventTask:
    """Task to insert a ViolationEvent with circular eviction checks."""

    def __init__(self, event: ViolationEvent, capacity: int) -> None:
        self.event = event
        self.capacity = capacity
        self.response_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()

    def execute(self, conn: sqlite3.Connection, current_count: int) -> tuple[int, int]:
        """Execute the insert task inside a transaction context.

        Returns a tuple of (inserted_row_id, updated_current_count).
        """
        cursor = conn.cursor()

        if current_count >= self.capacity:
            # Try to find a synced event to evict first
            cursor.execute(
                "SELECT id FROM offline_events WHERE sync_status = 1 ORDER BY id ASC LIMIT 1"
            )
            row = cursor.fetchone()
            if row is not None:
                evict_id = row[0]
                logger.warning("Database capacity reached. Evicting synced event ID: %s", evict_id)
            else:
                # Evict the oldest pending event (smallest ID)
                cursor.execute("SELECT id FROM offline_events ORDER BY id ASC LIMIT 1")
                row = cursor.fetchone()
                evict_id = row[0] if row is not None else None
                logger.warning(
                    "Database capacity reached. Evicting oldest pending event ID: %s",
                    evict_id,
                )

            if evict_id is not None:
                cursor.execute("DELETE FROM offline_events WHERE id = ?", (evict_id,))
                current_count -= 1

        # Insert new event
        cursor.execute(
            """
            INSERT INTO offline_events (
                device_uuid, timestamp, latitude, longitude, speed,
                violation_type, confidence, image_blob, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.event.device_uuid,
                self.event.timestamp,
                self.event.latitude,
                self.event.longitude,
                self.event.speed,
                self.event.violation_type,
                self.event.confidence,
                self.event.image_blob,
                self.event.sync_status,
            ),
        )
        last_row_id = cursor.lastrowid
        if last_row_id is None:
            raise sqlite3.DatabaseError("Failed to retrieve lastrowid after INSERT.")
        current_count += 1
        return last_row_id, current_count


class GetPendingEventsTask:
    """Task to query all pending (unsynced) violation events."""

    def __init__(self) -> None:
        self.response_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()

    def execute(self, conn: sqlite3.Connection) -> list[ViolationEvent]:
        """Query and return pending events."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, device_uuid, timestamp, latitude, longitude, speed,
                   violation_type, confidence, image_blob, sync_status
            FROM offline_events
            WHERE sync_status = 0
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        events = []
        for row in rows:
            events.append(
                ViolationEvent(
                    id=row[0],
                    device_uuid=row[1],
                    timestamp=row[2],
                    latitude=row[3],
                    longitude=row[4],
                    speed=row[5],
                    violation_type=row[6],
                    confidence=row[7],
                    image_blob=row[8],
                    sync_status=row[9],
                )
            )
        return events


class MarkSyncedTask:
    """Task to mark a violation event as successfully synchronized to the cloud."""

    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        self.response_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()

    def execute(self, conn: sqlite3.Connection) -> bool:
        """Mark event as synced."""
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE offline_events SET sync_status = 1 WHERE id = ?",
            (self.event_id,)
        )
        return cursor.rowcount > 0


class MarkFailedTask:
    """Task to mark a violation event as failed/retry."""

    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        self.response_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()

    def execute(self, conn: sqlite3.Connection) -> bool:
        """Mark event as failed (sync_status = 2)."""
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE offline_events SET sync_status = 2 WHERE id = ?",
            (self.event_id,)
        )
        return cursor.rowcount > 0


class SQLiteBuffer:
    """Thread-safe SQLite database manager utilizing a background worker thread."""

    def __init__(
        self,
        db_path: Path | str,
        capacity: int = 2000,
        max_blob_size: int = 512 * 1024,
    ) -> None:
        self.db_path = Path(db_path)
        self.capacity = capacity
        self.max_blob_size = max_blob_size
        self._current_count = 0
        self._task_queue: queue.Queue[Any] = queue.Queue()
        self._stop_event = threading.Event()
        self._init_done = threading.Event()
        self._init_error: Exception | None = None

        # Ensure directory structure exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Spawn background writer thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="SQLiteBufferWorker",
            daemon=True,
        )
        self._worker_thread.start()

        # Wait for worker thread setup to complete
        if not self._init_done.wait(timeout=5.0):
            raise TimeoutError("SQLite database initialization timed out.")
        if self._init_error is not None:
            raise self._init_error

    def _worker_loop(self) -> None:
        """Background loop executing database tasks sequentially."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            # Initialize schema
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS offline_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_uuid TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        speed REAL,
                        violation_type TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        image_blob BLOB NOT NULL,
                        sync_status INTEGER DEFAULT 0
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_offline_events_sync_status_id 
                    ON offline_events (sync_status, id);
                    """
                )

            # Query initial in-memory count
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM offline_events")
            self._current_count = cursor.fetchone()[0]

        except Exception as e:
            self._init_error = e
            self._init_done.set()
            if conn is not None:
                conn.close()
            return

        self._init_done.set()

        last_checkpoint_time = time.time()
        inserts_since_checkpoint = 0

        while True:
            task = self._task_queue.get()
            if task is None:
                self._task_queue.task_done()
                break

            try:
                with conn:
                    if isinstance(task, InsertEventTask):
                        result, self._current_count = task.execute(conn, self._current_count)
                        inserts_since_checkpoint += 1
                    else:
                        result = task.execute(conn)
                        
                task.response_queue.put((True, result))
                
                # Periodic WAL checkpoint
                if inserts_since_checkpoint >= 100 or (time.time() - last_checkpoint_time) >= 60.0:
                    try:
                        conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
                        last_checkpoint_time = time.time()
                        inserts_since_checkpoint = 0
                    except Exception as checkpoint_err:
                        logger.error("Failed to execute WAL checkpoint: %s", checkpoint_err)

            except Exception as e:
                task.response_queue.put((False, e))
            finally:
                self._task_queue.task_done()

        conn.close()

    @classmethod
    def from_config(cls, config: EdgeConfig) -> "SQLiteBuffer":
        """Factory method to construct SQLiteBuffer from EdgeConfig."""
        return cls(
            db_path=config.db_path,
            capacity=config.db_capacity,
        )

    def has_free_space(self) -> bool:
        """Check if the target disk has at least 100 MB of free space."""
        try:
            usage = shutil.disk_usage(self.db_path.parent)
            free_mb = usage.free / (1024.0 * 1024.0)
            return free_mb >= 100.0
        except Exception as e:
            logger.warning("Failed to check disk usage: %s", e)
            return True  # Fallback to True if check fails

    def save_event(self, event: ViolationEvent) -> int | None:
        """Enqueue and execute a database write to save a violation event.

        Returns the auto-incremented event ID on success, or None on failure.
        Also updates the event's `id` attribute in-place for compatibility.
        """
        if self._stop_event.is_set():
            raise RuntimeError("Database buffer is closed.")

        if len(event.image_blob) > self.max_blob_size:
            raise ValueError(
                f"Image blob size ({len(event.image_blob)} bytes) exceeds maximum "
                f"configured limit ({self.max_blob_size} bytes)."
            )

        if not self.has_free_space():
            logger.error("Disk space is critically low (< 100 MB). Refusing to save event.")
            return None

        task = InsertEventTask(event, self.capacity)
        self._task_queue.put(task)

        success, result = task.response_queue.get()
        if success:
            assert isinstance(result, int)
            event.id = result
            return result
        else:
            logger.error("Failed to save event to database: %s", result)
            return None

    def get_pending_events(self) -> list[ViolationEvent]:
        """Retrieve all unsynced violation events (sync_status = 0) ordered by ID."""
        if self._stop_event.is_set():
            raise RuntimeError("Database buffer is closed.")

        task = GetPendingEventsTask()
        self._task_queue.put(task)

        success, result = task.response_queue.get()
        if success:
            assert isinstance(result, list)
            return result
        else:
            logger.error("Failed to retrieve pending events: %s", result)
            return []

    def mark_synced(self, event_id: int) -> bool:
        """Mark a specific event ID as synchronized (sync_status = 1)."""
        if self._stop_event.is_set():
            raise RuntimeError("Database buffer is closed.")

        task = MarkSyncedTask(event_id)
        self._task_queue.put(task)

        success, result = task.response_queue.get()
        if success:
            assert isinstance(result, bool)
            return result
        else:
            logger.error("Failed to mark event %s as synced: %s", event_id, result)
            return False

    def mark_failed(self, event_id: int) -> bool:
        """Mark a specific event ID as failed/retry (sync_status = 2)."""
        if self._stop_event.is_set():
            raise RuntimeError("Database buffer is closed.")

        task = MarkFailedTask(event_id)
        self._task_queue.put(task)

        success, result = task.response_queue.get()
        if success:
            assert isinstance(result, bool)
            return result
        else:
            logger.error("Failed to mark event %s as failed: %s", event_id, result)
            return False

    def close(self) -> None:
        """Shut down the background writer thread and close database resources."""
        if not self._stop_event.is_set():
            self._stop_event.set()
            with contextlib.suppress(Exception):
                self._task_queue.put(None)
            if self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)

    def release(self) -> None:
        """Alias for close() to match FrameProvider interface patterns."""
        self.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
