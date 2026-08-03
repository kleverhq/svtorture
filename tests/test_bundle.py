from __future__ import annotations

import json
import struct
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from svtorture.bundle import (
    assemble_dashboard_data,
    assemble_public_pages,
    export_campaign_bundle,
    extract_campaign_archive,
    pack_evidence,
    pack_evidence_results,
    project_campaign_summary,
    project_verdicts,
    sha256_file,
    validate_campaign_bundle,
    write_campaign_archive,
)
from svtorture.catalog import Catalog
from svtorture.dashboard_models import (
    ArchiveMetadata,
    CampaignCaseVerdicts,
    CampaignCatalog,
    CampaignSummary,
    CampaignVerdict,
    CampaignVerdicts,
    DashboardEvidenceResult,
)
from svtorture.hashing import canonical_json_bytes, sha256_bytes
from svtorture.models import (
    EvidenceLevel,
    EvidenceMode,
    NormalizedResult,
    Phase,
    ReasonCode,
    ResultStatus,
)
from svtorture.publish import PublicationError
from tests.helpers import campaign_tool, make_campaign, normalized, observation


def _campaign(catalog: Catalog):
    cases = (
        catalog.cases["ch04-nba-rhs-captured"],
        catalog.cases["ch13-output-copyout-width"],
    )
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    results = tuple(
        normalized(
            case,
            "fake",
            "simulator",
            observations=(
                observation(attempted_through_phase=Phase.ELABORATE),
                observation(
                    attempted_through_phase=Phase.SIMULATE,
                    stdout=case.definition.oracle.marker or "runtime output",
                ),
            ),
        )
        for case in cases
    )
    return make_campaign(catalog, cases=cases, tool=tool, results=results)


def test_bundle_export_is_compact_complete_and_deterministic(
    catalog: Catalog, tmp_path: Path
) -> None:
    campaign = _campaign(catalog)
    first = export_campaign_bundle(catalog, campaign, tmp_path / "first")
    second = export_campaign_bundle(catalog, campaign, tmp_path / "second")

    first_manifest = validate_campaign_bundle(first)
    second_manifest = validate_campaign_bundle(second)
    assert first_manifest == second_manifest
    assert first_manifest.resources.verdicts.case_count == 2
    assert first_manifest.resources.verdicts.result_count == 2
    assert first_manifest.metrics[0].corpus_sha == campaign.hashes.cases
    exported_catalog = CampaignCatalog.model_validate_json(
        (first / "catalog.json").read_text(encoding="utf-8")
    )
    assert exported_catalog.standard_sections == catalog.standard_sections
    assert len(exported_catalog.standard_sections) == 1740

    historical_catalog = exported_catalog.model_dump(mode="json")
    del historical_catalog["standard_sections"]
    assert CampaignCatalog.model_validate(historical_catalog).standard_sections == ()

    empty_catalog = exported_catalog.model_dump(mode="json")
    empty_catalog["standard_sections"] = []
    with pytest.raises(ValidationError, match="at least 1740 items"):
        CampaignCatalog.model_validate(empty_catalog)

    malformed_catalog = exported_catalog.model_dump(mode="json")
    malformed_catalog["standard_sections"][0], malformed_catalog["standard_sections"][1] = (
        malformed_catalog["standard_sections"][1],
        malformed_catalog["standard_sections"][0],
    )
    with pytest.raises(ValidationError, match="canonically sorted"):
        CampaignCatalog.model_validate(malformed_catalog)

    first_files = {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
    assert all(not data.endswith(b"\n") for data in first_files.values())
    assert all(b'": ' not in data for data in first_files.values())

    evidence = json.loads((first / "evidence" / "0000.json").read_text(encoding="utf-8"))
    exported = evidence["results"][0]
    canonical = next(result for result in campaign.results if result.case_id == exported["case_id"])
    assert "reproduction_command" not in exported
    assert (
        exported["observations"][0]["stdout"]
        == canonical.model_dump(mode="json")["observations"][0]["stdout"]
    )

    first_zip = write_campaign_archive(first, tmp_path / "first.zip")
    second_zip = write_campaign_archive(second, tmp_path / "second.zip")
    assert first_zip.read_bytes() == second_zip.read_bytes()
    with zipfile.ZipFile(first_zip) as archive:
        assert all(name.startswith(f"campaigns/{campaign.id}/") for name in archive.namelist())
        assert "index.json" not in archive.namelist()
        assert "trends.json" not in archive.namelist()


def test_bundle_packing_keeps_cases_intact_and_obeys_limits(catalog: Catalog) -> None:
    campaign = _campaign(catalog)
    by_count = pack_evidence(campaign, max_cases=1)
    assert [len(shard.case_ids) for shard in by_count] == [1, 1]
    assert all(
        {result.case_id for result in shard.results} == set(shard.case_ids) for shard in by_count
    )

    by_size = pack_evidence(campaign, target_bytes=1)
    assert [len(shard.case_ids) for shard in by_size] == [1, 1]
    assert [shard.case_ids[0] for shard in by_size] == sorted(campaign.case_ids)


def _write_compact(path: Path, value: object) -> bytes:
    data = canonical_json_bytes(value)
    path.write_bytes(data)
    return data


def test_historical_bundle_without_standard_sections_still_validates_and_assembles(
    catalog: Catalog, tmp_path: Path
) -> None:
    root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "historical")
    catalog_path = root / "catalog.json"
    historical_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    del historical_catalog["standard_sections"]
    catalog_bytes = canonical_json_bytes(historical_catalog)
    catalog_path.write_bytes(catalog_bytes)

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["resources"]["catalog"]["bytes"] = len(catalog_bytes)
    manifest["resources"]["catalog"]["sha256"] = sha256_bytes(catalog_bytes)
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    assert validate_campaign_bundle(root).id == manifest["id"]
    index = assemble_dashboard_data(
        (root,),
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )
    assert index.default_campaign_id == manifest["id"]


