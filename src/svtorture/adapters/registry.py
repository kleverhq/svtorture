"""Adapter factory driven by tool metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from svtorture.adapters.base import DiagnosticFallback, ToolAdapter
from svtorture.adapters.commercial import VcsAdapter
from svtorture.adapters.fake import FakeAdapter
from svtorture.adapters.open_source import IcarusAdapter, SlangAdapter, VerilatorAdapter


class AdapterError(ValueError):
    pass


def load_fallbacks(path: Path | None) -> tuple[DiagnosticFallback, ...]:
    if path is None or not path.exists():
        return ()
    try:
        with path.open("rb") as stream:
            data: dict[str, Any] = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AdapterError(f"cannot load diagnostic rules: {error}") from error
    if (
        set(data) != {"schema_version", "rules"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise AdapterError("diagnostic rules must use strict schema_version 1")
    rules = data["rules"]
    if not isinstance(rules, list):
        raise AdapterError("diagnostic rules must be an array")
    result: list[DiagnosticFallback] = []
    allowed = {"tool", "case", "contains", "severity"}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not set(rule) <= allowed:
            raise AdapterError(f"invalid diagnostic rule at index {index}")
        if not all(isinstance(rule.get(key), str) for key in ("tool", "case", "contains")):
            raise AdapterError(f"incomplete diagnostic rule at index {index}")
        if any(not rule[key] or "\x00" in rule[key] for key in ("tool", "case", "contains")):
            raise AdapterError(f"invalid diagnostic rule value at index {index}")
        severity = rule.get("severity")
        if severity is not None and severity not in {"error", "warning", "fatal", "note", "info"}:
            raise AdapterError(f"invalid diagnostic severity at index {index}")
        result.append(
            DiagnosticFallback(
                tool=rule["tool"],
                case=rule["case"],
                contains=rule["contains"],
                severity=severity,
            )
        )
    return tuple(result)


def adapter_for(
    adapter_id: str,
    *,
    rules_path: Path | None = None,
    fake_scenario: str = "conform",
) -> ToolAdapter:
    fallbacks = load_fallbacks(rules_path)
    adapters: dict[str, ToolAdapter] = {
        "slang": SlangAdapter(fallbacks),
        "icarus": IcarusAdapter(fallbacks),
        "verilator": VerilatorAdapter(fallbacks),
        "vcs": VcsAdapter(fallbacks),
        "fake": FakeAdapter(fake_scenario),
    }
    try:
        return adapters[adapter_id]
    except KeyError as error:
        raise AdapterError(f"unregistered adapter {adapter_id!r}") from error
