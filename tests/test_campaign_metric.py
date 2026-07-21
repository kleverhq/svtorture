from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from svtorture.campaign import (
    PreparedTool,
    aggregate_campaigns,
    create_missing_campaign,
    create_preparation_failure_campaign,
    run_campaign,
    verify_campaign_against_catalog,
    wrapper_available,
)
from svtorture.catalog import Catalog, LoadedCase
from svtorture.metric import compute_metric
from svtorture.models import (
    Applicability,
    OracleKind,
    Phase,
    ReasonCode,
    ResultStatus,
    StandardRevision,
    SuiteDefinition,
    WrapperDefinition,
)
from tests.helpers import (
    campaign_tool,
    copy_catalog,
    image_identity,
    make_campaign,
    normalized,
    observation,
)


def test_unsupported_phase_is_recorded_without_execution(catalog: Catalog) -> None:
    tool = catalog.tools.tool("slang")
    profile = tool.profile("parser")
    recorded_tool = campaign_tool(tool, (profile.id,))
    progress: list[tuple[int, int, str, str, str]] = []
    campaign = run_campaign(
        catalog,
        (
            PreparedTool(
                definition=tool,
                profile=profile,
                selection=recorded_tool.selection,
                image=recorded_tool.image,
                reported_version=None,
            ),
        ),
        suite_id="smoke",
        progress=lambda current, total, tool_id, profile_id, case_id: progress.append(
            (current, total, tool_id, profile_id, case_id)
        ),
    )
    assert progress == [
        (number, len(campaign.case_ids), tool.id, profile.id, case_id)
        for number, case_id in enumerate(campaign.case_ids, start=1)
    ]
    by_case = {result.case_id: result for result in campaign.results}
    assert by_case["ch04-nba-rhs-captured"].status is ResultStatus.UNSUPPORTED_CAPABILITY
    assert by_case["ch04-nba-rhs-captured"].reason is ReasonCode.UNSUPPORTED_PHASE


def test_unsupported_revision_is_not_a_normal_result(catalog: Catalog) -> None:
    original = catalog.cases["ch04-nba-rhs-captured"]
    applicability = dict(original.definition.revision_applicability)
    applicability[StandardRevision.IEEE_1800_2012] = Applicability.NOT_ASSESSED
    definition = original.definition.model_copy(update={"revision_applicability": applicability})
    loaded = LoadedCase(
        definition=definition,
        directory=original.directory,
        metadata_path=original.metadata_path,
        anchor_source=original.anchor_source,
        anchor_line=original.anchor_line,
        content_sha256=original.content_sha256,
    )
    fake = catalog.tools.tool("fake")
    old_profile = fake.headline_profile.model_copy(
        update={
            "standard_revision": StandardRevision.IEEE_1800_2012,
            "effective_language": "synthetic 1800-2012",
        }
    )
    old_fake = fake.model_copy(update={"profiles": (old_profile,)})
    custom = Catalog(
        root=catalog.root,
        inventory=catalog.inventory,
        tags=catalog.tags,
        cases={definition.id: loaded},
        suites={
            "revision-test": SuiteDefinition(
                schema_version=1,
                id="revision-test",
                description="Revision test.",
                cases=(definition.id,),
            )
        },
        suite_cases={"revision-test": (definition.id,)},
        tools=catalog.tools,
    )
    campaign = run_campaign(
        custom,
        (
            PreparedTool(
                definition=old_fake,
                profile=old_profile,
                selection=None,
                image=image_identity(),
                reported_version=None,
            ),
        ),
        suite_id="revision-test",
    )
    assert campaign.results[0].status is ResultStatus.UNSUPPORTED_REVISION


