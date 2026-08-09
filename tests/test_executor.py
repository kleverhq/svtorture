from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import svtorture.executor as executor_module
from svtorture.adapters.open_source import IcarusAdapter, VerilatorAdapter
from svtorture.catalog import Catalog
from svtorture.executor import ExecutionError, execute_plan
from svtorture.models import RawOutcome, WorkFile
from svtorture.process import ProcessResult, StreamCapture


def test_executor_materializes_declared_and_generated_inputs(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = catalog.cases["ch32-iopath-rise-annotates-path"]
    tool = catalog.tools.tool("icarus")
    profile = tool.profile("simulator")
    adapter = IcarusAdapter()
    plan = adapter.build_plan(case, tool, profile, image="image", wrapper=None).model_copy(
        update={"work_files": (WorkFile(path="generated/setup.txt", content="setup\n"),)}
    )
    empty = StreamCapture(
        data=b"",
        size_bytes=0,
        sha256=hashlib.sha256(b"").hexdigest(),
        truncated=False,
    )

    def run_process(argv: tuple[str, ...], *, cwd: Path, **kwargs: object) -> ProcessResult:
        del argv, kwargs
        assert (cwd / "test.sdf").read_bytes() == (case.directory / "test.sdf").read_bytes()
        assert (cwd / "test.sdf").stat().st_mode & 0o222 == 0
        assert (cwd / "generated" / "setup.txt").read_text() == "setup\n"
        return ProcessResult(
            outcome=RawOutcome.NORMAL_EXIT,
            exit_code=0,
            signal=None,
            duration_seconds=0.0,
            stdout=empty,
            stderr=empty,
        )

    monkeypatch.setattr(executor_module, "run_process", run_process)
    execute_plan(plan, case, adapter, tmp_path / "work")

    def mutate_resource(argv: tuple[str, ...], *, cwd: Path, **kwargs: object) -> ProcessResult:
        del argv, kwargs
        resource = cwd / "test.sdf"
        resource.chmod(0o644)
        resource.write_text("modified", encoding="utf-8")
        return ProcessResult(
            outcome=RawOutcome.NORMAL_EXIT,
            exit_code=0,
            signal=None,
            duration_seconds=0.0,
            stdout=empty,
            stderr=empty,
        )

    monkeypatch.setattr(executor_module, "run_process", mutate_resource)
    with pytest.raises(ExecutionError, match="resource was modified"):
        execute_plan(plan, case, adapter, tmp_path / "mutated")


def test_missing_foreign_toolchain_has_stage_specific_ownership(catalog: Catalog) -> None:
    case = catalog.cases["ch35-c-source-import"]
    tool = catalog.tools.tool("verilator")
    plan = VerilatorAdapter().build_plan(
        case,
        tool,
        tool.profile("simulator"),
        image="image",
        wrapper=None,
    )
    empty = StreamCapture(
        data=b"",
        size_bytes=0,
        sha256=hashlib.sha256(b"").hexdigest(),
        truncated=False,
    )
    missing = ProcessResult(
        outcome=RawOutcome.NORMAL_EXIT,
        exit_code=127,
        signal=None,
        duration_seconds=0.0,
        stdout=empty,
        stderr=empty,
    )

    foreign = executor_module._classify_container(missing, plan.stages[1])
    compile_stage = executor_module._classify_container(missing, plan.stages[0])

    assert foreign.outcome is RawOutcome.LAUNCH_FAILURE
    assert compile_stage.outcome is RawOutcome.CONTAINER_FAILURE
