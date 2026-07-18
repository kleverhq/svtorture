"""Initial VCS adapter carried by the generic private-wrapper backend."""

from __future__ import annotations

import re

from svtorture.adapters.base import (
    PORTABLE_WORK_ROOT,
    WORK_ROOT,
    DiagnosticPattern,
    ToolAdapter,
    define_argv,
    include_argv,
    source_argv,
)
from svtorture.adapters.open_source import _stage
from svtorture.catalog import LoadedCase
from svtorture.models import (
    ExecutionBackend,
    ExecutionPlan,
    Phase,
    StageKind,
    ToolDefinition,
    ToolProfile,
)


class VcsAdapter(ToolAdapter):
    """VCS S-2021.09-1-compatible argv carried to a user-owned wrapper."""

    id = "vcs"
    diagnostic_patterns = (
        DiagnosticPattern(
            re.compile(
                r"(?ms)^(?P<severity>Error|Warning|Fatal|Info)-"
                r"\[(?P<code>[^\]]+)\]\s*(?P<message>.*?)(?:\n|$).*?"
                r"(?P<source>[^,\n]+),\s*(?P<line>\d+)"
            )
        ),
        DiagnosticPattern(
            re.compile(
                r"(?m)^(?P<source>[^,\n]+),\s*(?P<line>\d+):\s*"
                r"(?P<severity>error|warning|fatal|info):\s*(?P<message>.+)$"
            )
        ),
    )
    internal_error_patterns = (
        *ToolAdapter.internal_error_patterns,
        re.compile(r"Error-\[INTERNAL\]", re.IGNORECASE),
    )

    def version_argv(self) -> tuple[str, ...]:
        return ("vcs", "-ID")

    def build_plan(
        self,
        case: LoadedCase,
        tool: ToolDefinition,
        profile: ToolProfile,
        *,
        image: str | None,
        wrapper: str | None,
    ) -> ExecutionPlan:
        del image
        executable = f"{WORK_ROOT}/simv"
        portable_executable = f"{PORTABLE_WORK_ROOT}/simv"
        compile_argv: tuple[str, ...] = (
            "vcs",
            "-full64",
            "-sverilog",
            "-o",
            executable,
        )
        portable_compile: tuple[str, ...] = (
            "vcs",
            "-full64",
            "-sverilog",
            "-o",
            portable_executable,
        )
        compile_argv += include_argv(case, "plus") + define_argv(case, "plus")
        portable_compile += include_argv(case, "plus", portable=True) + define_argv(case, "plus")
        compile_argv += source_argv(case)
        portable_compile += source_argv(case, portable=True)
        stages = [
            _stage(
                "compile",
                StageKind.COMPILE,
                Phase.ELABORATE,
                compile_argv,
                portable_compile,
                case,
                "simv",
            )
        ]
        if case.definition.target_phase is Phase.SIMULATE:
            stages.append(
                _stage(
                    "run",
                    StageKind.RUN,
                    Phase.SIMULATE,
                    (executable, *case.definition.runtime_args),
                    (portable_executable, *case.definition.runtime_args),
                    case,
                )
            )
        return ExecutionPlan(
            schema_version=1,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            backend=ExecutionBackend.LOCAL_WRAPPER,
            wrapper=wrapper,
            stages=tuple(stages),
        )