def test_bundle_validation_recomputes_selection_judgments_and_metrics(
    catalog: Catalog, tmp_path: Path
) -> None:
    selection_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "selection")
    manifest_path = selection_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["selection_name"] = "forged-selection"
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="selection hash"):
        validate_campaign_bundle(selection_root)

    metric_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "metric")
    manifest_path = metric_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["metrics"][0]["label"] = "Forged metric"
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="metric does not match"):
        validate_campaign_bundle(metric_root)

    judgment_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "judgment")
    manifest_path = judgment_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evidence_resource = manifest["resources"]["evidence"][0]
    evidence_path = judgment_root / evidence_resource["href"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["results"][0]["status"] = "nonconforming"
    evidence["results"][0]["reason"] = "unexpected-accept"
    evidence_data = _write_compact(evidence_path, evidence)
    evidence_resource["bytes"] = len(evidence_data)
    evidence_resource["sha256"] = sha256_bytes(evidence_data)

    verdict_resource = manifest["resources"]["verdicts"]
    verdict_path = judgment_root / verdict_resource["href"]
    verdicts = json.loads(verdict_path.read_text(encoding="utf-8"))
    verdicts["cases"][0]["results"][0]["status"] = "nonconforming"
    verdicts["cases"][0]["results"][0]["reason"] = "unexpected-accept"
    verdict_data = _write_compact(verdict_path, verdicts)
    verdict_resource["bytes"] = len(verdict_data)
    verdict_resource["sha256"] = sha256_bytes(verdict_data)
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="judgment is invalid"):
        validate_campaign_bundle(judgment_root)

    definition_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "definition")
    manifest_path = definition_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog_resource = manifest["resources"]["catalog"]
    catalog_path = definition_root / catalog_resource["href"]
    catalog_value = json.loads(catalog_path.read_text(encoding="utf-8"))
    selected_id = manifest["cases"][0]["id"]
    selected_case = next(case for case in catalog_value["cases"] if case["id"] == selected_id)
    selected_case["title"] = "Forged case definition"
    definition = {
        key: value
        for key, value in selected_case.items()
        if key not in {"content_sha256", "definition_sha256", "source_links"}
    }
    selected_case["definition_sha256"] = sha256_bytes(canonical_json_bytes(definition))
    catalog_data = _write_compact(catalog_path, catalog_value)
    catalog_resource["bytes"] = len(catalog_data)
    catalog_resource["sha256"] = sha256_bytes(catalog_data)
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="case identity"):
        validate_campaign_bundle(definition_root)

    source_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "source-link")
    manifest_path = source_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog_resource = manifest["resources"]["catalog"]
    catalog_path = source_root / catalog_resource["href"]
    catalog_value = json.loads(catalog_path.read_text(encoding="utf-8"))
    first_source = next(iter(catalog_value["cases"][0]["source_links"]))
    catalog_value["cases"][0]["source_links"][first_source] = "https://example.com/forged.sv"
    catalog_data = _write_compact(catalog_path, catalog_value)
    catalog_resource["bytes"] = len(catalog_data)
    catalog_resource["sha256"] = sha256_bytes(catalog_data)
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="source link"):
        validate_campaign_bundle(source_root)


