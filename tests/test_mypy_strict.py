"""Test that mypy strict mode passes on src/fba/.

This test validates that the mypy --strict check passes without errors.
It runs mypy programmatically and asserts success.
"""

import subprocess
import sys
from pathlib import Path


def test_mypy_strict_passes():
    """Verify mypy --strict passes on src/fba/ with no errors."""
    src_dir = Path(__file__).parent.parent / "src" / "fba"
    result = subprocess.run(
        [sys.executable, "-m", "mypy", str(src_dir), "--strict"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"mypy --strict failed on src/fba/\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_mypy_config_respects_strict():
    """Verify pyproject.toml [tool.mypy] config is properly set."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()

    assert "[tool.mypy]" in content, "Missing [tool.mypy] section in pyproject.toml"
    assert 'strict = true' in content, "Missing strict = true in [tool.mypy]"
    assert 'exclude = ["vendor/"]' in content or 'exclude = ["vendor/"]\n' in content, (
        "Missing exclude = [\"vendor/\"] in [tool.mypy]"
    )
