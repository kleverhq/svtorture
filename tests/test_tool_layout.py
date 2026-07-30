from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from svtorture.campaign import CampaignError, load_runner_config
from svtorture.catalog import Catalog, CatalogError, load_catalog
from svtorture.models import RunnerConfig, ToolIndex, ToolManifest


def _copy_tools(catalog: Catalog, destination: Path) -> None:
    shutil.copytree(catalog.root / "tools", destination / "tools")
    (destination / "tools" / "vcs" / "runner.toml").unlink(missing_ok=True)


def _copy_catalog_tree(catalog: Catalog, destination: Path) -> None:
    for directory in ("standards", "suites", "tools", "cases"):
        shutil.copytree(catalog.root / directory, destination / directory)
    (destination / "tools" / "vcs" / "runner.toml").unlink(missing_ok=True)


def test_tool_index_lists_colocated_strict_manifests(catalog: Catalog) -> None:
    tools_directory = catalog.root / "tools"
    with (tools_directory / "tools.toml").open("rb") as stream:
        index = ToolIndex.model_validate(tomllib.load(stream))

    assert index.manifests == (
        "slang/tool.toml",
        "icarus/tool.toml",
        "verilator/tool.toml",
        "vcs/tool.toml",
        "fake-tool/tool.toml",
    )
    for relative in index.manifests:
        path = tools_directory / relative
        with path.open("rb") as stream:
            manifest = ToolManifest.model_validate(tomllib.load(stream))
        assert manifest.id == path.parent.name.replace("fake-tool", "fake")


def test_tool_index_rejects_unsafe_duplicate_and_unknown_entries() -> None:
    with pytest.raises(ValidationError):
        ToolIndex.model_validate({"schema_version": 1, "manifests": ["../vcs/tool.toml"]})
    with pytest.raises(ValidationError):
        ToolIndex.model_validate({"schema_version": 1, "manifests": ["tool.toml"]})
    with pytest.raises(ValidationError):
        ToolIndex.model_validate({"schema_version": 1, "manifests": ["vcs/config.toml"]})
    with pytest.raises(ValidationError):
        ToolIndex.model_validate(
            {"schema_version": 1, "manifests": ["vcs/tool.toml", "vcs/tool.toml"]}
        )
    with pytest.raises(ValidationError):
        ToolIndex.model_validate(
            {"schema_version": 1, "manifests": ["vcs/tool.toml"], "scan": True}
        )


def test_catalog_rejects_missing_manifest_and_duplicate_tool_ids(
    catalog: Catalog, tmp_path: Path
) -> None:
    missing_root = tmp_path / "missing"
    duplicate_root = tmp_path / "duplicate"
    _copy_catalog_tree(catalog, missing_root)
    _copy_catalog_tree(catalog, duplicate_root)

    (missing_root / "tools" / "vcs" / "tool.toml").unlink()
    with pytest.raises(CatalogError, match="missing or unsafe tool manifest"):
        load_catalog(missing_root)

    shutil.copytree(duplicate_root / "tools" / "vcs", duplicate_root / "tools" / "vcs-copy")
    index_path = duplicate_root / "tools" / "tools.toml"
    index_path.write_text(
        index_path.read_text(encoding="utf-8").replace(
            '  "fake-tool/tool.toml",',
            '  "fake-tool/tool.toml",\n  "vcs-copy/tool.toml",',
        ),
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="duplicate tool ids"):
        load_catalog(duplicate_root)


def test_catalog_rejects_manifest_reached_through_symlink(catalog: Catalog, tmp_path: Path) -> None:
    _copy_catalog_tree(catalog, tmp_path)
    vcs = tmp_path / "tools" / "vcs"
    vcs.rename(tmp_path / "tools" / "vcs-real")
    vcs.symlink_to("vcs-real", target_is_directory=True)

    with pytest.raises(CatalogError, match="missing or unsafe tool manifest"):
        load_catalog(tmp_path)


def test_generated_schemas_describe_index_and_per_tool_manifest(catalog: Catalog) -> None:
    index_schema = json.loads((catalog.root / "schemas" / "tools.schema.json").read_text())
    manifest_schema = json.loads((catalog.root / "schemas" / "tool.schema.json").read_text())

    assert set(index_schema["properties"]) == {"schema_version", "manifests"}
    assert "diagnostic_rules" in manifest_schema["properties"]
    assert "runner_config" in manifest_schema["properties"]
    assert manifest_schema["additionalProperties"] is False


def test_manifest_paths_are_normalized_and_rules_are_owned_by_tool(catalog: Catalog) -> None:
    slang = catalog.tools.tool("slang")
    fake = catalog.tools.tool("fake")
    vcs = catalog.tools.tool("vcs")

    assert slang.dockerfile == "tools/slang/Dockerfile"
    assert fake.recipe_files == ("tools/fake-tool/fake_tool.py",)
    assert vcs.runner_config == "tools/vcs/runner.toml"
    assert [(rule.case, rule.contains) for rule in vcs.diagnostic_rules] == [
        ("ch05-base-format-whitespace-rejected", "syntax error"),
        ("ch23-mixed-port-style-rejected", "port connection"),
    ]
    assert all(not tool.diagnostic_rules for tool in catalog.tools.tools if tool.id != "vcs")


def test_manifest_and_runner_models_reject_unknown_or_aggregate_fields(
    catalog: Catalog,
) -> None:
    vcs = catalog.tools.tool("vcs").model_dump(mode="json")
    vcs["schema_version"] = 1
    vcs["unexpected"] = True
    with pytest.raises(ValidationError):
        ToolManifest.model_validate(vcs)

    vcs.pop("unexpected")
    vcs["diagnostic_rules"].append(vcs["diagnostic_rules"][0])
    with pytest.raises(ValidationError, match="duplicate diagnostic rules"):
        ToolManifest.model_validate(vcs)

    with pytest.raises(ValidationError):
        RunnerConfig.model_validate(
            {
                "schema_version": 1,
                "wrappers": [{"tool": "vcs", "command": ["/bin/true"]}],
            }
        )


def test_missing_and_valid_per_tool_runner_configuration(catalog: Catalog, tmp_path: Path) -> None:
    _copy_tools(catalog, tmp_path)
    vcs = catalog.tools.tool("vcs")

    assert load_runner_config(tmp_path, vcs) is None

    runner_path = tmp_path / "tools" / "vcs" / "runner.toml"
    runner_path.write_text(
        'schema_version = 1\ncommand = ["/bin/true"]\n'
        'environment_allowlist = ["SVTORTURE_TEST_LICENSE"]\n',
        encoding="utf-8",
    )
    runner = load_runner_config(tmp_path, vcs)
    assert runner is not None
    assert runner.command == ("/bin/true",)
    assert runner.environment_allowlist == ("SVTORTURE_TEST_LICENSE",)


def test_malformed_or_symlinked_runner_fails_explicitly(catalog: Catalog, tmp_path: Path) -> None:
    _copy_tools(catalog, tmp_path)
    vcs = catalog.tools.tool("vcs")
    runner_path = tmp_path / "tools" / "vcs" / "runner.toml"
    runner_path.write_text("schema_version = true\ncommand = []\n", encoding="utf-8")
    with pytest.raises(CampaignError, match="runner configuration"):
        load_runner_config(tmp_path, vcs)

    runner_path.unlink()
    runner_path.symlink_to("runner.example.toml")
    with pytest.raises(CampaignError, match="symbolic links"):
        load_runner_config(tmp_path, vcs)

    runner_path.unlink()
