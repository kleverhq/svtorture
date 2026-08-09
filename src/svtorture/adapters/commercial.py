"""Initial VCS adapter carried by the generic local-wrapper backend."""

from __future__ import annotations

import re

from svtorture.adapters.base import (
    PORTABLE_WORK_ROOT,
    WORK_ROOT,
    DiagnosticPattern,
    ToolAdapter,
    UnsupportedCapability,
    define_argv,
    include_argv,
    source_argv,
)
from svtorture.adapters.open_source import _stage
from svtorture.catalog import LoadedCase
from svtorture.models import (
    ExecutionBackend,
    ExecutionPlan,
    ForeignInterface,
    Phase,
    StageKind,
    ToolDefinition,
    ToolProfile,
    WorkFile,
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

    def check_case(self, case: LoadedCase) -> None:
        if case.definition.foreign is ForeignInterface.VPI:
            raise UnsupportedCapability("VCS VPI support is not enabled")
        if case.definition.foreign is not None and case.definition.library_map is not None:
            raise UnsupportedCapability("combined foreign and library modes are unsupported")

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
        self.check_case(case)
        executable = f"{WORK_ROOT}/simv"
        portable_executable = f"{PORTABLE_WORK_ROOT}/simv"
        stages = []
        work_files: tuple[WorkFile, ...] = ()
        if case.definition.library_map is not None:
            setup = ["WORK > work"]
            generated: list[WorkFile] = []
            for library in case.logical_libraries:
                setup.append(f"{library.name} : ./libraries/{library.name}")
                generated.append(
                    WorkFile(path=f"libraries/{library.name}/.keep", content="generated\n")
                )
                library_argv = (
                    "vlogan",
                    "-full64",
                    "-sverilog",
                    "-work",
                    library.name,
                    *include_argv(case, "plus"),
                    *define_argv(case, "plus"),
                    *(f"/case/{source}" for source in library.sources),
                )
                portable_library_argv = (
                    "vlogan",
                    "-full64",
                    "-sverilog",
                    "-work",
                    library.name,
                    *include_argv(case, "plus", portable=True),
                    *define_argv(case, "plus"),
                    *(f"$CASE/{source}" for source in library.sources),
                )
                stages.append(
                    _stage(
                        f"compile-{library.name}",
                        StageKind.COMPILE,
                        Phase.PARSE,
                        library_argv,
                        portable_library_argv,
                        case,
                    )
                )
            generated.append(WorkFile(path="synopsys_sim.setup", content="\n".join(setup) + "\n"))
            work_files = tuple(generated)
            assert case.definition.top is not None
            stages.append(
                _stage(
                    "elaborate",
                    StageKind.COMPILE,
                    Phase.ELABORATE,
                    (
                        "vcs",
                        "-full64",
                        "-sverilog",
                        "-top",
                        case.definition.top,
                        "-o",
                        executable,
                        case.definition.top,
                    ),
                    (
                        "vcs",
                        "-full64",
                        "-sverilog",
                        "-top",
                        case.definition.top,
                        "-o",
                        portable_executable,
                        case.definition.top,
                    ),
                    case,
                    "simv",
                )
            )
        elif case.definition.foreign is not None:
            assert case.definition.top is not None
            analysis_argv = (
                "vlogan",
                "-full64",
                "-sverilog",
                *include_argv(case, "plus"),
                *define_argv(case, "plus"),
                *source_argv(case),
            )
            portable_analysis = (
                "vlogan",
                "-full64",
                "-sverilog",
                *include_argv(case, "plus", portable=True),
                *define_argv(case, "plus"),
                *source_argv(case, portable=True),
            )
            stages.append(
                _stage(
                    "compile",
                    StageKind.COMPILE,
                    Phase.PARSE,
                    analysis_argv,
                    portable_analysis,
                    case,
                )
            )
            foreign_sources = case.definition.foreign_sources
            compiler = (
                "$(CC)" if all(source.endswith(".c") for source in foreign_sources) else "$(CXX)"
            )
            compiler_inputs = " ".join(
                f"-x {'c' if source.endswith('.c') else 'c++'} {source}"
                for source in foreign_sources
            )
            work_files = (
                WorkFile(
                    path="svtorture-foreign.mk",
                    content=(
                        ".PHONY: simv\n"
                        "simv:\n"
                        f"\t{compiler} -shared -fPIC -I$(VCS_HOME)/include "
                        f"{compiler_inputs} -o foreign.so\n"
                        f"\tvcs -full64 -sverilog -top {case.definition.top} "
                        f"-o simv {case.definition.top} foreign.so\n"
                    ),
                ),
            )
            stages.append(
                _stage(
                    "foreign-build",
                    StageKind.FOREIGN_BUILD,
                    Phase.ELABORATE,
                    (
                        "make",
                        "-f",
                        f"{WORK_ROOT}/svtorture-foreign.mk",
                        "simv",
                    ),
                    (
                        "make",
                        "-f",
                        f"{PORTABLE_WORK_ROOT}/svtorture-foreign.mk",
                        "simv",
                    ),
                    case,
                    "simv",
                )
            )
        else:
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
            portable_compile += include_argv(case, "plus", portable=True) + define_argv(
                case, "plus"
            )
            compile_argv += source_argv(case)
            portable_compile += source_argv(case, portable=True)
            stages.append(
                _stage(
                    "compile",
                    StageKind.COMPILE,
                    Phase.ELABORATE,
                    compile_argv,
                    portable_compile,
                    case,
                    "simv",
                )
            )
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
            schema_version=3,
            case_id=case.definition.id,
            tool_id=tool.id,
            profile_id=profile.id,
            target_phase=case.definition.target_phase,
            backend=ExecutionBackend.LOCAL_WRAPPER,
            wrapper=wrapper,
            work_files=work_files,
            stages=tuple(stages),
        )