def test_missing_commercial_wrapper_is_skipped_by_generic_policy(
    catalog: Catalog,
) -> None:
    tool = catalog.tools.tool("vcs")
    campaign = run_campaign(
        catalog,
        (
            PreparedTool(
                definition=tool,
                profile=tool.profile("simulator"),
                selection=None,
                image=None,
                reported_version=None,
                wrapper=None,
            ),
        ),
        suite_id="smoke",
    )
    skipped = [
        result for result in campaign.results if result.status is ResultStatus.SKIPPED_UNAVAILABLE
    ]
    assert skipped
    assert all(result.reason is ReasonCode.TOOL_UNAVAILABLE for result in skipped)


def test_missing_allowlisted_license_environment_makes_wrapper_unavailable(
    monkeypatch,
) -> None:
    variable = "SVTORTURE_TEST_LICENSE_ENDPOINT"
    wrapper = WrapperDefinition(
        tool="licensed-simulator",
        command=("/bin/true",),
        environment_allowlist=(variable,),
    )
    monkeypatch.delenv(variable, raising=False)
    assert not wrapper_available(wrapper)
    monkeypatch.setenv(variable, "27000@example")
    assert wrapper_available(wrapper)


def test_no_artifacts_is_an_honest_missing_campaign(catalog: Catalog) -> None:
    campaign = create_missing_campaign(
        catalog,
        suite_id="smoke",
        expected_tool_ids=("slang",),
    )
    assert not campaign.complete
    assert campaign.tools == ()
    assert campaign.results == ()
    assert campaign.missing_tool_ids == ("slang",)
    verify_campaign_against_catalog(catalog, campaign)
    value = campaign.model_dump(mode="json")
    value["id"] = "../../outside"
    with pytest.raises(ValueError):
        campaign.__class__.model_validate(value)


def test_preparation_failure_emits_a_normalized_result_grid(catalog: Catalog) -> None:
    campaign = create_preparation_failure_campaign(
        catalog,
        suite_id="smoke",
        tool_id="slang",
    )
    assert not campaign.complete
    assert campaign.missing_tool_ids == ()
    assert len(campaign.tools) == 1
    tool = campaign.tools[0]
    assert tool.definition.id == "slang"
    assert tool.preparation_error
    assert tool.selection is None
    assert tool.image is None
    assert tool.reported_version is None
    assert len(campaign.results) == len(campaign.case_ids)
    assert any(
        result.reason is ReasonCode.TOOL_PREPARATION_FAILURE
        and result.status is ResultStatus.HARNESS_ERROR
        for result in campaign.results
    )
    assert any(
        result.reason is ReasonCode.UNSUPPORTED_PHASE
        and result.status is ResultStatus.UNSUPPORTED_CAPABILITY
        for result in campaign.results
    )
    assert all(result.reproduction_command is None for result in campaign.results)
    verify_campaign_against_catalog(catalog, campaign)


def test_aggregate_converts_preparation_failure_to_missing_tool(
    catalog: Catalog,
) -> None:
    preparation = create_preparation_failure_campaign(
        catalog,
        suite_id="smoke",
        tool_id="slang",
    )
    aggregate = aggregate_campaigns(catalog.root, (preparation,))
    assert not aggregate.complete
    assert aggregate.tools == ()
    assert aggregate.results == ()
    assert aggregate.expected_tool_ids == ("slang",)
    assert aggregate.missing_tool_ids == ("slang",)
    verify_campaign_against_catalog(catalog, aggregate)


def test_local_aggregate_preserves_the_measured_execution_platform(
    catalog: Catalog,
    tmp_path: Path,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    marker = case.definition.oracle.marker
    assert marker is not None
    fake = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    slang = campaign_tool(catalog.tools.tool("slang"), ("elaborator",))
    fake_campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=fake,
        results=(
            normalized(
                case,
                "fake",
                "simulator",
                observations=(
                    observation(
                        phase=Phase.SIMULATE,
                        stdout=marker,
                    ),
                ),
            ),
        ),
        campaign_id="20260101T000000Z-aggregate-fake",
    )
    slang_campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=slang,
        results=(
            normalized(
                case,
                "slang",
                "elaborator",
                status=ResultStatus.UNSUPPORTED_CAPABILITY,
                reason=ReasonCode.UNSUPPORTED_PHASE,
            ),
        ),
        campaign_id="20260101T000000Z-aggregate-slang",
    )
    root = tmp_path / "repo"
    for directory in ("standards", "suites", "tools", "cases"):
        shutil.copytree(catalog.root / directory, root / directory)
    aggregate = aggregate_campaigns(
        root,
        (fake_campaign, slang_campaign),
        expected_tools=("fake", "slang"),
    )
    assert aggregate.platform == "Linux x86_64"
    assert aggregate.complete
    assert all(aggregate.id in (result.reproduction_command or "") for result in aggregate.results)