def test_bundle_validation_rejects_integrity_changes_and_unexpected_files(
    catalog: Catalog, tmp_path: Path
) -> None:
    root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path)
    catalog_path = root / "catalog.json"
    catalog_path.write_bytes(catalog_path.read_bytes() + b" ")
    with pytest.raises(PublicationError, match="integrity mismatch"):
        validate_campaign_bundle(root)

    root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "clean")
    (root / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PublicationError, match="unexpected or missing"):
        validate_campaign_bundle(root)


def test_bundle_validation_rejects_symlinks_and_oversized_manifest(
    catalog: Catalog, tmp_path: Path
) -> None:
    root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "symlink")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "linked.json").symlink_to(outside)
    with pytest.raises(PublicationError, match="symlink"):
        validate_campaign_bundle(root)

    clean_bundle = tmp_path / "clean-bundle"
    export_campaign_bundle(catalog, _campaign(catalog), clean_bundle)
    bundle_alias = tmp_path / "bundle-alias"
    bundle_alias.symlink_to(clean_bundle, target_is_directory=True)
    with pytest.raises(PublicationError, match="path contains a symlink"):
        write_campaign_archive(bundle_alias, tmp_path / "alias.zip")

    oversized = tmp_path / "oversized" / "campaigns" / "20260101T000000Z-oversized"
    oversized.mkdir(parents=True)
    with (oversized / "manifest.json").open("wb") as output:
        output.truncate(16 * 1024 * 1024 + 1)
    with pytest.raises(PublicationError, match="size limit"):
        validate_campaign_bundle(oversized)

    aggregate_root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "aggregate")
    manifest_path = aggregate_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["resources"]["evidence"].extend(
        {
            "href": f"evidence/extra-{index:04d}.json",
            "sha256": "0" * 64,
            "bytes": 128 * 1024 * 1024,
            "case_count": 0,
            "result_count": 0,
        }
        for index in range(16)
    )
    _write_compact(manifest_path, manifest)
    with pytest.raises(PublicationError, match="aggregate resource limit"):
        validate_campaign_bundle(aggregate_root)


