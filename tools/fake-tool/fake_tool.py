#!/usr/bin/env python3
"""Deterministic fake compiler/simulator used by SVTORTURE integration tests."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import sys
import time


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--version", action="store_true")
    result.add_argument("--action", choices=("compile", "run"))
    result.add_argument("--case")
    result.add_argument("--phase")
    result.add_argument("--expectation")
    result.add_argument("--anchor-line", type=int, default=1)
    result.add_argument("--marker", default="-")
    result.add_argument("--scenario", default="conform")
    result.add_argument("--artifact")
    return result


def diagnostic(arguments: argparse.Namespace, *, target: bool = True) -> None:
    line = arguments.anchor_line if target else arguments.anchor_line + 7
    severity = "warning" if arguments.expectation == "diagnostic" else "error"
    print(
        f"/case/top.sv:{line}: {severity}: fake diagnostic for {arguments.case}",
        file=sys.stderr,
        flush=True,
    )


def main() -> int:
    arguments = parser().parse_args()
    if arguments.version:
        print("svtorture-fake-tool 1.0")
        return 0
    if not all(
        (
            arguments.action,
            arguments.case,
            arguments.phase,
            arguments.expectation,
            arguments.artifact,
        )
    ):
        return 2
    target_action = "run" if arguments.phase == "simulate" else "compile"
    active = arguments.action == target_action
    if active and arguments.scenario == "timeout":
        time.sleep(3600)
    if active and arguments.scenario == "crash":
        os.kill(os.getpid(), signal.SIGSEGV)
    if active and arguments.scenario == "internal-error":
        print("internal compiler error: synthetic fault", file=sys.stderr)
        return 1
    if active and arguments.scenario == "unrelated":
        print(
            "/case/unrelated.sv:1: error: synthetic unrelated failure",
            file=sys.stderr,
            flush=True,
        )
        return 1
    if active and arguments.scenario == "wrong-location":
        diagnostic(arguments, target=False)
        return 1

    if arguments.action == "compile" and arguments.phase == "simulate":
        if arguments.scenario != "missing-artifact":
            Path(arguments.artifact).write_text("fake artifact\n", encoding="utf-8")
        return 0

    if arguments.action == "compile":
        if arguments.expectation == "reject":
            diagnostic(arguments)
            return 1
        if arguments.expectation == "diagnostic":
            diagnostic(arguments)
        return 0

    if arguments.scenario == "missing-marker":
        return 0
    if arguments.scenario == "marker-nonzero":
        if arguments.marker != "-":
            print(arguments.marker)
        return 1
    if arguments.scenario == "wrong-runtime":
        print("FATAL: synthetic wrong runtime value", file=sys.stderr)
        return 1
    if arguments.expectation == "diagnostic":
        diagnostic(arguments)
    if arguments.marker != "-":
        print(arguments.marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
