from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from svtorture.campaign import (
    CampaignError,
    load_campaign,
    verify_campaign_against_catalog,
)
from svtorture.catalog import Catalog, CatalogError, load_catalog, mvp_audit
from svtorture.evaluator import synthetic_result
from svtorture.models import (
    Campaign,
    CaseDefinition,
    EvidenceMode,
    NormalizedResult,
    Phase,
    ReasonCode,
    RequirementInventory,
    ResultStatus,
    ToolProfile,
    safe_relative_path,
)
from tests.helpers import campaign_tool, make_campaign, normalized


def _copy_catalog_tree(catalog: Catalog, destination: Path) -> None:
    for directory in ("standards", "suites", "tools", "cases"):
        source = catalog.root / directory
        target = destination / directory
        if directory != "standards":
            shutil.copytree(source, target)
            continue
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("ieee-1800-2023-annotate"),
        )


def test_seed_catalog_meets_mvp(catalog: Catalog) -> None:
    assert catalog.inventory.schema_version == 2
    counts = mvp_audit(catalog)
    assert counts["cases"] == 12
    assert counts["chapters"] == 11
    assert counts["simulation_acceptance"] >= 4
    assert counts["rejection"] >= 2


def test_repository_directories_have_navigation_readmes(catalog: Catalog) -> None:
    top_level = (
        "cases",
        "dashboard",
        "docs",
        "schemas",
        "scripts",
        "src",
        "standards",
        "suites",
        "templates",
        "tests",
        "tools",
    )
    tool_directories = ("fake-tool", "icarus", "slang", "vcs", "verilator")
    assert all((catalog.root / directory / "README.md").is_file() for directory in top_level)
    assert all(
        (catalog.root / "tools" / directory / "README.md").is_file()
        for directory in tool_directories
    )


def test_tool_recipes_are_colocated_under_tools(catalog: Catalog) -> None:
    expected_directories = {
        "fake": "fake-tool",
        "icarus": "icarus",
        "slang": "slang",
        "verilator": "verilator",
    }
    for tool_id, directory in expected_directories.items():
        tool = catalog.tools.tool(tool_id)
        assert tool.dockerfile == f"tools/{directory}/Dockerfile"
        assert (catalog.root / "tools" / directory / "README.md").is_file()


def test_generated_schemas_use_the_controlled_tag_registry(catalog: Catalog) -> None:
    expected = [tag.id for tag in catalog.tags.tags]
    case_schema = json.loads((catalog.root / "schemas" / "case.schema.json").read_text())
    requirement_schema = json.loads(
        (catalog.root / "schemas" / "requirements.schema.json").read_text()
    )
    assert case_schema["properties"]["tags"]["items"]["enum"] == expected
    requirement_properties = requirement_schema["$defs"]["Requirement"]["properties"]
    assert requirement_properties["tags"]["items"]["enum"] == expected
    assert requirement_properties["anchors"]["minItems"] == 1
    assert requirement_properties["anchors"]["uniqueItems"] is True
    assert "paragraph_anchor" not in requirement_properties


def test_tool_phase_ceiling_is_cumulative(catalog: Catalog) -> None:
    simulator = catalog.tools.tool("verilator").profile("simulator")
    assert simulator.phase_ceiling is Phase.SIMULATE
    assert simulator.supports(Phase.PREPROCESS)
    assert simulator.supports(Phase.PARSE)
    assert simulator.supports(Phase.ELABORATE)
    assert simulator.supports(Phase.SIMULATE)
    assert Phase.PARSE not in simulator.direct_phases


def test_legacy_tool_phase_list_is_rejected(catalog: Catalog) -> None:
    profile = catalog.tools.tool("verilator").profile("simulator")
    value = profile.model_dump(mode="json")
    value["phases"] = ["elaborate", "simulate"]
    del value["phase_ceiling"]
    del value["direct_phases"]
    with pytest.raises(ValidationError, match=r"phase_ceiling|direct_phases"):
        ToolProfile.model_validate(value)


def test_unknown_metadata_is_rejected(catalog: Catalog) -> None:
    value = catalog.cases["ch04-nba-rhs-captured"].definition.model_dump(mode="json")
    value["unknown_field"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CaseDefinition.model_validate(value)


def test_boolean_schema_version_is_rejected(catalog: Catalog) -> None:
    value = catalog.cases["ch04-nba-rhs-captured"].definition.model_dump(mode="json")
    value["schema_version"] = True
    with pytest.raises(ValidationError, match="valid integer"):
        CaseDefinition.model_validate(value)


def test_retired_requirement_schema_version_is_rejected(catalog: Catalog) -> None:
    value = catalog.inventory.model_dump(mode="json")
    value["schema_version"] = 1
    with pytest.raises(ValidationError, match="greater than or equal to 2"):
        RequirementInventory.model_validate(value)


@pytest.mark.parametrize(
    "value",
    ("../escape.sv", "/absolute.sv", "nested/../escape.sv", r"windows\\escape.sv"),
)
def test_path_traversal_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="unsafe relative path"):
        safe_relative_path(value)


