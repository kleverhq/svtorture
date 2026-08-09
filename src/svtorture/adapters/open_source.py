"""Slang, Icarus, and Verilator adapters."""

from __future__ import annotations

import re

from svtorture.adapters.base import (
    PORTABLE_WORK_ROOT,
    WORK_ROOT,
    DiagnosticPattern,
    ToolAdapter,
    UnsupportedCapability,
    define_argv,
    foreign_source_argv,
    include_argv,
    source_argv,
)
from svtorture.catalog import LoadedCase
from svtorture.models import (
    ExecutionBackend,
    ExecutionPlan,
    ExecutionStage,
    ForeignInterface,
    Phase,
    StageKind,
    ToolDefinition,
    ToolProfile,
)


def _stage(
    stage_id: str,
    kind: StageKind,
    attempted_through_phase: Phase,
    argv: tuple[str, ...],
    portable_argv: tuple[str, ...],
    case: LoadedCase,
    expected_artifact: str | None = None,
) -> ExecutionStage:
    return ExecutionStage(
        id=stage_id,
        kind=kind,
        attempted_through_phase=attempted_through_phase,
        argv=argv,
        portable_argv=portable_argv,
        timeout_seconds=case.definition.limits.timeout_seconds,
        output_bytes=case.definition.limits.output_bytes,
        expected_artifact=expected_artifact,
    )


class SlangAdapter(ToolAdapter):
    id = "slang"
    diagnostic_patterns = (
        DiagnosticPattern(
            re.compile(
                r"(?m)^(?P<source>[^:\n]+):(?P<line>\d+):(?P<column>\d+): "
                r"(?P<severity>error|warning|note): (?P<message>.+?)(?: "
                r"\[-W(?P<code>[^\]]+)\])?$"
            )
        ),
    )

    def version_argv(self) -> tuple[str, ...]:
        return ("slang", "--version")

    def check_case(self, case: LoadedCase) -> None:
        if case.definition.foreign is not None:
            raise UnsupportedCapability("Slang has no foreign interface runtime")
        if case.definition.covergroups:
            raise UnsupportedCapability("Slang has no functional coverage runtime")
        if any(resource.casefold().endswith(".sdf") for resource in case.definition.resources):
            raise UnsupportedCapability("Slang has no SDF simulation runtime")

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
        self.check_case(case)
        base: tuple[str, ...] = ("slang", "--std=1800-2023", "--single-unit")
        portable: tuple[str, ...] = base
        if case.definition.target_phase is Phase.PREPROCESS:
            base += ("-E",)
            portable += ("-E",)
        elif case.definition.target_phase is Phase.PARSE:
            base += ("--parse-only",)
            portable += ("--parse-only",)
        elif case.definition.target_phase is Phase.ELABORATE and case.definition.top:
            base += (f"--top={case.definition.top}",)
            portable += (f"--top={case.definition.top}",)
        else:
            if case.definition.target_phase is Phase.SIMULATE:
                raise ValueError("Slang does not implement simulation")
        if case.definition.library_map is not None:
            base += ("--libmap", f"/case/{case.definition.library_map}")
            portable += ("--libmap", f"$CASE/{case.definition.library_map}")
        base += include_argv(case, "split") + define_argv(case, "joined")
        portable += include_argv(case, "split", portable=True) + define_argv(case, "joined")
        base += source_argv(case)
        portable += source_argv(case, portable=True)
        return ExecutionPlan(
            schema_version=3,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            target_phase=case.definition.target_phase,
            backend=ExecutionBackend.DOCKER,
            image=image,
            stages=(
                _stage(
                    case.definition.target_phase.value,
                    StageKind.COMPILE,
                    case.definition.target_phase,
                    base,
                    portable,
                    case,
                ),
            ),
        )


