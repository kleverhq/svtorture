"""Bounded, timeout-safe process execution with full-stream hashes."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import BinaryIO

from svtorture.models import RawOutcome


@dataclass(frozen=True)
class StreamCapture:
    data: bytes
    size_bytes: int
    sha256: str
    truncated: bool


class _Collector:
    def __init__(self, limit: int, full_output_path: Path | None = None) -> None:
        self.limit = limit
        self.size = 0
        self.digest = hashlib.sha256()
        self.head = bytearray()
        self.tail = bytearray()
        self.head_limit = limit // 2
        self.tail_limit = limit - self.head_limit
        self.full_stream = None
        if full_output_path is not None:
            full_output_path.parent.mkdir(parents=True, exist_ok=True)
            self.full_stream = full_output_path.open("wb")

    def consume(self, chunk: bytes) -> None:
        if self.full_stream is not None:
            self.full_stream.write(chunk)
        self.size += len(chunk)
        self.digest.update(chunk)
        if len(self.head) < self.head_limit:
            take = min(self.head_limit - len(self.head), len(chunk))
            self.head.extend(chunk[:take])
            chunk = chunk[take:]
        if chunk and self.tail_limit:
            self.tail.extend(chunk)
            if len(self.tail) > self.tail_limit:
                del self.tail[: len(self.tail) - self.tail_limit]

    def finish(self) -> StreamCapture:
        if self.full_stream is not None:
            self.full_stream.flush()
            self.full_stream.close()
        truncated = self.size > self.limit
        if truncated:
            data = bytes(self.head) + b"\n...<SVTORTURE_OUTPUT_TRUNCATED>...\n" + bytes(self.tail)
        else:
            data = bytes(self.head) + bytes(self.tail)
        return StreamCapture(
            data=data,
            size_bytes=self.size,
            sha256=self.digest.hexdigest(),
            truncated=truncated,
        )


@dataclass(frozen=True)
class ProcessResult:
    outcome: RawOutcome
    exit_code: int | None
    signal: int | None
    duration_seconds: float
    stdout: StreamCapture
    stderr: StreamCapture
    launch_error: str | None = None


def _drain(stream: BinaryIO, collector: _Collector) -> None:
    try:
        while chunk := stream.read(16384):
            collector.consume(chunk)
    finally:
        stream.close()


def _empty_capture() -> StreamCapture:
    return StreamCapture(
        data=b"",
        size_bytes=0,
        sha256=hashlib.sha256(b"").hexdigest(),
        truncated=False,
    )


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    output_bytes: int,
    environment: Mapping[str, str] | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> ProcessResult:
    """Run argv without a shell, terminate its process group, and bound retained output."""

    start = time.monotonic()
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=None if environment is None else dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as error:
        return ProcessResult(
            outcome=RawOutcome.LAUNCH_FAILURE,
            exit_code=None,
            signal=None,
            duration_seconds=time.monotonic() - start,
            stdout=_empty_capture(),
            stderr=_empty_capture(),
            launch_error=f"{type(error).__name__}: {error}",
        )

    assert process.stdout is not None
    assert process.stderr is not None
    stdout_collector = _Collector(output_bytes, stdout_path)
    stderr_collector = _Collector(output_bytes, stderr_path)
    stdout_thread = Thread(target=_drain, args=(process.stdout, stdout_collector), daemon=True)
    stderr_thread = Thread(target=_drain, args=(process.stderr, stderr_collector), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            return_code = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            return_code = process.wait()

    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    duration = time.monotonic() - start
    stdout = stdout_collector.finish()
    stderr = stderr_collector.finish()
    if timed_out:
        return ProcessResult(
            outcome=RawOutcome.TIMEOUT,
            exit_code=None,
            signal=None,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
        )
    if return_code < 0:
        return ProcessResult(
            outcome=RawOutcome.SIGNAL,
            exit_code=None,
            signal=-return_code,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
        )
    return ProcessResult(
        outcome=RawOutcome.NORMAL_EXIT,
        exit_code=return_code,
        signal=None,
        duration_seconds=duration,
        stdout=stdout,
        stderr=stderr,
    )