def test_duplicate_requirement_ids_are_rejected(catalog: Catalog) -> None:
    inventory = catalog.inventory.model_dump(mode="json")
    inventory["requirements"].append(inventory["requirements"][0])
    with pytest.raises(ValidationError, match="duplicate requirement ids"):
        RequirementInventory.model_validate(inventory)


def test_requirement_anchors_are_nonempty_and_unique(catalog: Catalog) -> None:
    inventory = catalog.inventory.model_dump(mode="json")
    requirement = inventory["requirements"][0]
    requirement["anchors"] = []
    with pytest.raises(ValidationError, match="at least 1 item"):
        RequirementInventory.model_validate(inventory)

    requirement["anchors"] = ["[2023:4.9.4:P001:p070]"] * 2
    with pytest.raises(ValidationError, match="duplicate requirement anchors"):
        RequirementInventory.model_validate(inventory)


def test_retired_paragraph_anchor_is_rejected(catalog: Catalog) -> None:
    inventory = catalog.inventory.model_dump(mode="json")
    inventory["requirements"][0]["paragraph_anchor"] = "retired informal anchor"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RequirementInventory.model_validate(inventory)


def test_catalog_rejects_anchor_absent_from_pinned_standard(
    catalog: Catalog, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    chapter = root / "standards" / "requirements" / "chapter-04.toml"
    chapter.write_text(
        chapter.read_text(encoding="utf-8").replace(
            "[2023:4.9.4:P001:p070]",
            "[2023:4.9.4:P999:p999]",
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="absent from committed IEEE 1800-2023 index"):
        load_catalog(root)


def test_catalog_loads_without_materialized_annotation(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    assert not (root / "standards" / "ieee-1800-2023-annotate").exists()
    load_catalog(root)


def test_catalog_requires_vendored_anchor_index(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    (root / "standards" / "ieee-1800-2023-anchors.json").unlink()
    with pytest.raises(CatalogError, match="cannot read JSON"):
        load_catalog(root)


def test_catalog_accepts_an_explicit_runtime_anchor_index(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    (root / "standards" / "ieee-1800-2023-anchors.json").unlink()
    anchor_index = catalog.root / "standards" / "ieee-1800-2023-anchors.json"
    loaded = load_catalog(root, anchor_index=anchor_index)
    assert loaded.anchor_index == anchor_index.resolve()


def test_catalog_rejects_duplicate_case_directory(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    duplicate = root / "cases" / "different-directory"
    shutil.copytree(root / "cases" / "ch04-nba-rhs-captured", duplicate)
    with pytest.raises(CatalogError, match="containing directory"):
        load_catalog(root)


def test_catalog_rejects_a_symlinked_case_source(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    case_directory = root / "cases" / "ch04-nba-rhs-captured"
    source = case_directory / "top.sv"
    source.rename(case_directory / "actual.sv")
    source.symlink_to("actual.sv")
    with pytest.raises(CatalogError, match="symbolic link"):
        load_catalog(root)


def test_requirement_chapter_must_match_index(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    chapter = root / "standards" / "requirements" / "chapter-04.toml"
    chapter.write_text(
        chapter.read_text(encoding="utf-8").replace("chapter = 4", "chapter = 5", 1),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="chapter"):
        load_catalog(root)


def test_unknown_controlled_tag_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    metadata = root / "cases" / "ch04-nba-rhs-captured" / "case.toml"
    metadata.write_text(
        metadata.read_text(encoding="utf-8").replace(
            'tags = ["nba", "scheduling"]',
            'tags = ["nba", "scheduling", "zz-unknown"]',
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="unknown tags: zz-unknown"):
        load_catalog(root)


def test_unknown_requirement_tag_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    chapter = root / "standards" / "requirements" / "chapter-04.toml"
    chapter.write_text(
        chapter.read_text(encoding="utf-8").replace(
            'tags = ["nba", "scheduling"]',
            'tags = ["nba", "scheduling", "zz-unknown"]',
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="unknown tags: zz-unknown"):
        load_catalog(root)


def test_unsorted_tags_are_rejected(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    metadata = root / "cases" / "ch04-nba-rhs-captured" / "case.toml"
    metadata.write_text(
        metadata.read_text(encoding="utf-8").replace(
            'tags = ["nba", "scheduling"]',
            'tags = ["scheduling", "nba"]',
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="tags must be sorted"):
        load_catalog(root)


def test_suite_globs_expand_deterministically(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    (root / "suites" / "chapter-12.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                'id = "chapter-12"',
                'description = "Chapter 12 cases."',
                'cases = ["ch12-*", "ch12-if-*"]',
                "",
            )
        ),
        encoding="utf-8",
    )
    loaded = load_catalog(root)
    assert loaded.suite_cases["all"] == tuple(sorted(loaded.cases))
    assert loaded.suite_cases["chapter-12"] == (
        "ch12-if-x-takes-else",
        "ch12-unique-if-no-match-diagnostic",
    )


def test_suite_glob_without_matches_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    (root / "suites" / "empty.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                'id = "empty"',
                'description = "Invalid empty selection."',
                'cases = ["ch99-*"]',
                "",
            )
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="matched no cases"):
        load_catalog(root)


def test_version_two_campaign_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
    )
    value = campaign.model_dump(mode="json")
    value["schema_version"] = 2
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(CampaignError, match="greater than or equal to 3"):
        load_campaign(path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda value: value.pop("corpus_metrics"),
            "corpus_metrics",
        ),
        (
            lambda value: value["corpus_metrics"]["requirements"]["coverage"].update(
                {"numerator": 20000}
            ),
            "coverage numerator",
        ),
        (
            lambda value: value["corpus_metrics"]["cases"]["density"].update({"denominator": 0}),
            "density denominator",
        ),
    ),
)
def test_campaign_requires_coherent_corpus_metrics(
    catalog: Catalog,
    mutate,
    message: str,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
    )
    value = campaign.model_dump(mode="json")
    mutate(value)
    with pytest.raises(ValidationError, match=message):
        Campaign.model_validate(value)


@pytest.mark.parametrize("value", ("16", True, 16.0))
def test_campaign_corpus_operands_reject_coercion(
    catalog: Catalog,
    value: object,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
    )
    payload = campaign.model_dump(mode="json")
    payload["corpus_metrics"]["requirements"]["coverage"]["numerator"] = value
    with pytest.raises(ValidationError, match="valid integer"):
        Campaign.model_validate(payload)


def test_result_evidence_mode_must_match_observations(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    value = normalized(case, "fake", "simulator").model_dump(mode="json")
    value["evidence_mode"] = "cumulative"
    with pytest.raises(ValidationError, match="evidence mode"):
        NormalizedResult.model_validate(value)


@pytest.mark.parametrize(
    ("update", "message"),
    (
        (
            {
                "target_phase": Phase.PARSE,
                "evidence_mode": EvidenceMode.CUMULATIVE,
            },
            "wrong target phase",
        ),
        ({"evidence_mode": EvidenceMode.CUMULATIVE}, "does not match observations"),
    ),
)
def test_campaign_phase_provenance_tamper_is_rejected(
    catalog: Catalog,
    update: dict[str, object],
    message: str,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    result = normalized(case, "fake", "simulator")
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(result,),
    ).model_copy(update={"results": (result.model_copy(update=update),)})
    with pytest.raises(CampaignError, match=message):
        verify_campaign_against_catalog(catalog, campaign)


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        (ResultStatus.UNSUPPORTED_CAPABILITY, ReasonCode.UNSUPPORTED_PHASE),
        (ResultStatus.HARNESS_ERROR, ReasonCode.INVALID_EXECUTION_PLAN),
    ),
)
def test_supported_case_cannot_be_suppressed_without_observations(
    catalog: Catalog,
    status: ResultStatus,
    reason: ReasonCode,
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("icarus"), ("simulator",))
    result = synthetic_result(
        case,
        "icarus",
        "simulator",
        status,
        reason,
        "tampered observation-free result",
    )
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(result,),
        complete=status is not ResultStatus.HARNESS_ERROR,
    )
    with pytest.raises(CampaignError, match=r"observations|structural result"):
        verify_campaign_against_catalog(catalog, campaign)


def test_campaign_manifest_tamper_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    definition = catalog.tools.tool("fake")
    tool = campaign_tool(definition, ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
    )
    value = campaign.model_dump(mode="json")
    value["hashes"]["cases"] = "f" * 64
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(CampaignError, match="case manifest hash mismatch"):
        load_campaign(path)


def test_campaign_selection_tamper_is_rejected(catalog: Catalog, tmp_path: Path) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
    )
    value = campaign.model_dump(mode="json")
    value["selection_name"] = "tampered"
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(CampaignError, match="selection manifest hash mismatch"):
        load_campaign(path)
