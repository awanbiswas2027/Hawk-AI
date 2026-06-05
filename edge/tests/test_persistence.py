"""Tests for SQLite database persistence buffer."""
import concurrent.futures
import sqlite3
from pathlib import Path

import pytest

from hawk_edge.persistence import SQLiteBuffer, ViolationEvent


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture to provide a clean temporary database path."""
    return tmp_path / "test_hawk.db"


def test_sqlite_buffer_initialization(temp_db_path: Path) -> None:
    """Test that SQLiteBuffer initializes correctly and creates the schema."""
    assert not temp_db_path.exists()

    with SQLiteBuffer(temp_db_path):
        assert temp_db_path.exists()
        # Verify database is active and schema matches
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='offline_events';"
        )
        assert cursor.fetchone() is not None
        conn.close()

    # Verify release alias behaves identically
    db2 = SQLiteBuffer(temp_db_path)
    db2.release()


def test_sqlite_buffer_invalid_path(tmp_path: Path) -> None:
    """Test that initialization with an invalid path fails gracefully."""
    # Attempting to initialize with a directory path as the database file should fail
    invalid_path = tmp_path / "is_a_directory"
    invalid_path.mkdir()
    with pytest.raises(sqlite3.OperationalError):
        SQLiteBuffer(invalid_path)



def test_sqlite_buffer_crud_operations(temp_db_path: Path) -> None:
    """Test standard Event save, pending retrieve, and mark synced flow."""
    event = ViolationEvent(
        device_uuid="test-uuid-1",
        timestamp="2026-06-05T12:00:00Z",
        latitude=12.9716,
        longitude=77.5946,
        violation_type="NO_HELMET",
        confidence=0.92,
        image_blob=b"fake_jpeg_bytes",
        speed=45.5,
    )

    with SQLiteBuffer(temp_db_path) as db:
        # Check initial pending
        assert len(db.get_pending_events()) == 0

        # Save event
        assert db.save_event(event) is True
        assert event.id is not None
        assert event.id == 1

        # Retrieve pending event
        pending = db.get_pending_events()
        assert len(pending) == 1
        retrieved = pending[0]
        assert retrieved.id == event.id
        assert retrieved.device_uuid == event.device_uuid
        assert retrieved.timestamp == event.timestamp
        assert retrieved.latitude == event.latitude
        assert retrieved.longitude == event.longitude
        assert retrieved.violation_type == event.violation_type
        assert retrieved.confidence == event.confidence
        assert retrieved.image_blob == event.image_blob
        assert retrieved.speed == event.speed
        assert retrieved.sync_status == 0

        # Mark synced
        assert db.mark_synced(event.id) is True
        assert len(db.get_pending_events()) == 0


def test_sqlite_buffer_eviction_oldest_pending(temp_db_path: Path) -> None:
    """Test circular eviction: oldest pending event is evicted when database is full."""
    # Capacity = 3
    with SQLiteBuffer(temp_db_path, capacity=3) as db:
        events = [
            ViolationEvent(
                device_uuid=f"dev-{i}",
                timestamp=f"2026-06-05T12:00:0{i}Z",
                latitude=12.0,
                longitude=77.0,
                violation_type="NO_HELMET",
                confidence=0.8,
                image_blob=bytes([i]),
            )
            for i in range(1, 5)
        ]

        # Save first 3 events
        assert db.save_event(events[0]) is True  # ID 1
        assert db.save_event(events[1]) is True  # ID 2
        assert db.save_event(events[2]) is True  # ID 3

        pending = db.get_pending_events()
        assert len(pending) == 3
        assert [e.id for e in pending] == [1, 2, 3]

        # Save 4th event (triggers eviction of absolute oldest: ID 1)
        assert db.save_event(events[3]) is True  # ID 4
        
        pending_after = db.get_pending_events()
        assert len(pending_after) == 3
        # ID 1 should be gone, IDs 2, 3, 4 remain
        assert [e.id for e in pending_after] == [2, 3, 4]


def test_sqlite_buffer_eviction_synced_first(temp_db_path: Path) -> None:
    """Test circular eviction: synced events are evicted before pending events."""
    with SQLiteBuffer(temp_db_path, capacity=3) as db:
        events = [
            ViolationEvent(
                device_uuid=f"dev-{i}",
                timestamp=f"2026-06-05T12:00:0{i}Z",
                latitude=12.0,
                longitude=77.0,
                violation_type="NO_HELMET",
                confidence=0.8,
                image_blob=bytes([i]),
            )
            for i in range(1, 5)
        ]

        # Save first 3 events
        assert db.save_event(events[0]) is True  # ID 1
        assert db.save_event(events[1]) is True  # ID 2
        assert db.save_event(events[2]) is True  # ID 3

        # Mark ID 2 as synced
        assert db.mark_synced(2) is True

        # Save 4th event (triggers eviction. ID 2 is synced, so evict it first)
        assert db.save_event(events[3]) is True  # ID 4

        # Verify remaining events: ID 2 should be evicted; IDs 1, 3, 4 remain.
        pending = db.get_pending_events()
        assert len(pending) == 3
        assert [e.id for e in pending] == [1, 3, 4]


def test_sqlite_buffer_thread_safety(temp_db_path: Path) -> None:
    """Test that concurrent saves from multiple threads complete successfully without locks."""
    num_threads = 8
    events_per_thread = 15

    with SQLiteBuffer(temp_db_path, capacity=200) as db:
        def worker(thread_idx: int) -> None:
            for _i in range(events_per_thread):
                event = ViolationEvent(
                    device_uuid=f"thread-{thread_idx}",
                    timestamp="2026-06-05T12:00:00Z",
                    latitude=12.0,
                    longitude=77.0,
                    violation_type="NO_HELMET",
                    confidence=0.85,
                    image_blob=b"bytes",
                )
                assert db.save_event(event) is True

        # Launch concurrent worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, idx) for idx in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                # Raise any exceptions from workers
                future.result()

        # Check total events saved
        pending = db.get_pending_events()
        assert len(pending) == num_threads * events_per_thread


def test_sqlite_buffer_closed_operations(temp_db_path: Path) -> None:
    """Test that operations on a closed SQLiteBuffer raise RuntimeError."""
    db = SQLiteBuffer(temp_db_path)
    db.close()

    event = ViolationEvent(
        device_uuid="test-uuid",
        timestamp="2026-06-05T12:00:00Z",
        latitude=12.0,
        longitude=77.0,
        violation_type="NO_HELMET",
        confidence=0.8,
        image_blob=b"bytes",
    )

    with pytest.raises(RuntimeError):
        db.save_event(event)

    with pytest.raises(RuntimeError):
        db.get_pending_events()

    with pytest.raises(RuntimeError):
        db.mark_synced(1)
