"""Execute typed plans in isolated Docker containers or private wrappers."""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Mapping
from pathlib import Path

from svtorture.adapters.base import ToolAdapter
from svtorture.catalog import LoadedCase
from svtorture.models import (
    CapturedStream,
    ExecutionBackend,
    ExecutionPlan,
    ExecutionStage,
    RawOutcome,
    StageObservation,
    WrapperDefinition,
)
from svtorture.process import ProcessResult, StreamCapture, run_process

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
HOST_PATH_RE = re.compile(r"(?<![A-Za-z0-9_$])/(?:home|Users|private|tmp|root)/[^\s:]+")


class ExecutionError(RuntimeError):
    pass


def _sanitize(text: str, replacements: Mapping[str, str]) -> str:
    text = ANSI_RE.sub("", text)
    for source, target in sorted(replacements.items(), key=lambda item: -len(item[0])):
        text = text.replace(source, target)
    return HOST_PATH_RE.sub("$HOST_PATH", text)


def _captured(stream: StreamCapture, replacements: Mapping[str, str]) -> CapturedStream:
    decoded = stream.data.decode("utf-8", errors="replace")
    return CapturedStream(
        excerpt=_sanitize(decoded, replacements),
        size_bytes=stream.size_bytes,
        sha256=stream.sha256,
        truncated=stream.truncated,
    )


def _docker_argv(
    plan: ExecutionPlan,
    stage: ExecutionStage,
    case: LoadedCase,
    work_dir: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    assert plan.image is not None
    uid = os.getuid()
    gid = os.getgid()
    limits = case.definition.limits
    actual = (
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--init",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--pids-limit={limits.pids}",
        f"--memory={limits.memory_mb}m",
        "--platform=linux/amd64",
        "--user",
        f"{uid}:{gid}",
        "--workdir",
        "/work",
        "--env",
        "HOME=/tmp",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--mount",
        f"type=bind,src={case.directory},dst=/case,readonly",
        "--mount",
        f"type=bind,src={work_dir},dst=/work",
        plan.image,
        *stage.argv,
    )
    portable = (
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--init",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--pids-limit={limits.pids}",
        f"--memory={limits.memory_mb}m",
        "--platform=linux/amd64",
        "--user",
        "$UID:$GID",
        "--workdir",
        "$WORK",
        "--env",
        "HOME=/tmp",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--mount",
        "type=bind,src=$CASE,dst=/case,readonly",
        "--mount",
        "type=bind,src=$WORK,dst=/work",
        plan.image,
        *stage.portable_argv,
    )
    return actual, portable


def _wrapper_argv(
    wrapper: WrapperDefinition,
    plan: ExecutionPlan,
    stage: ExecutionStage,
    case: LoadedCase,
    work_dir: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, str]]:
    request_path = work_dir / f"wrapper-request-{stage.id}.json"
    request = {
        "schema_version": 2,
        "tool": plan.tool_id,
        "case": plan.case_id,
        "profile": plan.profile_id,
        "stage": {
            "id": stage.id,
            "target_phase": plan.target_phase.value,
            "attempted_through_phase": stage.attempted_through_phase.value,
            "argv": list(stage.argv),
            "portable_argv": list(stage.portable_argv),
            "timeout_seconds": stage.timeout_seconds,
        },
        "mounts": {
            "case": str(case.directory),
            "work": str(work_dir),
            "case_container": "/case",
            "work_container": "/work",
        },
        "execution_policy": {"network": "none", "isolation": "wrapper-required"},
    }
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    actual = (*wrapper.command, "--request", str(request_path))
    portable = (
        "$SVTORTURE_PRIVATE_WRAPPER",
        "--request",
        f"$WORK/{request_path.name}",
    )
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    for name in wrapper.environment_allowlist:
        if name in os.environ:
            environment[name] = os.environ[name]
    return actual, portable, environment


