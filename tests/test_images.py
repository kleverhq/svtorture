from __future__ import annotations

import subprocess
from typing import Any

from pytest import MonkeyPatch

from svtorture.images import _run


def test_verbose_image_command_inherits_console(monkeypatch: MonkeyPatch) -> None:
    invocation: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        invocation.update(kwargs)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _run(["docker", "build"], verbose=True) == ""
    assert invocation["stdout"] is None
    assert invocation["stderr"] is None


def test_compact_image_command_captures_combined_output(monkeypatch: MonkeyPatch) -> None:
    invocation: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        invocation.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="build output")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _run(["docker", "build"]) == "build output"
    assert invocation["stdout"] is subprocess.PIPE
    assert invocation["stderr"] is subprocess.STDOUT
