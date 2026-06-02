"""Integration tests for GpsDaemon verifying TCP socket and PTY stream behaviors."""
import socket
import sys
import time
from pathlib import Path

import pynmea2
import pytest

from hawk_edge.gps.daemon import GpsDaemon


@pytest.fixture
def commute_route_path() -> Path:
    """Return path to default Bengaluru TOML commute route."""
    root_dir = Path(__file__).parent.parent
    route_file = "src/hawk_edge/sim/routes/bengaluru_commute.toml"
    return root_dir / route_file


def test_gps_daemon_tcp_mode(commute_route_path):
    """Verify TCP daemon binding on ephemeral ports, accepts client links, and streams NMEA."""
    # Bind to port 0 to let the OS assign a free ephemeral port
    with GpsDaemon(
        route_path=commute_route_path, mode="tcp", port=0, seed=42, dt=0.01
    ) as daemon:
        assert daemon.mode == "tcp"
        assert daemon.port > 0
        assert daemon.connection_string.startswith("socket://127.0.0.1:")

        # Connect client socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", daemon.port))
        client.settimeout(2.0)

        # Buffer incoming streams
        data = b""
        start_time = time.time()
        while len(data) < 200 and (time.time() - start_time) < 2.0:
            chunk = client.recv(1024)
            if not chunk:
                break
            data += chunk

        client.close()

        # Check gathered sentences
        assert len(data) > 0
        lines = data.decode("utf-8", errors="ignore").split("\r\n")
        sentences = [line for line in lines if line.strip()]

        assert len(sentences) >= 2

        # Verify first items are parsed correctly by pynmea2
        parsed_rmc = pynmea2.parse(sentences[0])
        assert isinstance(parsed_rmc, pynmea2.types.talker.RMC)
        assert 12.8 <= parsed_rmc.latitude <= 13.1
        assert 77.4 <= parsed_rmc.longitude <= 77.8


@pytest.mark.skipif(sys.platform == "win32", reason="PTY mode only supported on Unix/macOS")
def test_gps_daemon_pty_mode(commute_route_path):
    """Verify PTY daemon initializes virtual serial paths and handles streaming."""
    with GpsDaemon(
        route_path=commute_route_path, mode="pty", seed=42, dt=0.01
    ) as daemon:
        assert daemon.mode == "pty"
        assert daemon.master_fd is not None
        assert daemon.slave_fd is not None
        assert daemon.connection_string.startswith("/dev/")

        # Verify we can read characters from the master FD
        import os

        data = os.read(daemon.master_fd, 200)
        assert len(data) > 0

        lines = data.decode("utf-8", errors="ignore").split("\r\n")
        sentences = [line for line in lines if line.strip()]
        assert len(sentences) >= 1
        assert sentences[0].startswith("$")