class IcarusAdapter(ToolAdapter):
    id = "icarus"
    diagnostic_patterns = (
        DiagnosticPattern(
            re.compile(
                r"(?m)^(?P<severity>ERROR|WARNING|FATAL|INFO): "
                r"(?P<source>[^:\n]+):(?P<line>\d+)(?::(?P<column>\d+))?: "
                r"(?P<message>.+)$",
                re.IGNORECASE,
            )
        ),
        DiagnosticPattern(
            re.compile(
                r"(?m)^(?P<source>[^:\n]+):(?P<line>\d+)(?::(?P<column>\d+))?: "
                r"(?:(?P<severity>error|warning|fatal|note): )?(?P<message>.+)$"
            )
        ),
    )
    internal_error_patterns = (
        *ToolAdapter.internal_error_patterns,
        re.compile(r"\bivl:.*assert", re.IGNORECASE),
        re.compile(r"\bI give up\.", re.IGNORECASE),
    )

    def version_argv(self) -> tuple[str, ...]:
        return ("iverilog", "-V")

    def check_case(self, case: LoadedCase) -> None:
        if case.definition.foreign is ForeignInterface.DPI:
            raise UnsupportedCapability("Icarus does not support DPI")
        if case.definition.foreign is ForeignInterface.VPI:
            raise UnsupportedCapability("Icarus VPI support is not enabled")
        if case.definition.library_map is not None:
            raise UnsupportedCapability("Icarus does not support configurations")
        if case.definition.covergroups:
            raise UnsupportedCapability("Icarus does not support covergroups")

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
        self.check_case(case)
        output = f"{WORK_ROOT}/sim.vvp"
        portable_output = f"{PORTABLE_WORK_ROOT}/sim.vvp"
        preprocessing = case.definition.target_phase is Phase.PREPROCESS
        if preprocessing:
            compile_argv: tuple[str, ...] = ("iverilog", "-g2012", "-E", "-o", "-")
            portable_compile: tuple[str, ...] = compile_argv
        else:
            compile_argv = ("iverilog", "-g2012", "-o", output)
            portable_compile = (
                "iverilog",
                "-g2012",
                "-o",
                portable_output,
            )
        if case.definition.top and not preprocessing:
            compile_argv += ("-s", case.definition.top)
            portable_compile += ("-s", case.definition.top)
        if any(resource.casefold().endswith(".sdf") for resource in case.definition.resources):
            compile_argv += ("-gspecify",)
            portable_compile += ("-gspecify",)
        compile_argv += include_argv(case, "joined") + define_argv(case, "joined")
        portable_compile += include_argv(case, "joined", portable=True) + define_argv(
            case, "joined"
        )
        compile_argv += source_argv(case)
        portable_compile += source_argv(case, portable=True)
        stages: list[ExecutionStage] = [
            _stage(
                "compile",
                StageKind.COMPILE,
                Phase.PREPROCESS if preprocessing else Phase.ELABORATE,
                compile_argv,
                portable_compile,
                case,
                None if preprocessing else "sim.vvp",
            )
        ]
        if case.definition.target_phase is Phase.SIMULATE:
            run = ("vvp", output, *case.definition.runtime_args)
            portable_run = ("vvp", portable_output, *case.definition.runtime_args)
            stages.append(
                _stage(
                    "run",
                    StageKind.RUN,
                    Phase.SIMULATE,
                    run,
                    portable_run,
                    case,
                )
            )
        return ExecutionPlan(
            schema_version=3,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            target_phase=case.definition.target_phase,
            backend=ExecutionBackend.DOCKER,
            image=image,
            stages=tuple(stages),
        )


