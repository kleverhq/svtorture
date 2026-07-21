"""Deterministic fake adapter used to test the real executor and evaluator."""

from __future__ import annotations

import re

from svtorture.adapters.base import (
    PORTABLE_WORK_ROOT,
    WORK_ROOT,
    DiagnosticPattern,
    ToolAdapter,
)
from svtorture.adapters.open_source import _stage
from svtorture.catalog import LoadedCase
from svtorture.models import (
    ExecutionBackend,
    ExecutionPlan,
    Expectation,
    Phase,
    StageKind,
    ToolDefinition,
    ToolProfile,
)


class FakeAdapter(ToolAdapter):
    id = "fake"
    diagnostic_patterns = (
        DiagnosticPattern(
            re.compile(
                r"(?m)^(?P<source>[^:\n]+):(?P<line>\d+): "
                r"(?P<severity>error|warning|fatal|note|info): (?P<message>.+)$"
            )
        ),
    )

    def __init__(self, scenario: str = "conform") -> None:
        super().__init__()
        self.scenario = scenario

    def version_argv(self) -> tuple[str, ...]:
        return ("fake-tool", "--version")

    def _args(self, case: LoadedCase, action: str, portable: bool) -> tuple[str, ...]:
        work = PORTABLE_WORK_ROOT if portable else WORK_ROOT
        marker = case.definition.oracle.marker or "-"
        anchor_line = str(case.anchor_line or 1)
        return (
            "fake-tool",
            "--action",
            action,
            "--case",
            case.definition.id,
            "--phase",
            case.definition.target_phase.value,
            "--expectation",
            case.definition.expectation.value,
            "--anchor-line",
            anchor_line,
            "--marker",
            marker,
            "--scenario",
            self.scenario,
            "--artifact",
            f"{work}/fake.artifact",
        )

    def build_plan(
        self,
        case: LoadedCase,
        tool: ToolDefinition,
        profile: ToolProfile,
        *,
        image: str | None,
        wrapper: str | None,
    ) -> ExecutionPlan:
        del wrapper
        stages = [
            _stage(
                "compile",
                StageKind.COMPILE,
                (
                    Phase.ELABORATE
                    if case.definition.target_phase is Phase.SIMULATE
                    else case.definition.target_phase
                ),
                self._args(case, "compile", False),
                self._args(case, "compile", True),
                case,
                "fake.artifact" if case.definition.target_phase is Phase.SIMULATE else None,
            )
        ]
        if case.definition.target_phase is Phase.SIMULATE:
            stages.append(
                _stage(
                    "run",
                    StageKind.RUN,
                    Phase.SIMULATE,
                    self._args(case, "run", False),
                    self._args(case, "run", True),
                    case,
                )
            )
        elif case.definition.expectation is Expectation.DIAGNOSTIC:
            raise ValueError("fake non-runtime diagnostics are represented in compile action")
        return ExecutionPlan(
            schema_version=2,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            target_phase=case.definition.target_phase,
            backend=ExecutionBackend.DOCKER,
            image=image,
            stages=tuple(stages),
        )
