"""Adapter factory driven by validated tool metadata."""

from __future__ import annotations

from collections.abc import Iterable

from svtorture.adapters.base import DiagnosticFallback, ToolAdapter
from svtorture.adapters.commercial import VcsAdapter
from svtorture.adapters.fake import FakeAdapter
from svtorture.adapters.open_source import IcarusAdapter, SlangAdapter, VerilatorAdapter
from svtorture.models import DiagnosticRule


class AdapterError(ValueError):
    pass


def adapter_for(
    adapter_id: str,
    *,
    diagnostic_rules: Iterable[DiagnosticRule] = (),
    fake_scenario: str = "conform",
) -> ToolAdapter:
    fallbacks = tuple(
        DiagnosticFallback(
            case=rule.case,
            contains=rule.contains,
            severity=rule.severity,
        )
        for rule in diagnostic_rules
    )
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