def test_archive_extraction_rejects_unsafe_members_and_validates_bundle(
    catalog: Catalog, tmp_path: Path
) -> None:
    root = export_campaign_bundle(catalog, _campaign(catalog), tmp_path / "source")
    archive = write_campaign_archive(root, tmp_path / "campaign.zip")
    extracted = extract_campaign_archive(archive, tmp_path / "extracted")
    assert validate_campaign_bundle(extracted).id == root.name

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as output:
        output.writestr("campaigns/example/../../outside", b"bad")
    with pytest.raises(PublicationError, match="unsafe campaign archive member"):
        extract_campaign_archive(unsafe, tmp_path / "unsafe-output")

    aliased = tmp_path / "aliased.zip"
    with zipfile.ZipFile(aliased, "w") as output:
        output.writestr("campaigns/example/./manifest.json", b"{}")
    with pytest.raises(PublicationError, match="unsafe campaign archive member"):
        extract_campaign_archive(aliased, tmp_path / "aliased-output")

    too_many = tmp_path / "too-many.zip"
    too_many.write_bytes(
        struct.pack(
            "<4s4H2LH",
            b"PK\x05\x06",
            0,
            0,
            20_001,
            20_001,
            0,
            0,
            0,
        )
    )
    with pytest.raises(PublicationError, match="unsafe member count"):
        extract_campaign_archive(too_many, tmp_path / "too-many-output")


def test_local_assembler_combines_directories_and_zips(catalog: Catalog, tmp_path: Path) -> None:
    first_campaign = _campaign(catalog)
    second_campaign = first_campaign.model_copy(
        update={
            "id": "20260102T000000Z-second-campaign",
            "started_at": first_campaign.started_at + timedelta(days=1),
            "finished_at": first_campaign.finished_at + timedelta(days=1),
        }
    )
    first = export_campaign_bundle(catalog, first_campaign, tmp_path / "first")
    second = export_campaign_bundle(catalog, second_campaign, tmp_path / "second")
    second_zip = write_campaign_archive(second, tmp_path / "second.zip")

    output = tmp_path / "data"
    index = assemble_dashboard_data(
        (first, second_zip),
        output,
        Path(__file__).resolve().parents[1] / "schemas",
    )
    assert [campaign.id for campaign in index.campaigns] == [
        first_campaign.id,
        second_campaign.id,
    ]
    assert index.default_campaign_id == second_campaign.id
    trends = json.loads((output / "trends.json").read_text(encoding="utf-8"))
    assert [campaign["id"] for campaign in trends["campaigns"]] == [
        first_campaign.id,
        second_campaign.id,
    ]
    assert all("archive" not in campaign for campaign in trends["campaigns"])
    assert (output / "campaigns" / first_campaign.id / "manifest.json").is_file()
    assert (output / "campaigns" / second_campaign.id / "manifest.json").is_file()
    assert (output / "schemas" / "campaign-summary.schema.json").is_file()
    assert not (output / "dataset.json").exists()

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent = tuple(
            executor.map(
                lambda _: assemble_dashboard_data(
                    (first, second_zip),
                    output,
                    Path(__file__).resolve().parents[1] / "schemas",
                ),
                range(2),
            )
        )
    assert all(item.default_campaign_id == second_campaign.id for item in concurrent)
    assert (
        json.loads((output / "index.json").read_text(encoding="utf-8"))["default_campaign_id"]
        == second_campaign.id
    )

    unsafe_output = tmp_path / "unsafe-data"
    lock_target = tmp_path / "lock-target"
    lock_target.write_text("do not truncate", encoding="utf-8")
    unsafe_output.with_name(".unsafe-data.lock").symlink_to(lock_target)
    with pytest.raises(PublicationError, match="safely open"):
        assemble_dashboard_data(
            (first,),
            unsafe_output,
            Path(__file__).resolve().parents[1] / "schemas",
        )
    assert lock_target.read_text(encoding="utf-8") == "do not truncate"


