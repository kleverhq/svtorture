"""Common adapter contract and diagnostic normalization."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from re import Pattern

from svtorture.catalog import LoadedCase
from svtorture.models import (
    Diagnostic,
    ExecutionPlan,
    ToolDefinition,
    ToolProfile,
)

CASE_ROOT = "/case"
WORK_ROOT = "/work"
PORTABLE_CASE_ROOT = "$CASE"
PORTABLE_WORK_ROOT = "$WORK"


@dataclass(frozen=True)
class DiagnosticPattern:
    regex: Pattern[str]
    default_severity: str = "error"


@dataclass(frozen=True)
class DiagnosticFallback:
    case: str
    contains: str
    severity: str | None = None


class ToolAdapter(ABC):
    """Adapters expose capabilities, build typed plans, and normalize diagnostics."""

    id: str
    internal_error_patterns: tuple[Pattern[str], ...] = (
        re.compile(r"\binternal (?:compiler )?(?:error|fault)\b", re.IGNORECASE),
        re.compile(r"\bsegmentation fault\b", re.IGNORECASE),
    )
    diagnostic_patterns: tuple[DiagnosticPattern, ...] = ()

    def __init__(self, fallbacks: Iterable[DiagnosticFallback] = ()) -> None:
        self.fallbacks = tuple(fallbacks)

    @abstractmethod
    def build_plan(
        self,
        case: LoadedCase,
        tool: ToolDefinition,
        profile: ToolProfile,
        *,
        image: str | None,
        wrapper: str | None,
    ) -> ExecutionPlan:
        """Construct an execution plan without executing it."""

    @abstractmethod
    def version_argv(self) -> tuple[str, ...]:
        """Return argv used inside the tool environment to report its version."""

    def normalize_diagnostics(
        self, stdout: str, stderr: str, case: LoadedCase
    ) -> tuple[tuple[Diagnostic, ...], bool]:
        combined = "\n".join((stdout, stderr))
        diagnostics: list[Diagnostic] = []
        occupied: set[tuple[int, int]] = set()
        for pattern in self.diagnostic_patterns:
            for match in pattern.regex.finditer(combined):
                span = match.span()
                if span in occupied:
                    continue
                occupied.add(span)
                values = match.groupdict()
                severity = (values.get("severity") or pattern.default_severity).lower()
                if severity not in {"error", "warning", "fatal", "note", "info"}:
                    severity = pattern.default_severity
                line = _optional_int(values.get("line"))
                column = _optional_int(values.get("column"))
                source = values.get("source")
                source = _portable_source(source) if source else None
                target_case_id: str | None = None
                if (
                    source is not None
                    and line is not None
                    and case.anchor_source is not None
                    and case.anchor_line is not None
                    and Path(source).name == Path(case.anchor_source).name
                    and line == case.anchor_line
                ):
                    target_case_id = case.definition.id
                diagnostics.append(
                    Diagnostic(
                        severity=severity,
                        message=(values.get("message") or match.group(0)).strip()[:4096],
                        source=source,
                        line=line,
                        column=column,
                        code=values.get("code"),
                        target_case_id=target_case_id,
                    )
                )

        for diagnostic_index, diagnostic in enumerate(diagnostics):
            if diagnostic.target_case_id is not None or diagnostic.source is not None:
                continue
            for fallback in self.fallbacks:
                if (
                    fallback.case == case.definition.id
                    and fallback.contains.casefold() in diagnostic.message.casefold()
                    and (fallback.severity is None or fallback.severity == diagnostic.severity)
                ):
                    diagnostics[diagnostic_index] = diagnostic.model_copy(
                        update={"target_case_id": case.definition.id}
                    )
                    break

        # Some tools emit terse diagnostics that do not match their normal
        # location-bearing format at all. Keep these narrowly scoped rules in
        # adapter metadata and synthesize a diagnostic only for the named case.
        for fallback in self.fallbacks:
            if (
                fallback.case != case.definition.id
                or fallback.contains.casefold() not in combined.casefold()
                or any(
                    diagnostic.target_case_id == case.definition.id for diagnostic in diagnostics
                )
            ):
                continue
            matching_line = next(
                (
                    line.strip()
                    for line in combined.splitlines()
                    if fallback.contains.casefold() in line.casefold()
                ),
                fallback.contains,
            )
            diagnostics.append(
                Diagnostic(
                    severity=fallback.severity or "error",
                    message=matching_line[:4096],
                    target_case_id=case.definition.id,
                )
            )
        internal_error = any(pattern.search(combined) for pattern in self.internal_error_patterns)
        return tuple(diagnostics), internal_error


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _portable_source(source: str) -> str:
    source = source.strip()
    if source.startswith(CASE_ROOT + "/"):
        return PORTABLE_CASE_ROOT + source[len(CASE_ROOT) :]
    if source.startswith(WORK_ROOT + "/"):
        return PORTABLE_WORK_ROOT + source[len(WORK_ROOT) :]
    return source


def source_argv(case: LoadedCase, portable: bool = False) -> tuple[str, ...]:
    root = PORTABLE_CASE_ROOT if portable else CASE_ROOT
    return tuple(f"{root}/{source}" for source in case.definition.sources)


def include_argv(case: LoadedCase, style: str, *, portable: bool = False) -> tuple[str, ...]:
    root = PORTABLE_CASE_ROOT if portable else CASE_ROOT
    result: list[str] = []
    for include_dir in case.definition.include_dirs:
        path = f"{root}/{include_dir}"
        if style == "split":
            result.extend(("-I", path))
        elif style == "joined":
            result.append(f"-I{path}")
        elif style == "plus":
            result.append(f"+incdir+{path}")
        else:
            raise ValueError(f"unknown include option style {style}")
    return tuple(result)


def define_argv(case: LoadedCase, style: str) -> tuple[str, ...]:
    if style == "split":
        result: list[str] = []
        for define in case.definition.defines:
            result.extend(("-D", define))
        return tuple(result)
    if style == "joined":
        return tuple(f"-D{define}" for define in case.definition.defines)
    if style == "plus":
        return tuple(f"+define+{define}" for define in case.definition.defines)
    raise ValueError(f"unknown define option style {style}")