class VerilatorAdapter(ToolAdapter):
    id = "verilator"
    diagnostic_patterns = (
        DiagnosticPattern(
            re.compile(
                r"(?m)^%(?P<severity>Error|Warning|Fatal|Info)"
                r"(?:-(?P<code>[A-Z0-9_]+))?: "
                r"(?P<source>[^:\n]+):(?P<line>\d+):(?P<column>\d+): "
                r"(?P<message>.+)$"
            )
        ),
        DiagnosticPattern(
            re.compile(
                r"(?m)^%(?P<severity>Error|Warning|Fatal|Info): "
                r"(?P<source>[^:\n]+):(?P<line>\d+): (?P<message>.+)$"
            )
        ),
    )
    internal_error_patterns = (
        *ToolAdapter.internal_error_patterns,
        re.compile(r"%Error: Internal Error", re.IGNORECASE),
        re.compile(r"Verilator internal fault", re.IGNORECASE),
    )

    def version_argv(self) -> tuple[str, ...]:
        return ("verilator", "--version")

    def check_case(self, case: LoadedCase) -> None:
        if case.definition.foreign is ForeignInterface.VPI:
            raise UnsupportedCapability("Verilator VPI support is not enabled")
        if any(resource.casefold().endswith(".sdf") for resource in case.definition.resources):
            raise UnsupportedCapability("Verilator does not implement SDF annotation")

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
        self.check_case(case)
        base: tuple[str, ...] = (
            "verilator",
            "--language",
            "1800-2023",
        )
        portable: tuple[str, ...] = base
        preprocessing = case.definition.target_phase is Phase.PREPROCESS
        if preprocessing:
            base += ("-E",)
            portable += ("-E",)
        else:
            base += ("--timing", "-Wno-fatal", "-Wpedantic")
            portable += ("--timing", "-Wno-fatal", "-Wpedantic")
            if case.definition.target_phase is Phase.SIMULATE:
                mode = ("--cc", "--main") if case.definition.foreign is not None else ("--binary",)
                base += (*mode, "--Mdir", f"{WORK_ROOT}/obj", "-o", "sim")
                portable += (
                    *mode,
                    "--Mdir",
                    f"{PORTABLE_WORK_ROOT}/obj",
                    "-o",
                    "sim",
                )
            else:
                base += ("--lint-only",)
                portable += ("--lint-only",)
        if case.definition.top and not preprocessing:
            base += ("--top-module", case.definition.top)
            portable += ("--top-module", case.definition.top)
        if case.definition.library_map is not None:
            base += ("--libmap", f"/case/{case.definition.library_map}")
            portable += ("--libmap", f"$CASE/{case.definition.library_map}")
        if case.definition.covergroups:
            base += ("--coverage-user",)
            portable += ("--coverage-user",)
        base += include_argv(case, "joined") + define_argv(case, "joined")
        portable += include_argv(case, "joined", portable=True) + define_argv(case, "joined")
        base += source_argv(case)
        portable += source_argv(case, portable=True)
        if case.definition.foreign is not None:
            base += ("--exe", *foreign_source_argv(case))
            portable += ("--exe", *foreign_source_argv(case, portable=True))
        artifact = None
        if case.definition.target_phase is Phase.SIMULATE:
            artifact = (
                f"obj/V{case.definition.top}.mk"
                if case.definition.foreign is not None
                else "obj/sim"
            )
        stages: list[ExecutionStage] = [
            _stage(
                "compile",
                StageKind.COMPILE,
                Phase.PREPROCESS if preprocessing else Phase.ELABORATE,
                base,
                portable,
                case,
                artifact,
            )
        ]
        if case.definition.foreign is not None:
            assert case.definition.top is not None
            stages.append(
                _stage(
                    "foreign-build",
                    StageKind.FOREIGN_BUILD,
                    Phase.ELABORATE,
                    (
                        "make",
                        "-C",
                        f"{WORK_ROOT}/obj",
                        "-f",
                        f"V{case.definition.top}.mk",
                        "sim",
                    ),
                    (
                        "make",
                        "-C",
                        f"{PORTABLE_WORK_ROOT}/obj",
                        "-f",
                        f"V{case.definition.top}.mk",
                        "sim",
                    ),
                    case,
                    "obj/sim",
                )
            )
        if case.definition.target_phase is Phase.SIMULATE:
            stages.append(
                _stage(
                    "run",
                    StageKind.RUN,
                    Phase.SIMULATE,
                    (f"{WORK_ROOT}/obj/sim", *case.definition.runtime_args),
                    (f"{PORTABLE_WORK_ROOT}/obj/sim", *case.definition.runtime_args),
                    case,
                )
            )
        return ExecutionPlan(
            schema_version=3,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            target_phase=case.definition.target_phase,
            backend=ExecutionBackend.DOCKER,
            image=image,
            stages=tuple(stages),
        )
