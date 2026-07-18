from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from svtorture.models import RawOutcome
from svtorture.process import run_process


def test_process_capture_is_bounded_but_hashes_full_stream(tmp_path: Path) -> None:
    payload_size = 20_000
    full_log = tmp_path / "stdout.log"
    result = run_process(
        [
            sys.executable,
            "-c",
            f"import sys; sys.stdout.write('x' * {payload_size})",
        ],
        cwd=tmp_path,
        timeout_seconds=5,
        output_bytes=1024,
        stdout_path=full_log,
    )
    assert result.outcome is RawOutcome.NORMAL_EXIT
    assert result.stdout.truncated
    assert result.stdout.size_bytes == payload_size
    assert result.stdout.sha256 == hashlib.sha256(b"x" * payload_size).hexdigest()
    assert full_log.stat().st_size == payload_size


def test_process_timeout_is_not_a_normal_exit(tmp_path: Path) -> None:
    result = run_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        timeout_seconds=1,
        output_bytes=1024,
    )
    assert result.outcome is RawOutcome.TIMEOUT
    assert result.exit_code is None
