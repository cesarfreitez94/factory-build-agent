import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from fba.state import StateManager


def test_atomic_write_success(tmp_path):
    dest = tmp_path / "test.json"
    content = '{"key": "value"}'

    from fba.state import _atomic_write

    _atomic_write(dest, content)

    assert dest.exists()
    assert dest.read_text() == content


def test_atomic_write_original_intact_on_write_failure(tmp_path):
    dest = tmp_path / "test.json"
    original_content = '{"original": true}'
    dest.write_text(original_content)

    from fba.state import _atomic_write

    original_replace = os.replace

    def failing_replace(src, dst):
        raise OSError("simulated os.replace failure")

    try:
        os.replace = failing_replace
        with pytest.raises(OSError, match="simulated os.replace failure"):
            _atomic_write(dest, '{"new": "content"}')
    finally:
        os.replace = original_replace

    assert dest.read_text() == original_content


def test_atomic_write_directory_created(tmp_path):
    dest = tmp_path / "subdir" / "nested" / "test.json"
    content = '{"deep": "nested"}'

    from fba.state import _atomic_write

    assert not dest.parent.exists()
    _atomic_write(dest, content)
    assert dest.exists()
    assert dest.read_text() == content


def test_atomic_write_temp_cleaned_on_failure(tmp_path):
    dest = tmp_path / "test.json"
    dest.write_text('{"original": true}')

    from fba.state import _atomic_write

    original_replace = os.replace

    def replace_but_check_temp(src, dst):
        raise OSError("simulated failure")

    try:
        os.replace = replace_but_check_temp
        with pytest.raises(OSError):
            _atomic_write(dest, '{"new": "content"}')
    finally:
        os.replace = original_replace

    json_files = list(dest.parent.glob("*.json*"))
    for f in json_files:
        assert not f.name.startswith(".tmp"), f"Temp file not cleaned: {f.name}"


def test_state_manager_save_uses_atomic_write(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state_path = factory_dir / "state.json"
    initial_state = {"current_phase": "init", "phases": {"init": {"status": "in_progress"}}}
    state_path.write_text(json.dumps(initial_state, indent=2))

    sm = StateManager(tmp_path)
    new_state = {"current_phase": "elicitation", "phases": {"init": {"status": "complete"}, "elicitation": {"status": "in_progress"}}}

    from fba.state import _atomic_write as original_atomic_write
    call_count = [0]
    called_with = [None, None]

    def mock_atomic_write(dest, content):
        call_count[0] += 1
        called_with[0] = dest
        called_with[1] = content
        original_atomic_write(dest, content)

    with patch("fba.state._atomic_write", side_effect=mock_atomic_write):
        sm.save(new_state)

    assert call_count[0] == 1
    assert called_with[0] == state_path
    parsed = json.loads(called_with[1])
    assert parsed["current_phase"] == "elicitation"


def test_record_event_uses_append_with_fsync(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state_path = factory_dir / "state.json"
    state_path.write_text(json.dumps({"current_phase": "init"}))

    sm = StateManager(tmp_path)

    events_path = sm.events_path
    with patch("os.fsync") as mock_fsync:
        sm.record_event("test_event", {"key": "value"})

    assert events_path.exists()
    content = events_path.read_text().strip()
    assert content
    parsed = json.loads(content)
    assert parsed["type"] == "test_event"
    assert parsed["data"] == {"key": "value"}


def test_state_manager_save_does_not_leave_temp_files(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state_path = factory_dir / "state.json"
    state_path.write_text(json.dumps({"current_phase": "init"}))

    sm = StateManager(tmp_path)
    sm.save({"current_phase": "elicitation"})

    temp_files = list(factory_dir.glob(".tmp*"))
    assert len(temp_files) == 0, f"Temp files left: {[f.name for f in temp_files]}"


def test_concurrent_writes_no_corruption(tmp_path):
    dest = tmp_path / "concurrent.json"
    dest.write_text(json.dumps({"initial": True}))

    from fba.state import _atomic_write

    original_replace = os.replace
    stages = {"rename_count": 0, "allow": False}

    def staged_replace(src, dst):
        stages["rename_count"] += 1
        if not stages["allow"]:
            raise OSError("simulated race: rename failed")
        original_replace(src, dst)

    try:
        os.replace = staged_replace
        with pytest.raises(OSError):
            _atomic_write(dest, json.dumps({"corrupted": "partial"}))

        assert dest.read_text() == json.dumps({"initial": True})
    finally:
        os.replace = original_replace
