"""Mock GPS Daemon server streaming NMEA sentences over virtual serial (PTY) or TCP."""
import contextlib
import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path

from hawk_edge.gps.emulator import RouteEmulator
from hawk_edge.gps.nmea import telemetry_to_gpgga, telemetry_to_gprmc

logger = logging.getLogger(__name__)


class GpsDaemon:
    """Mock GPS Daemon server streaming NMEA sentences.

    On Linux/macOS, it emulates a serial port via a pseudo-terminal (PTY).
    On Windows, it emulates a serial port via a TCP server (localhost:9500).
    """

    def __init__(
        self,
        route_path: Path,
        mode: str = "auto",
        host: str = "127.0.0.1",
        port: int = 9500,
        seed: int | None = None,
        dt: float = 1.0,
    ) -> None:
        self.route_path = route_path
        self.host = host
        self.port = port
        self.seed = seed
        self.dt = dt

        self.mode = self._resolve_mode(mode)
        self.emulator = RouteEmulator(route_path=route_path, seed=seed, time_step=dt)

        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

        # Socket and File Descriptor states
        self.server_socket: socket.socket | None = None
        self.master_fd: int | None = None
        self.slave_fd: int | None = None
        self.connection_string: str = ""

    def _resolve_mode(self, mode: str) -> str:
        if mode == "auto":
            return "pty" if sys.platform != "win32" else "tcp"
        return mode

    def __enter__(self) -> "GpsDaemon":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.stop()

    def start(self) -> str:
        """Start the streaming daemon.

        Returns:
            The connection address/port or virtual PTY path.
        """
        self._stop_event.clear()
        if self.mode == "pty":
            return self._start_pty()
        else:
            return self._start_tcp()

    def _start_pty(self) -> str:
        # Import pty dynamically to support cross-platform parsing
        import pty

        master, slave = pty.openpty()  # type: ignore[attr-defined]
        self.master_fd = master
        self.slave_fd = slave
        self.connection_string = os.ttyname(slave)  # type: ignore[attr-defined]

        logger.info("Starting GPS Daemon in PTY mode on %s", self.connection_string)

        t = threading.Thread(target=self._pty_stream_loop, daemon=True)
        t.start()
        self._threads.append(t)

        return self.connection_string

    def _start_tcp(self) -> str:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        # Retrieve ephemeral port if bound to 0
        self.port = self.server_socket.getsockname()[1]
        self.connection_string = f"socket://{self.host}:{self.port}"

        logger.info("Starting GPS Daemon in TCP mode on %s", self.connection_string)

        t = threading.Thread(target=self._tcp_accept_loop, daemon=True)
        t.start()
        self._threads.append(t)

        return self.connection_string

    def _pty_stream_loop(self) -> None:
        try:
            for telemetry in self.emulator:
                if self._stop_event.is_set():
                    break

                sentences = telemetry_to_gprmc(telemetry) + telemetry_to_gpgga(telemetry)
                try:
                    assert self.master_fd is not None
                    os.write(self.master_fd, sentences.encode("utf-8"))
                except OSError as e:
                    logger.debug("PTY write error (no client connected yet?): %s", e)

                self._stop_event.wait(timeout=self.dt)
        except Exception as e:
            logger.error("Error in PTY stream loop: %s", e)
        finally:
            self.stop()

    def _tcp_accept_loop(self) -> None:
        assert self.server_socket is not None
        self.server_socket.settimeout(0.5)
        while not self._stop_event.is_set():
            try:
                client_sock, addr = self.server_socket.accept()
                logger.info("Client connected to GPS Daemon: %s", addr)
                t = threading.Thread(
                    target=self._tcp_client_stream, args=(client_sock,), daemon=True
                )
                t.start()
                self._threads.append(t)
            except TimeoutError:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error("Error accepting connections: %s", e)
                break

    def _tcp_client_stream(self, client_sock: socket.socket) -> None:
        client_sock.settimeout(1.0)
        try:
            for telemetry in self.emulator:
                if self._stop_event.is_set():
                    break

                sentences = telemetry_to_gprmc(telemetry) + telemetry_to_gpgga(telemetry)
                client_sock.sendall(sentences.encode("utf-8"))

                self._stop_event.wait(timeout=self.dt)
        except (OSError, ConnectionResetError, BrokenPipeError) as e:
            logger.info("Client disconnected: %s", e)
        except Exception as e:
            logger.error("Error in TCP client stream: %s", e)
        finally:
            with contextlib.suppress(Exception):
                client_sock.close()

    def stop(self) -> None:
        """Signal and stop the daemon, closing open handles."""
        self._stop_event.set()

        # Close TCP sockets
        if self.server_socket:
            with contextlib.suppress(Exception):
                self.server_socket.close()
            self.server_socket = None

        # Close PTY file descriptors
        if self.master_fd is not None:
            with contextlib.suppress(Exception):
                os.close(self.master_fd)
            self.master_fd = None

        if self.slave_fd is not None:
            with contextlib.suppress(Exception):
                os.close(self.slave_fd)
            self.slave_fd = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    route = (
        Path(__file__).parent.parent / "sim" / "routes" / "bengaluru_commute.toml"
    )

    daemon = GpsDaemon(route_path=route, seed=42)
    address = daemon.start()

    print("\n=========================================")
    print(f"Hawk-AI GPS Daemon Running in {daemon.mode.upper()} mode")
    print(f"Connect to: {address}")
    print("=========================================\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down daemon...")
        daemon.stop()
        print("Stopped.")