def _classify_container(result: ProcessResult) -> ProcessResult:
    if result.outcome is not RawOutcome.NORMAL_EXIT:
        return result
    assert result.exit_code is not None
    if result.exit_code in {125, 126, 127}:
        return ProcessResult(
            outcome=RawOutcome.CONTAINER_FAILURE,
            exit_code=None,
            signal=None,
            duration_seconds=result.duration_seconds,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    if 128 < result.exit_code <= 192:
        return ProcessResult(
            outcome=RawOutcome.SIGNAL,
            exit_code=None,
            signal=result.exit_code - 128,
            duration_seconds=result.duration_seconds,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    return result


def _classify_wrapper(result: ProcessResult) -> ProcessResult:
    """Map the wrapper protocol's EX_UNAVAILABLE status into a typed outcome."""

    if result.outcome is RawOutcome.NORMAL_EXIT and result.exit_code == 69:
        return ProcessResult(
            outcome=RawOutcome.BACKEND_UNAVAILABLE,
            exit_code=None,
            signal=None,
            duration_seconds=result.duration_seconds,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    # Licensed wrappers normally front a private Docker runtime; preserve the
    # same reserved launch and signal ownership rules when they propagate it.
    return _classify_container(result)


def _observation(
    result: ProcessResult,
    stage: ExecutionStage,
    portable_argv: tuple[str, ...],
    case: LoadedCase,
    adapter: ToolAdapter,
    work_dir: Path,
) -> StageObservation:
    replacements = {
        str(case.directory): "$CASE",
        str(work_dir): "$WORK",
    }
    stdout = _captured(result.stdout, replacements)
    stderr = _captured(result.stderr, replacements)
    diagnostic_stdout = stdout.excerpt
    diagnostic_stderr = stderr.excerpt
    if result.launch_error:
        diagnostic_stderr += "\n" + _sanitize(result.launch_error, replacements)
    diagnostics, internal_error = adapter.normalize_diagnostics(
        diagnostic_stdout, diagnostic_stderr, case
    )
    artifact_present: bool | None = None
    if stage.expected_artifact is not None:
        artifact = work_dir / stage.expected_artifact
        artifact_present = artifact.is_file() and not artifact.is_symlink()
    return StageObservation(
        stage_id=stage.id,
        kind=stage.kind,
        attempted_through_phase=stage.attempted_through_phase,
        outcome=result.outcome,
        exit_code=result.exit_code,
        signal=result.signal,
        duration_seconds=result.duration_seconds,
        stdout=stdout,
        stderr=stderr,
        diagnostics=diagnostics,
        internal_error=internal_error,
        artifact_present=artifact_present,
        portable_argv=portable_argv,
    )


def execute_plan(
    plan: ExecutionPlan,
    case: LoadedCase,
    adapter: ToolAdapter,
    work_dir: Path,
    *,
    wrapper: WrapperDefinition | None = None,
) -> tuple[StageObservation, ...]:
    """Execute stages in order, stopping whenever a prerequisite did not complete."""

    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, mode=0o700)
    observations: list[StageObservation] = []
    for stage in plan.stages:
        environment: dict[str, str] | None = None
        if plan.backend is ExecutionBackend.DOCKER:
            argv, portable = _docker_argv(plan, stage, case, work_dir)
        else:
            if wrapper is None:
                raise ExecutionError("private wrapper is unavailable")
            argv, portable, environment = _wrapper_argv(wrapper, plan, stage, case, work_dir)
        process_result = run_process(
            argv,
            cwd=work_dir,
            timeout_seconds=stage.timeout_seconds,
            output_bytes=stage.output_bytes,
            environment=environment,
            stdout_path=work_dir / f"{stage.id}.stdout.log",
            stderr_path=work_dir / f"{stage.id}.stderr.log",
        )
        if plan.backend is ExecutionBackend.DOCKER:
            process_result = _classify_container(process_result)
        else:
            process_result = _classify_wrapper(process_result)
        observation = _observation(process_result, stage, portable, case, adapter, work_dir)
        observations.append(observation)
        if (
            observation.outcome is not RawOutcome.NORMAL_EXIT
            or observation.exit_code != 0
            or observation.artifact_present is False
        ):
            break
    return tuple(observations)