def test_public_pages_contains_all_summaries_and_only_latest_detail(
    catalog: Catalog, tmp_path: Path
) -> None:
    first_campaign = _campaign(catalog)
    second_campaign = first_campaign.model_copy(
        update={
            "id": "20260102T000000Z-public-latest",
            "started_at": first_campaign.started_at + timedelta(days=1),
            "finished_at": first_campaign.finished_at + timedelta(days=1),
        }
    )
    first_manifest = validate_campaign_bundle(
        export_campaign_bundle(catalog, first_campaign, tmp_path / "first")
    )
    second_root = export_campaign_bundle(catalog, second_campaign, tmp_path / "second")
    second_manifest = validate_campaign_bundle(second_root)
    archive_path = write_campaign_archive(second_root, tmp_path / "latest.zip")

    def archive(campaign_id: str, *, sha256: str, size: int) -> ArchiveMetadata:
        asset = f"svtorture-campaign-{campaign_id}.zip"
        tag = f"campaign-{campaign_id}"
        return ArchiveMetadata(
            release_tag=tag,
            release_url=f"https://github.com/example/repo/releases/tag/{tag}",
            asset_name=asset,
            download_url=f"https://github.com/example/repo/releases/download/{tag}/{asset}",
            sha256=sha256,
            bytes=size,
        )

    summaries = (
        project_campaign_summary(
            first_manifest, archive(first_manifest.id, sha256="1" * 64, size=1)
        ),
        project_campaign_summary(
            second_manifest,
            archive(
                second_manifest.id,
                sha256=sha256_file(archive_path),
                size=archive_path.stat().st_size,
            ),
        ),
    )
    built_site = tmp_path / "built"
    built_site.mkdir()
    (built_site / "index.html").write_text("<html></html>", encoding="utf-8")
    output = tmp_path / "pages"
    report = assemble_public_pages(
        built_site,
        summaries,
        archive_path,
        output,
        Path(__file__).resolve().parents[1] / "schemas",
    )
    index = json.loads((output / "data" / "index.json").read_text(encoding="utf-8"))
    trends = json.loads((output / "data" / "trends.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in index["campaigns"]] == [second_manifest.id]
    assert trends == {
        "schema_version": 6,
        "kind": "campaign-trends",
        "campaigns": [summary.model_dump(mode="json", exclude_none=True) for summary in summaries],
    }
    assert not (output / "data" / "campaigns" / first_manifest.id).exists()
    assert report.total_bytes == sum(
        path.stat().st_size for path in output.rglob("*") if path.is_file()
    )
    assert report.campaign_bytes == (
        report.manifest_bytes + report.catalog_bytes + report.verdicts_bytes + report.evidence_bytes
    )
    with pytest.raises(PublicationError, match="limit is 1"):
        assemble_public_pages(
            built_site,
            summaries,
            archive_path,
            tmp_path / "too-large",
            Path(__file__).resolve().parents[1] / "schemas",
            size_limit=1,
        )


def test_summary_is_one_reusable_strict_projection(catalog: Catalog, tmp_path: Path) -> None:
    manifest = validate_campaign_bundle(
        export_campaign_bundle(catalog, _campaign(catalog), tmp_path)
    )
    local = project_campaign_summary(manifest)
    assert "archive" not in local.model_dump(mode="json", exclude_none=True)

    asset_name = f"svtorture-campaign-{manifest.id}.zip"
    archive = ArchiveMetadata(
        release_tag=f"campaign-{manifest.id}",
        release_url=f"https://github.com/example/svtorture/releases/tag/campaign-{manifest.id}",
        asset_name=asset_name,
        download_url=(
            f"https://github.com/example/svtorture/releases/download/"
            f"campaign-{manifest.id}/{asset_name}"
        ),
        sha256="0" * 64,
        bytes=123,
    )
    published = project_campaign_summary(manifest, archive)
    assert CampaignSummary.model_validate(published.model_dump(mode="json")) == published

    extra = published.model_dump(mode="json")
    extra["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CampaignSummary.model_validate(extra)


def test_dashboard_schema_snapshots_require_discriminants_and_reuse_summary_schema() -> None:
    root = Path(__file__).resolve().parents[1] / "schemas"
    trends = json.loads((root / "campaign-trends.schema.json").read_text(encoding="utf-8"))
    assert trends["required"][:2] == ["schema_version", "kind"]
    assert trends["properties"]["campaigns"]["items"] == {"$ref": "campaign-summary.schema.json"}
    summary = json.loads((root / "campaign-summary.schema.json").read_text(encoding="utf-8"))
    assert summary["$id"] == "campaign-summary.schema.json"
    assert summary["required"][:2] == ["schema_version", "kind"]
    archive = summary["$defs"]["ArchiveMetadata"]["properties"]
    assert archive["sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert archive["release_url"]["pattern"].startswith("^https://")

    manifest = json.loads((root / "campaign-manifest.schema.json").read_text(encoding="utf-8"))
    resource = manifest["$defs"]["DashboardResource"]["properties"]
    assert "pattern" in resource["href"]
    assert resource["sha256"]["pattern"] == "^[0-9a-f]{64}$"

    catalog = json.loads((root / "campaign-catalog.schema.json").read_text(encoding="utf-8"))
    source_links = catalog["$defs"]["DashboardCase"]["properties"]["source_links"]
    assert source_links["additionalProperties"]["pattern"].startswith("^(?:https://")
    assert catalog["properties"]["standard_sections"]["items"] == {
        "$ref": "#/$defs/StandardSection"
    }


def test_compact_verdict_and_evidence_packing_scale_to_ten_thousand_cases() -> None:
    verdicts = tuple(
        CampaignVerdict(
            tool_id=f"tool-{index}",
            profile_id="simulator",
            status="conforming",
            reason="expectation-met",
            evidence_mode="direct",
            summary="Synthetic deterministic scale result.",
        )
        for index in range(10)
    )
    cases = tuple(
        CampaignCaseVerdicts(
            case_id=f"case-{index:05d}",
            evidence_href=f"evidence/{index // 100:04d}.json",
            results=verdicts,
        )
        for index in range(10_000)
    )
    document = CampaignVerdicts(
        campaign_id="20260101T000000Z-scale-test",
        case_count=10_000,
        result_count=100_000,
        cases=cases,
    )
    data = canonical_json_bytes(document.model_dump(mode="json", exclude_none=True))
    assert len(data) < 30 * 1024 * 1024
    assert sha256_bytes(data) == sha256_bytes(data)

    case_ids = tuple(f"case-{index:05d}" for index in range(10_000))
    shards = pack_evidence_results(
        "20260101T000000Z-scale-test",
        case_ids,
        (
            DashboardEvidenceResult(
                schema_version=2,
                case_id=case_id,
                requirement_id="requirement",
                tool_id=f"tool-{tool_index}",
                profile_id="simulator",
                target_phase=Phase.SIMULATE,
                evidence_mode=EvidenceMode.NOT_OBSERVED,
                status=ResultStatus.UNSUPPORTED_CAPABILITY,
                reason=ReasonCode.UNSUPPORTED_PHASE,
                summary="Synthetic deterministic scale result.",
                evidence=EvidenceLevel.MANDATORY,
            )
            for case_id in case_ids
            for tool_index in range(10)
        ),
    )
    assert len(shards) == 100
    assert sum(len(shard.case_ids) for shard in shards) == 10_000
    assert sum(len(shard.results) for shard in shards) == 100_000
    assert all(len(shard.case_ids) <= 100 for shard in shards)
    assert all(
        len(canonical_json_bytes(shard.model_dump(mode="json"))) <= 8 * 1024 * 1024
        for shard in shards
    )

    normalized_results = tuple(
        NormalizedResult.model_validate(
            {**result.model_dump(mode="json"), "reproduction_command": None}
        )
        for shard in shards
        for result in shard.results
    )
    case_shards = {
        case_id: f"evidence/{index:04d}.json"
        for index, shard in enumerate(shards)
        for case_id in shard.case_ids
    }
    projected = project_verdicts(
        "20260101T000000Z-scale-test",
        case_ids,
        normalized_results,
        case_shards,
    )
    assert projected.case_count == 10_000
    assert projected.result_count == 100_000
