"""Security validation tests."""
import subprocess
import sys

import pytest


@pytest.mark.slow
def test_no_known_vulnerabilities():
    """Run pip-audit to check for known vulnerabilities."""
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--skip-editable"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Vulnerabilities found:\n{result.stdout}"
