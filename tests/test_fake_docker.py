from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from svtorture.adapters.fake import FakeAdapter
from svtorture.campaign import PreparedTool, run_campaign
from svtorture.catalog import Catalog, LoadedCase
from svtorture.evaluator import evaluate
from svtorture.executor import execute_plan
from svtorture.images import build_image
from svtorture.models import (
    ImageIdentity,
    ReasonCode,
    ResourceLimits,
    ResultStatus,
)
from svtorture.reproduce import reproduce_case

pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def docker_daemon() -> None:
    result = subprocess.run(
        ["docker", "info"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        if os.environ.get("SVTORTURE_REQUIRE_DOCKER") == "1":
            pytest.fail("a working Docker daemon is required")
        pytest.skip("Docker daemon unavailable")


@pytest.fixture(scope="module")
def fake_image(root: Path, catalog: Catalog, docker_daemon: None) -> ImageIdentity:
    del docker_daemon
    return build_image(root, catalog.tools.tool("fake"), None)


def _scenario(
    catalog: Catalog,
    fake_image: ImageIdentity,
    tmp_path: Path,
    *,
    case_id: str,
    scenario: str,
) -> tuple[ResultStatus, ReasonCode]:
    case = catalog.cases[case_id]
    adapter = FakeAdapter(scenario)
    tool = catalog.tools.tool("fake")
    profile = tool.profile("simulator")
    plan = adapter.build_plan(
        case,
        tool,
        profile,
        image=fake_image.reference,
        wrapper=None,
    )
    observations = execute_plan(
        plan,
        case,
        adapter,
        tmp_path / f"{case_id}-{scenario}",
    )
    result = evaluate(case, tool.id, profile.id, observations)
    return result.status, result.reason


def test_fake_container_exercises_executor_campaign_and_reproduction(
    root: Path,
    catalog: Catalog,
    fake_image: ImageIdentity,
) -> None:
    tool = catalog.tools.tool("fake")
    profile = tool.profile("simulator")
    campaign = run_campaign(
        catalog,
        (
            PreparedTool(
                definition=tool,
                profile=profile,
                selection=None,
                image=fake_image,
                reported_version="svtorture-fake-tool 1.0",
            ),
        ),
        suite_id="smoke",
    )
    assert campaign.results
    assert {result.status for result in campaign.results} == {ResultStatus.CONFORMING}
    report = reproduce_case(
        root,
        campaign,
        tool_id="fake",
        profile_id="simulator",
        case_id="ch04-nba-rhs-captured",
    )
    assert not report.differences


@pytest.mark.parametrize(
    ("case_id", "scenario", "expected"),
    (
        (
            "ch05-base-format-whitespace-rejected",
            "crash",
            (ResultStatus.INCONCLUSIVE, ReasonCode.CRASH),
        ),
        (
            "ch05-base-format-whitespace-rejected",
            "unrelated",
            (ResultStatus.INCONCLUSIVE, ReasonCode.OFF_TARGET_DIAGNOSTIC),
        ),
        (
            "ch05-base-format-whitespace-rejected",
            "wrong-location",
            (ResultStatus.INCONCLUSIVE, ReasonCode.OFF_TARGET_DIAGNOSTIC),
        ),
        (
            "ch05-base-format-whitespace-rejected",
            "internal-error",
            (ResultStatus.INCONCLUSIVE, ReasonCode.INTERNAL_ERROR),
        ),
        (
            "ch04-nba-rhs-captured",
            "missing-marker",
            (ResultStatus.NONCONFORMING, ReasonCode.MISSING_PASS_MARKER),
        ),
        (
            "ch04-nba-rhs-captured",
            "marker-nonzero",
            (ResultStatus.NONCONFORMING, ReasonCode.PASS_MARKER_NONZERO),
        ),
        (
            "ch04-nba-rhs-captured",
            "wrong-runtime",
            (ResultStatus.NONCONFORMING, ReasonCode.WRONG_RUNTIME_RESULT),
        ),
        (
            "ch04-nba-rhs-captured",
            "missing-artifact",
            (ResultStatus.NONCONFORMING, ReasonCode.MISSING_ARTIFACT),
        ),
    ),
)
def test_fake_container_false_pass_scenarios(
    catalog: Catalog,
    fake_image: ImageIdentity,
    tmp_path: Path,
    case_id: str,
    scenario: str,
    expected: tuple[ResultStatus, ReasonCode],
) -> None:
    assert (
        _scenario(
            catalog,
            fake_image,
            tmp_path,
            case_id=case_id,
            scenario=scenario,
        )
        == expected
    )


def test_fake_container_timeout_is_inconclusive(
    catalog: Catalog,
    fake_image: ImageIdentity,
    tmp_path: Path,
) -> None:
    original = catalog.cases["ch05-base-format-whitespace-rejected"]
    definition = original.definition.model_copy(
        update={
            "limits": ResourceLimits(
                timeout_seconds=1,
                output_bytes=4096,
                memory_mb=256,
                pids=32,
            )
        }
    )
    case = LoadedCase(
        definition=definition,
        directory=original.directory,
        metadata_path=original.metadata_path,
        anchor_source=original.anchor_source,
        anchor_line=original.anchor_line,
        content_sha256=original.content_sha256,
    )
    adapter = FakeAdapter("timeout")
    tool = catalog.tools.tool("fake")
    profile = tool.profile("simulator")
    plan = adapter.build_plan(
        case,
        tool,
        profile,
        image=fake_image.reference,
        wrapper=None,
    )
    result = evaluate(
        case,
        tool.id,
        profile.id,
        execute_plan(plan, case, adapter, tmp_path / "timeout"),
    )
    assert (result.status, result.reason) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.TIMEOUT,
    )


def test_missing_container_image_is_harness_error(catalog: Catalog, tmp_path: Path) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    adapter = FakeAdapter()
    tool = catalog.tools.tool("fake")
    profile = tool.profile("simulator")
    plan = adapter.build_plan(
        case,
        tool,
        profile,
        image="svtorture/definitely-missing-image:never",
        wrapper=None,
    )
    result = evaluate(
        case,
        tool.id,
        profile.id,
        execute_plan(plan, case, adapter, tmp_path / "missing-image"),
    )
    assert (result.status, result.reason) == (
        ResultStatus.HARNESS_ERROR,
        ReasonCode.CONTAINER_FAILURE,
    )
