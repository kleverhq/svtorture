from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from svtorture.campaign import CampaignError, load_campaign
from svtorture.catalog import Catalog, CatalogError, load_catalog, mvp_audit
from svtorture.models import (
    CaseDefinition,
    RequirementInventory,
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
            ignore=shutil.ignore_patterns("ieee-1800-2023-annotated"),
        )
        annotated = target / "ieee-1800-2023-annotated"
        annotated.mkdir()
        shutil.copy2(
            source / "ieee-1800-2023-annotated" / "anchors.json",
            annotated / "anchors.json",
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
        ".github",
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
    with pytest.raises(CatalogError, match="absent from pinned annotated standard"):
        load_catalog(root)


def test_catalog_requires_annotated_anchor_index(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_catalog_tree(catalog, root)
    (root / "standards" / "ieee-1800-2023-annotated" / "anchors.json").unlink()
    with pytest.raises(CatalogError, match="cannot read JSON"):
        load_catalog(root)


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
