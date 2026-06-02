"""Day 1 smoke tests: validate core dependencies and compatibility."""
import sys


class TestEnvironment:
    """Validate the Python environment is correctly configured."""

    def test_python_version(self):
        assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"

    def test_virtual_environment_active(self):
        assert sys.prefix != sys.base_prefix, "Not running inside a virtual environment"


class TestCoreDependencies:
    """Validate Day 1 core dependencies."""

    def test_opencv_import(self):
        import cv2
        assert cv2.__version__, "OpenCV version not available"

    def test_numpy_import(self):
        import numpy as np
        assert np.__version__, "NumPy version not available"

    def test_opencv_numpy_compatibility(self):
        """Verify OpenCV and NumPy work together correctly."""
        import cv2
        import numpy as np

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        assert gray.shape == (100, 100)
        assert gray.dtype == np.uint8

    def test_opencv_video_codec_support(self):
        """Verify OpenCV has video codec support (needed for Day 3)."""
        import cv2
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        assert fourcc != 0, "MP4 codec not available"


class TestPackageStructure:
    """Validate project package structure."""

    def test_hawk_edge_importable(self):
        import hawk_edge
        assert hawk_edge.__version__ == "0.1.0"

    def test_config_importable(self):
        from hawk_edge.config import EdgeConfig
        config = EdgeConfig()
        assert config.target_fps == 15