def _variant(case: LoadedCase, root: Path) -> LoadedCase:
    variant_id = f"{case.definition.id}-variant"
    value = case.definition.model_dump(mode="json")
    value["id"] = variant_id
    value["title"] = "A second mandatory boundary variant"
    value["oracle"] = {
        "kind": OracleKind.RUNTIME_PASS_MARKER.value,
        "marker": f"SVTORTURE_PASS:{variant_id}",
    }
    definition = case.definition.__class__.model_validate(value)
    return LoadedCase(
        definition=definition,
        directory=root,
        metadata_path=root / "case.toml",
        anchor_source=None,
        anchor_line=None,
        content_sha256="2" * 64,
    )


def test_multiple_variants_do_not_increase_requirement_weight(
    catalog: Catalog, tmp_path: Path
) -> None:
    first = catalog.cases["ch04-nba-rhs-captured"]
    second = _variant(first, tmp_path)
    custom = copy_catalog(
        catalog,
        cases={
            first.definition.id: first,
            second.definition.id: second,
        },
    )
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        custom,
        cases=(first, second),
        tool=tool,
        results=(
            normalized(first, "fake", "simulator"),
            normalized(second, "fake", "simulator"),
        ),
    )
    metric = compute_metric(
        custom,
        campaign,
        tool.definition,
        tool.definition.profile("simulator"),
    )
    assert (metric.numerator, metric.denominator) == (1, 1)


def test_all_mandatory_variants_must_conform(catalog: Catalog, tmp_path: Path) -> None:
    first = catalog.cases["ch04-nba-rhs-captured"]
    second = _variant(first, tmp_path)
    custom = copy_catalog(
        catalog,
        cases={
            first.definition.id: first,
            second.definition.id: second,
        },
    )
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        custom,
        cases=(first, second),
        tool=tool,
        results=(
            normalized(first, "fake", "simulator"),
            normalized(
                second,
                "fake",
                "simulator",
                status=ResultStatus.NONCONFORMING,
                reason=ReasonCode.WRONG_RUNTIME_RESULT,
            ).model_copy(update={"known_issue": "Tracked defect remains a failure."}),
        ),
    )
    metric = compute_metric(
        custom,
        campaign,
        tool.definition,
        tool.definition.profile("simulator"),
    )
    assert (metric.numerator, metric.denominator, metric.nonconforming) == (0, 1, 1)


def test_harness_error_invalidates_headline_metric(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "fake",
                "simulator",
                status=ResultStatus.HARNESS_ERROR,
                reason=ReasonCode.CONTAINER_FAILURE,
            ),
        ),
        complete=False,
    )
    metric = compute_metric(
        catalog,
        campaign,
        tool.definition,
        tool.definition.profile("simulator"),
    )
    assert not metric.valid
    assert not metric.complete
    assert metric.infrastructure_state == "harness-error"


def test_another_missing_tool_does_not_make_an_executed_profile_incomplete(
    catalog: Catalog,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
        expected_tool_ids=("fake", "slang"),
        missing_tool_ids=("slang",),
        complete=False,
    )
    metric = compute_metric(
        catalog,
        campaign,
        tool.definition,
        tool.definition.profile("simulator"),
    )
    assert metric.complete
    assert metric.valid
