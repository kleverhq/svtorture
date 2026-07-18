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


def test_seed_catalog_meets_mvp(catalog: Catalog) -> None:
    counts = mvp_audit(catalog)
    assert counts["cases"] == 12
    assert counts["chapters"] == 11
    assert counts["simulation_acceptance"] >= 4
    assert counts["rejection"] >= 2


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


def test_catalog_rejects_duplicate_case_directory(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    shutil.copytree(catalog.root / "standards", root / "standards")
    shutil.copytree(catalog.root / "suites", root / "suites")
    shutil.copytree(catalog.root / "toolchains", root / "toolchains")
    shutil.copytree(catalog.root / "containers", root / "containers")
    shutil.copytree(catalog.root / "cases", root / "cases")
    duplicate = root / "cases" / "different-directory"
    shutil.copytree(root / "cases" / "ch04-nba-rhs-captured", duplicate)
    with pytest.raises(CatalogError, match="containing directory"):
        load_catalog(root)


def test_catalog_rejects_a_symlinked_case_source(catalog: Catalog, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    for directory in ("standards", "suites", "toolchains", "containers", "cases"):
        shutil.copytree(catalog.root / directory, root / directory)
    case_directory = root / "cases" / "ch04-nba-rhs-captured"
    source = case_directory / "top.sv"
    source.rename(case_directory / "actual.sv")
    source.symlink_to("actual.sv")
    with pytest.raises(CatalogError, match="symbolic link"):
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
