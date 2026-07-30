from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from threading import Event, Thread

import pytest

import svtorture.process as process_module
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


def _ignoring_child_code(child_pid_path: Path) -> str:
    return (
        "import os, signal, time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(child_pid_path)!r}).write_text(str(os.getpid())); "
        "time.sleep(30)"
    )


def _assert_child_stopped(child_pid_path: Path) -> None:
    child_pid = child_pid_path.read_text(encoding="utf-8")
    child_status = Path(f"/proc/{child_pid}/stat")
    if child_status.exists():
        assert child_status.read_text(encoding="utf-8").split()[2] == "Z"


def test_process_cancellation_terminates_the_process_group(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    child_code = _ignoring_child_code(child_pid_path)
    parent_code = (
        "import subprocess, time; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {child_code!r}]); "
        "time.sleep(30)"
    )
    cancel_event = Event()

    def cancel_after_child_starts() -> None:
        deadline = time.monotonic() + 2
        while not child_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        cancel_event.set()

    canceller = Thread(target=cancel_after_child_starts)
    canceller.start()
    started = time.monotonic()
    with pytest.raises(process_module.ProcessCancelled):
        run_process(
            [sys.executable, "-c", parent_code],
            cwd=tmp_path,
            timeout_seconds=30,
            output_bytes=1024,
            cancel_event=cancel_event,
        )
    canceller.join()
    assert time.monotonic() - started < 4
    _assert_child_stopped(child_pid_path)


def test_cancellation_cleans_up_descendants_after_the_leader_exits(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "orphan.pid"
    child_code = _ignoring_child_code(child_pid_path)
    parent_code = (
        "import subprocess, time; from pathlib import Path; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {child_code!r}]); "
        f"path = Path({str(child_pid_path)!r}); "
        "\nwhile not path.exists(): time.sleep(0.01)"
    )
    cancel_event = Event()

    def cancel_after_parent_exits() -> None:
        while not child_pid_path.exists():
            time.sleep(0.01)
        time.sleep(0.1)
        cancel_event.set()

    canceller = Thread(target=cancel_after_parent_exits)
    canceller.start()
    started = time.monotonic()
    with pytest.raises(process_module.ProcessCancelled):
        run_process(
            [sys.executable, "-c", parent_code],
            cwd=tmp_path,
            timeout_seconds=30,
            output_bytes=1024,
            cancel_event=cancel_event,
        )
    canceller.join()
    assert time.monotonic() - started < 4
    _assert_child_stopped(child_pid_path)
