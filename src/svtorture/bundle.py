"""Build and validate deterministic portable dashboard campaign bundles."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import struct
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, ValidationError

from svtorture.campaign import (
    CampaignError,
    campaign_selection_hash,
    verify_campaign_against_catalog,
    verify_result_against_case,
)
from svtorture.catalog import Catalog, LoadedCase
from svtorture.dashboard_models import (
    ArchiveMetadata,
    CampaignCaseVerdicts,
    CampaignCatalog,
    CampaignEvidenceShard,
    CampaignManifest,
    CampaignResources,
    CampaignSummary,
    CampaignTrends,
    CampaignVerdict,
    CampaignVerdicts,
    CountedDashboardResource,
    DashboardCase,
    DashboardCaseIdentity,
    DashboardEvidenceResult,
    DashboardIndex,
    DashboardIndexCampaign,
    DashboardMetric,
    DashboardResource,
    DashboardSchemas,
    SummaryRepository,
)
from svtorture.hashing import canonical_json_bytes, hash_json, sha256_bytes
from svtorture.metric import compute_metric
from svtorture.models import (
    Campaign,
    CampaignTool,
    CaseDefinition,
    ManifestHashes,
    NormalizedResult,
    Requirement,
    RequirementInventory,
    StandardRevision,
    model_to_jsonable,
    standard_location_sort_key,
)
from svtorture.publish import PublicationError, _source_link, validate_public_campaign

DEFAULT_SHARD_CASES = 100
DEFAULT_SHARD_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024 - 1
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20_000
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_RESOURCE_BYTES = 128 * 1024 * 1024
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class PagesBuildReport:
    total_bytes: int
    frontend_bytes: int
    schema_bytes: int
    index_bytes: int
    trends_bytes: int
    campaign_bytes: int
    manifest_bytes: int
    catalog_bytes: int
    verdicts_bytes: int
    evidence_bytes: int
    largest_evidence_shard_bytes: int


@dataclass(frozen=True)
class _BundleCatalog:
    cases: dict[str, LoadedCase]
    _requirements: dict[str, Requirement]

    @property
    def requirements(self) -> dict[str, Requirement]:
        return self._requirements


@dataclass(frozen=True)
class _BundleCampaign:
    case_ids: tuple[str, ...]
    results: tuple[NormalizedResult, ...]
    expected_tool_ids: tuple[str, ...]
    missing_tool_ids: tuple[str, ...]
    hashes: ManifestHashes


def _model_bytes(model: Any) -> bytes:
    value = model.model_dump(mode="json", exclude_none=True)
    return canonical_json_bytes(value)


def _write_model(path: Path, model: Any) -> bytes:
    data = _model_bytes(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def _metric_with_provenance(metric: Any, campaign_tool: CampaignTool) -> DashboardMetric:
    selection = campaign_tool.selection
    image = campaign_tool.image
    return DashboardMetric(
        **model_to_jsonable(metric),
        tool_sha=selection.resolved_sha if selection else None,
        exact_tags=selection.exact_tags if selection else (),
        nearest_tag=selection.nearest_tag if selection else None,
        reported_version=campaign_tool.reported_version,
        image_digest=image.digest if image else None,
    )


def _dashboard_metric(
    catalog: Catalog, campaign: Campaign, tool_id: str, profile_id: str
) -> DashboardMetric:
    campaign_tool = next(tool for tool in campaign.tools if tool.definition.id == tool_id)
    profile = campaign_tool.definition.profile(profile_id)
    metric = compute_metric(catalog, campaign, campaign_tool.definition, profile)
    return _metric_with_provenance(metric, campaign_tool)


def _evidence_result(result: NormalizedResult) -> DashboardEvidenceResult:
    value = model_to_jsonable(result)
    value.pop("reproduction_command", None)
    return DashboardEvidenceResult.model_validate(value)


def _verdict(result: NormalizedResult) -> CampaignVerdict:
    return CampaignVerdict(
        tool_id=result.tool_id,
        profile_id=result.profile_id,
        status=result.status,
        reason=result.reason,
        evidence_mode=result.evidence_mode,
        summary=result.summary,
        known_issue=result.known_issue,
    )


def project_verdicts(
    campaign_id: str,
    case_ids: Iterable[str],
    results: Iterable[NormalizedResult],
    case_shards: dict[str, str],
) -> CampaignVerdicts:
    """Project compact case verdicts from one result-grid scan."""

    ordered_case_ids = tuple(sorted(case_ids))
    by_case: dict[str, list[CampaignVerdict]] = {case_id: [] for case_id in ordered_case_ids}
    for result in results:
        try:
            by_case[result.case_id].append(_verdict(result))
        except KeyError as error:
            raise PublicationError(f"verdict contains unknown case {result.case_id}") from error
    cases = tuple(
        CampaignCaseVerdicts(
            case_id=case_id,
            evidence_href=case_shards[case_id],
            results=tuple(
                sorted(by_case[case_id], key=lambda result: (result.tool_id, result.profile_id))
            ),
        )
        for case_id in ordered_case_ids
    )
    return CampaignVerdicts(
        campaign_id=campaign_id,
        case_count=len(cases),
        result_count=sum(len(case.results) for case in cases),
        cases=cases,
    )


def _make_shard(
    campaign_id: str, case_ids: list[str], by_case: dict[str, tuple[DashboardEvidenceResult, ...]]
) -> CampaignEvidenceShard:
    return CampaignEvidenceShard(
        campaign_id=campaign_id,
        case_ids=tuple(case_ids),
        results=tuple(result for case_id in case_ids for result in by_case[case_id]),
    )


def pack_evidence_results(
    campaign_id: str,
    case_ids: Iterable[str],
    results: Iterable[DashboardEvidenceResult],
    *,
    max_cases: int = DEFAULT_SHARD_CASES,
    target_bytes: int = DEFAULT_SHARD_BYTES,
) -> tuple[CampaignEvidenceShard, ...]:
    """Pack complete case groups in linear time with exact compact byte accounting."""

    if max_cases < 1 or target_bytes < 1:
        raise PublicationError("evidence shard limits must be positive")
    ordered_case_ids = tuple(sorted(case_ids))
    by_case_lists: dict[str, list[DashboardEvidenceResult]] = {
        case_id: [] for case_id in ordered_case_ids
    }
    for result in results:
        try:
            by_case_lists[result.case_id].append(result)
        except KeyError as error:
            raise PublicationError(f"evidence contains unknown case {result.case_id}") from error
    by_case = {
        case_id: tuple(sorted(case_results, key=lambda result: (result.tool_id, result.profile_id)))
        for case_id, case_results in by_case_lists.items()
    }
    base_bytes = len(
        canonical_json_bytes(
            {
                "campaign_id": campaign_id,
                "case_ids": [],
                "kind": "campaign-evidence",
                "results": [],
                "schema_version": 6,
            }
        )
    )
    case_bytes = {
        case_id: len(canonical_json_bytes(case_id))
        + sum(len(_model_bytes(result)) for result in by_case[case_id])
        + max(0, len(by_case[case_id]) - 1)
        for case_id in ordered_case_ids
    }
    result_counts = {case_id: len(by_case[case_id]) for case_id in ordered_case_ids}

    shards: list[CampaignEvidenceShard] = []
    pending: list[str] = []
    pending_bytes = base_bytes
    pending_results = 0
    for case_id in ordered_case_ids:
        added_bytes = case_bytes[case_id]
        if pending:
            added_bytes += 1
        result_count = result_counts[case_id]
        if pending_results and result_count:
            added_bytes += 1
        if pending and (len(pending) >= max_cases or pending_bytes + added_bytes > target_bytes):
            shards.append(_make_shard(campaign_id, pending, by_case))
            pending = []
            pending_bytes = base_bytes
            pending_results = 0
            added_bytes = case_bytes[case_id]
        pending.append(case_id)
        pending_bytes += added_bytes
        pending_results += result_count
        if pending_bytes > target_bytes:
            shards.append(_make_shard(campaign_id, pending, by_case))
            pending = []
            pending_bytes = base_bytes
            pending_results = 0
    if pending:
        shards.append(_make_shard(campaign_id, pending, by_case))
    return tuple(shards)


def pack_evidence(
    campaign: Campaign,
    *,
    max_cases: int = DEFAULT_SHARD_CASES,
    target_bytes: int = DEFAULT_SHARD_BYTES,
) -> tuple[CampaignEvidenceShard, ...]:
    """Project and pack one canonical campaign's complete evidence grid."""

    return pack_evidence_results(
        campaign.id,
        campaign.case_ids,
        (_evidence_result(result) for result in campaign.results),
        max_cases=max_cases,
        target_bytes=target_bytes,
    )


def _catalog(catalog: Catalog, campaign: Campaign) -> CampaignCatalog:
    requirements = tuple(
        sorted(
            catalog.inventory.requirements, key=lambda item: standard_location_sort_key(item.clause)
        )
    )
    cases = []
    for loaded in sorted(catalog.cases.values(), key=lambda item: item.definition.id):
        value = model_to_jsonable(loaded.definition)
        value.update(
            {
                "content_sha256": loaded.content_sha256,
                "definition_sha256": hash_json(model_to_jsonable(loaded.definition)),
                "source_links": {
                    source: _source_link(catalog, campaign, loaded.definition.id, source)
                    for source in loaded.definition.sources
                },
            }
        )
        cases.append(DashboardCase.model_validate(value))
    return CampaignCatalog(
        campaign_id=campaign.id,
        requirements=requirements,
        cases=tuple(cases),
        corpus_metrics=campaign.corpus_metrics,
    )


def _resource(href: str, data: bytes) -> DashboardResource:
    return DashboardResource(href=href, sha256=sha256_bytes(data), bytes=len(data))


def _counted_resource(
    href: str, data: bytes, *, case_count: int, result_count: int
) -> CountedDashboardResource:
    return CountedDashboardResource(
        href=href,
        sha256=sha256_bytes(data),
        bytes=len(data),
        case_count=case_count,
        result_count=result_count,
    )


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise PublicationError(f"campaign bundle path contains a symlink: {current}")


def _require_regular_tree(root: Path) -> None:
    _reject_symlink_components(root)
    if root.is_symlink() or not root.is_dir():
        raise PublicationError("campaign bundle root must be a regular directory")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise PublicationError(f"campaign bundle contains a symlink: {path}")
        mode = path.stat(follow_symlinks=False).st_mode
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise PublicationError(f"campaign bundle contains a non-regular object: {path}")


def _read_regular(path: Path, root: Path, maximum: int) -> bytes:
    try:
        path.resolve().relative_to(root.resolve())
        if path.is_symlink():
            raise PublicationError(f"campaign resource is a symlink: {path}")
        file_stat = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(file_stat.st_mode):
            raise PublicationError(f"campaign resource is not a regular file: {path}")
        if file_stat.st_size > maximum:
            raise PublicationError(f"campaign resource exceeds its size limit: {path}")
        with path.open("rb") as source:
            data = source.read(maximum + 1)
    except (OSError, ValueError) as error:
        raise PublicationError(f"cannot read campaign resource {path}") from error
    if len(data) > maximum:
        raise PublicationError(f"campaign resource exceeds its size limit: {path}")
    return data


def _tree_files(root: Path) -> dict[str, bytes]:
    _require_regular_tree(root)
    return {
        path.relative_to(root).as_posix(): _read_regular(path, root, MAX_RESOURCE_BYTES)
        for path in root.rglob("*")
        if path.is_file()
    }


def _same_tree(left: Path, right: Path) -> bool:
    return _tree_files(left) == _tree_files(right)


def export_campaign_bundle(
    catalog: Catalog,
    campaign: Campaign,
    output: Path,
    *,
    public: bool = False,
    max_shard_cases: int = DEFAULT_SHARD_CASES,
    target_shard_bytes: int = DEFAULT_SHARD_BYTES,
) -> Path:
    """Export one canonical campaign under ``output/campaigns/<id>``."""

    try:
        verify_campaign_against_catalog(catalog, campaign)
    except CampaignError as error:
        raise PublicationError(str(error)) from error
    if public:
        validate_public_campaign(catalog, campaign)

    output.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".bundle-", dir=output))
    temporary_campaign = temporary / "campaigns" / campaign.id
    try:
        catalog_model = _catalog(catalog, campaign)
        catalog_bytes = _write_model(temporary_campaign / "catalog.json", catalog_model)

        shards = pack_evidence(
            campaign,
            max_cases=max_shard_cases,
            target_bytes=target_shard_bytes,
        )
        shard_resources: list[CountedDashboardResource] = []
        case_shards: dict[str, str] = {}
        for index, shard in enumerate(shards):
            href = f"evidence/{index:04d}.json"
            data = _write_model(temporary_campaign / href, shard)
            shard_resources.append(
                _counted_resource(
                    href,
                    data,
                    case_count=len(shard.case_ids),
                    result_count=len(shard.results),
                )
            )
            case_shards.update(dict.fromkeys(shard.case_ids, href))

        verdicts = project_verdicts(
            campaign.id,
            campaign.case_ids,
            campaign.results,
            case_shards,
        )
        verdict_bytes = _write_model(temporary_campaign / "verdicts.json", verdicts)

        metrics = tuple(
            _dashboard_metric(catalog, campaign, tool.definition.id, profile_id)
            for tool in sorted(campaign.tools, key=lambda item: item.definition.id)
            for profile_id in sorted(tool.profile_ids)
        )
        manifest = CampaignManifest(
            id=campaign.id,
            started_at=campaign.started_at,
            finished_at=campaign.finished_at,
            repository=campaign.repository,
            platform=campaign.platform,
            selection_name=campaign.selection_name,
            cases=tuple(
                DashboardCaseIdentity(
                    id=identity.id,
                    content_sha256=identity.content_sha256,
                    definition_sha256=hash_json(
                        model_to_jsonable(catalog.cases[identity.id].definition)
                    ),
                )
                for identity in sorted(campaign.cases, key=lambda item: item.id)
            ),
            tools=tuple(sorted(campaign.tools, key=lambda item: item.definition.id)),
            expected_tool_ids=tuple(sorted(campaign.expected_tool_ids)),
            missing_tool_ids=tuple(sorted(campaign.missing_tool_ids)),
            hashes=campaign.hashes,
            corpus_metrics=campaign.corpus_metrics,
            metrics=metrics,
            complete=campaign.complete,
            trust=campaign.trust,
            resources=CampaignResources(
                catalog=_resource("catalog.json", catalog_bytes),
                verdicts=_counted_resource(
                    "verdicts.json",
                    verdict_bytes,
                    case_count=verdicts.case_count,
                    result_count=verdicts.result_count,
                ),
                evidence=tuple(shard_resources),
            ),
        )
        _write_model(temporary_campaign / "manifest.json", manifest)
        validate_campaign_bundle(temporary_campaign)

        destination = output / "campaigns" / campaign.id
        if destination.exists():
            if not _same_tree(temporary_campaign, destination):
                raise PublicationError(f"campaign bundle collision for {campaign.id}")
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary_campaign, destination)
        return destination
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _parse_model[ModelT: BaseModel](
    data: bytes,
    path: Path,
    model: type[ModelT],
) -> ModelT:
    try:
        value = json.loads(data)
        return model.model_validate(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise PublicationError(f"invalid dashboard resource {path}") from error


def _load_manifest(campaign_root: Path) -> CampaignManifest:
    path = campaign_root / "manifest.json"
    return _parse_model(
        _read_regular(path, campaign_root, MAX_MANIFEST_BYTES),
        path,
        CampaignManifest,
    )


def _verify_resource(campaign_root: Path, resource: DashboardResource) -> bytes:
    if resource.bytes > MAX_RESOURCE_BYTES:
        raise PublicationError(f"campaign resource exceeds its size limit: {resource.href}")
    path = campaign_root / resource.href
    data = _read_regular(path, campaign_root, MAX_RESOURCE_BYTES)
    if len(data) != resource.bytes or sha256_bytes(data) != resource.sha256:
        raise PublicationError(f"campaign resource integrity mismatch for {resource.href}")
    return data


def validate_campaign_bundle(campaign_root: Path) -> CampaignManifest:
    """Validate one unpacked ``campaigns/<id>`` directory and all references."""

    _require_regular_tree(campaign_root)
    manifest = _load_manifest(campaign_root)
    if campaign_root.name != manifest.id:
        raise PublicationError("campaign bundle directory does not match manifest id")
    resources = (
        manifest.resources.catalog,
        manifest.resources.verdicts,
        *manifest.resources.evidence,
    )
    if len(resources) > MAX_ARCHIVE_MEMBERS or sum(item.bytes for item in resources) > (
        MAX_ARCHIVE_UNCOMPRESSED_BYTES
    ):
        raise PublicationError("campaign bundle exceeds its aggregate resource limit")
    catalog_data = _verify_resource(campaign_root, manifest.resources.catalog)
    verdict_data = _verify_resource(campaign_root, manifest.resources.verdicts)
    catalog_path = campaign_root / manifest.resources.catalog.href
    verdict_path = campaign_root / manifest.resources.verdicts.href
    catalog = _parse_model(catalog_data, catalog_path, CampaignCatalog)
    verdicts = _parse_model(verdict_data, verdict_path, CampaignVerdicts)
    if catalog.campaign_id != manifest.id or verdicts.campaign_id != manifest.id:
        raise PublicationError("campaign resource identity mismatch")
    if tuple(case.case_id for case in verdicts.cases) != tuple(case.id for case in manifest.cases):
        raise PublicationError("verdict cases do not match manifest cases")
    if catalog.corpus_metrics != manifest.corpus_metrics:
        raise PublicationError("campaign catalog metrics do not match manifest")

    requirements = RequirementInventory(
        schema_version=3,
        authority=StandardRevision.IEEE_1800_2023,
        requirements=catalog.requirements,
    )
    if hash_json(model_to_jsonable(requirements)) != manifest.hashes.requirements:
        raise PublicationError("campaign requirement hash does not match catalog")
    catalog_cases = {case.id: case for case in catalog.cases}
    for catalog_case in catalog.cases:
        definition = catalog_case.model_dump(
            mode="json",
            exclude={"content_sha256", "definition_sha256", "source_links"},
            exclude_none=True,
        )
        if hash_json(definition) != catalog_case.definition_sha256:
            raise PublicationError("campaign case definition hash does not match catalog")
        for source, source_link in catalog_case.source_links.items():
            if manifest.trust.repository and manifest.repository.commit != "unborn":
                expected_link = (
                    f"https://github.com/{manifest.trust.repository}/blob/"
                    f"{manifest.repository.commit}/cases/{catalog_case.id}/"
                    f"{quote(source, safe='/')}"
                )
                if source_link != expected_link:
                    raise PublicationError("campaign source link does not match repository commit")
            elif not source_link.startswith("data:text/plain;charset=utf-8,"):
                raise PublicationError("local campaign source link must embed source data")

    selected_cases = []
    for case_identity in manifest.cases:
        selected_catalog_case = catalog_cases.get(case_identity.id)
        if (
            selected_catalog_case is None
            or selected_catalog_case.content_sha256 != case_identity.content_sha256
            or selected_catalog_case.definition_sha256 != case_identity.definition_sha256
        ):
            raise PublicationError("campaign case identity does not match catalog")
        selected_cases.append(
            {"id": case_identity.id, "content_sha256": case_identity.content_sha256}
        )
    if hash_json(selected_cases) != manifest.hashes.cases:
        raise PublicationError("campaign case hash does not match catalog")

    selection_hash = campaign_selection_hash(
        manifest.selection_name,
        (case.id for case in manifest.cases),
        manifest.tools,
        manifest.expected_tool_ids,
    )
    if selection_hash != manifest.hashes.selection:
        raise PublicationError("campaign selection hash does not match manifest")

    evidence_by_case: dict[str, tuple[DashboardEvidenceResult, ...]] = {}
    evidence_href_by_case: dict[str, str] = {}
    expected_files = {
        "manifest.json",
        manifest.resources.catalog.href,
        manifest.resources.verdicts.href,
    }
    for resource in manifest.resources.evidence:
        shard_data = _verify_resource(campaign_root, resource)
        shard_path = campaign_root / resource.href
        shard = _parse_model(shard_data, shard_path, CampaignEvidenceShard)
        if shard.campaign_id != manifest.id:
            raise PublicationError("evidence campaign identity mismatch")
        if (
            len(shard.case_ids) != resource.case_count
            or len(shard.results) != resource.result_count
        ):
            raise PublicationError("evidence resource counts do not match shard")
        for case_id in shard.case_ids:
            if case_id in evidence_by_case:
                raise PublicationError("campaign case occurs in more than one evidence shard")
            evidence_by_case[case_id] = tuple(
                result for result in shard.results if result.case_id == case_id
            )
            evidence_href_by_case[case_id] = resource.href
        expected_files.add(resource.href)

    if set(evidence_by_case) != {case.case_id for case in verdicts.cases}:
        raise PublicationError("verdict and evidence cases do not match")
    evidence_coordinates: set[tuple[str, str, str]] = set()
    for case_verdicts in verdicts.cases:
        if evidence_href_by_case[case_verdicts.case_id] != case_verdicts.evidence_href:
            raise PublicationError("verdict references the wrong evidence shard")
        actual_results = evidence_by_case[case_verdicts.case_id]
        for verdict in case_verdicts.results:
            matching = [
                result
                for result in actual_results
                if (result.tool_id, result.profile_id) == (verdict.tool_id, verdict.profile_id)
            ]
            if len(matching) != 1:
                raise PublicationError("verdict does not identify exactly one evidence result")
            result = matching[0]
            catalog_case = catalog_cases[case_verdicts.case_id]
            if (
                result.requirement_id != catalog_case.primary_requirement
                or result.target_phase != catalog_case.target_phase
                or result.evidence != catalog_case.evidence
            ):
                raise PublicationError("evidence result does not match the campaign catalog")
            coordinates = (case_verdicts.case_id, verdict.tool_id, verdict.profile_id)
            evidence_coordinates.add(coordinates)
            if (
                result.status,
                result.reason,
                result.evidence_mode,
                result.summary,
                result.known_issue,
            ) != (
                verdict.status,
                verdict.reason,
                verdict.evidence_mode,
                verdict.summary,
                verdict.known_issue,
            ):
                raise PublicationError("verdict does not match evidence result")
    all_coordinates = {
        (case_id, result.tool_id, result.profile_id)
        for case_id, results in evidence_by_case.items()
        for result in results
    }
    expected_coordinates = {
        (case.id, tool.definition.id, profile_id)
        for case in manifest.cases
        for tool in manifest.tools
        for profile_id in tool.profile_ids
    }
    if (
        evidence_coordinates != all_coordinates
        or all_coordinates != expected_coordinates
        or len(all_coordinates) != verdicts.result_count
    ):
        raise PublicationError("evidence result grid does not match manifest and verdicts")

    loaded_cases = {
        case.id: LoadedCase(
            definition=CaseDefinition.model_validate(
                case.model_dump(exclude={"content_sha256", "definition_sha256", "source_links"})
            ),
            directory=Path(".") / case.id,
            metadata_path=Path(".") / case.id / "case.toml",
            anchor_source=None,
            anchor_line=None,
            content_sha256=case.content_sha256,
        )
        for case in catalog.cases
    }
    normalized_results = tuple(
        NormalizedResult.model_validate(
            {**result.model_dump(mode="json"), "reproduction_command": None}
        )
        for results in evidence_by_case.values()
        for result in results
    )
    tools = {tool.definition.id: tool for tool in manifest.tools}
    try:
        for normalized_result in normalized_results:
            verify_result_against_case(
                loaded_cases[normalized_result.case_id],
                tools[normalized_result.tool_id],
                normalized_result,
            )
    except (CampaignError, KeyError) as error:
        raise PublicationError(f"campaign evidence judgment is invalid: {error}") from error

    metric_catalog = _BundleCatalog(
        cases=loaded_cases,
        _requirements={requirement.id: requirement for requirement in catalog.requirements},
    )
    metric_campaign = _BundleCampaign(
        case_ids=tuple(case.id for case in manifest.cases),
        results=normalized_results,
        expected_tool_ids=manifest.expected_tool_ids,
        missing_tool_ids=manifest.missing_tool_ids,
        hashes=manifest.hashes,
    )
    for recorded_metric in manifest.metrics:
        campaign_tool = tools[recorded_metric.tool_id]
        profile = campaign_tool.definition.profile(recorded_metric.profile_id)
        recomputed = _metric_with_provenance(
            compute_metric(metric_catalog, metric_campaign, campaign_tool.definition, profile),
            campaign_tool,
        )
        if recomputed != recorded_metric:
            raise PublicationError("campaign metric does not match catalog and evidence")

    actual_files = {
        path.relative_to(campaign_root).as_posix()
        for path in campaign_root.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise PublicationError("campaign bundle contains unexpected or missing files")
    return manifest


def project_campaign_summary(
    manifest: CampaignManifest,
    archive: ArchiveMetadata | None = None,
) -> CampaignSummary:
    """Project the only summary model used by local and public trends."""

    return CampaignSummary(
        id=manifest.id,
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
        complete=manifest.complete,
        repository=SummaryRepository(commit=manifest.repository.commit),
        trust=manifest.trust,
        hashes=manifest.hashes,
        corpus_metrics=manifest.corpus_metrics,
        tool_metrics=manifest.metrics,
        archive=archive,
    )


def _campaign_root(path: Path) -> Path:
    _reject_symlink_components(path)
    if (path / "manifest.json").is_file():
        return path
    campaigns = path / "campaigns"
    if campaigns.is_symlink():
        raise PublicationError("bundle campaigns directory must not be a symlink")
    candidates = (
        [candidate for candidate in campaigns.iterdir() if candidate.is_dir()]
        if campaigns.is_dir()
        else []
    )
    if len(candidates) != 1:
        raise PublicationError("bundle must contain exactly one campaign")
    campaign_root = candidates[0]
    if campaign_root.is_symlink():
        raise PublicationError("bundle campaign directory must not be a symlink")
    try:
        campaign_root.resolve().relative_to(path.resolve())
    except ValueError as error:
        raise PublicationError("campaign directory escapes its bundle root") from error
    return campaign_root


def write_campaign_archive(bundle: Path, output: Path) -> Path:
    """Write a reproducible ZIP containing only one portable campaign tree."""

    campaign_root = _campaign_root(bundle)
    manifest = validate_campaign_bundle(campaign_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    prefix = f"campaigns/{manifest.id}"
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for path in sorted(item for item in campaign_root.rglob("*") if item.is_file()):
                relative = path.relative_to(campaign_root).as_posix()
                info = zipfile.ZipInfo(f"{prefix}/{relative}", date_time=ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.create_system = 3
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def _materialize_bundle(bundle: Path, output: Path) -> Path:
    if bundle.is_file():
        return extract_campaign_archive(bundle, output)
    campaign_root = _campaign_root(bundle)
    manifest = validate_campaign_bundle(campaign_root)
    destination = output / "campaigns" / manifest.id
    if destination.exists():
        if not _same_tree(campaign_root, destination):
            raise PublicationError(f"campaign bundle collision for {manifest.id}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(campaign_root, destination, symlinks=False)
    return destination


def assemble_dashboard_data(
    bundles: Iterable[Path],
    output: Path,
    schema_directory: Path,
) -> DashboardIndex:
    """Assemble validated local bundles into one bounded dashboard data tree."""

    inputs = tuple(bundles)
    if not inputs:
        raise PublicationError("at least one campaign bundle is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".dashboard-data-", dir=output.parent))
    backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.backup-", dir=output.parent))
    backup.rmdir()
    try:
        manifests: list[CampaignManifest] = []
        seen: dict[str, Path] = {}
        for bundle in inputs:
            campaign_root = _materialize_bundle(bundle, temporary)
            manifest = validate_campaign_bundle(campaign_root)
            existing = seen.get(manifest.id)
            if existing is not None:
                if not _same_tree(existing, campaign_root):
                    raise PublicationError(f"campaign bundle collision for {manifest.id}")
                continue
            seen[manifest.id] = campaign_root
            manifests.append(manifest)
        manifests.sort(key=lambda manifest: (manifest.finished_at, manifest.id))
        latest = manifests[-1]
        trends = CampaignTrends(
            campaigns=tuple(project_campaign_summary(manifest) for manifest in manifests)
        )
        _write_model(temporary / "trends.json", trends)

        schema_names = {
            "summary": "campaign-summary.schema.json",
            "trends": "campaign-trends.schema.json",
            "campaign": "campaign-manifest.schema.json",
            "catalog": "campaign-catalog.schema.json",
            "verdicts": "campaign-verdicts.schema.json",
            "evidence": "campaign-evidence.schema.json",
        }
        schema_output = temporary / "schemas"
        schema_output.mkdir()
        for name in (*schema_names.values(), "dashboard-index.schema.json"):
            source = schema_directory / name
            if not source.is_file():
                raise PublicationError(f"dashboard schema is missing: {source}")
            shutil.copyfile(source, schema_output / name)
        index = DashboardIndex(
            default_campaign_id=latest.id,
            campaigns=tuple(
                DashboardIndexCampaign(
                    id=manifest.id,
                    manifest=f"campaigns/{manifest.id}/manifest.json",
                )
                for manifest in manifests
            ),
            trends="trends.json",
            schemas=DashboardSchemas(
                **{key: f"schemas/{value}" for key, value in schema_names.items()}
            ),
        )
        _write_model(temporary / "index.json", index)

        lock_path = output.with_name(f".{output.name}.lock")
        try:
            lock_fd = os.open(
                lock_path,
                os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                os.close(lock_fd)
                raise PublicationError("dashboard data lock must be a regular file")
        except OSError as error:
            raise PublicationError("cannot safely open the dashboard data lock") from error
        with os.fdopen(lock_fd, "r+", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            backup_exists = False
            if output.exists():
                if not output.is_dir():
                    raise PublicationError("dashboard data output must be a directory")
                os.replace(output, backup)
                backup_exists = True
            try:
                os.replace(temporary, output)
            except Exception:
                if backup_exists and not output.exists():
                    os.replace(backup, output)
                raise
            if backup_exists:
                shutil.rmtree(backup)
        return index
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def sha256_file(path: Path) -> str:
    """Hash a file without buffering an archive-sized payload."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def assemble_public_pages(
    built_site: Path,
    summaries: Iterable[CampaignSummary],
    latest_archive: Path,
    output: Path,
    schema_directory: Path,
    *,
    size_limit: int = 650 * 1024 * 1024,
) -> PagesBuildReport:
    """Build a clean latest-only Pages tree from immutable Release artifacts."""

    if not (built_site / "index.html").is_file():
        raise PublicationError("built dashboard site has no index.html")
    ordered = tuple(sorted(summaries, key=lambda item: (item.finished_at, item.id)))
    trends = CampaignTrends(campaigns=ordered)
    if not ordered or any(summary.archive is None for summary in ordered):
        raise PublicationError("public Pages history requires archived campaign summaries")
    latest = ordered[-1]
    assert latest.archive is not None
    archive_bytes = latest_archive.stat().st_size
    if archive_bytes != latest.archive.bytes or sha256_file(latest_archive) != (
        latest.archive.sha256
    ):
        raise PublicationError("latest campaign archive does not match its summary")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".public-pages-", dir=output.parent))
    site = temporary / "site"
    try:
        shutil.copytree(built_site, site)
        shutil.rmtree(site / "data", ignore_errors=True)
        index = assemble_dashboard_data((latest_archive,), site / "data", schema_directory)
        if index.default_campaign_id != latest.id or len(index.campaigns) != 1:
            raise PublicationError("latest campaign archive does not match public history")
        _write_model(site / "data" / "trends.json", trends)
        (site / ".data.lock").unlink(missing_ok=True)

        evidence_files = tuple(
            (site / "data" / "campaigns" / latest.id / "evidence").glob("*.json")
        )
        report = PagesBuildReport(
            total_bytes=_tree_size(site),
            frontend_bytes=sum(
                path.stat().st_size
                for path in site.rglob("*")
                if path.is_file() and "data" not in path.relative_to(site).parts
            ),
            schema_bytes=_tree_size(site / "data" / "schemas"),
            index_bytes=(site / "data" / "index.json").stat().st_size,
            trends_bytes=(site / "data" / "trends.json").stat().st_size,
            campaign_bytes=_tree_size(site / "data" / "campaigns" / latest.id),
            manifest_bytes=(site / "data" / "campaigns" / latest.id / "manifest.json")
            .stat()
            .st_size,
            catalog_bytes=(site / "data" / "campaigns" / latest.id / "catalog.json").stat().st_size,
            verdicts_bytes=(site / "data" / "campaigns" / latest.id / "verdicts.json")
            .stat()
            .st_size,
            evidence_bytes=sum(path.stat().st_size for path in evidence_files),
            largest_evidence_shard_bytes=max(
                (path.stat().st_size for path in evidence_files),
                default=0,
            ),
        )
        if report.total_bytes > size_limit:
            raise PublicationError(
                f"public Pages tree is {report.total_bytes} bytes; limit is {size_limit}"
            )
        if output.exists():
            if not output.is_dir() or output.is_symlink():
                raise PublicationError("public Pages output must be a regular directory")
            shutil.rmtree(output)
        os.replace(site, output)
        return report
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _zip_member_count(archive_path: Path) -> int:
    try:
        if archive_path.is_symlink():
            raise PublicationError("campaign archive must be a regular file")
        archive_stat = archive_path.stat(follow_symlinks=False)
        if not stat.S_ISREG(archive_stat.st_mode) or archive_stat.st_size > MAX_ARCHIVE_BYTES:
            raise PublicationError("campaign archive exceeds the compressed size limit")
        tail_size = min(archive_stat.st_size, 65_557)
        with archive_path.open("rb") as archive:
            archive.seek(-tail_size, os.SEEK_END)
            tail = archive.read(tail_size)
    except OSError as error:
        raise PublicationError("cannot read campaign archive") from error
    signature = b"PK\x05\x06"
    position = len(tail)
    while (position := tail.rfind(signature, 0, position)) >= 0:
        if position + 22 <= len(tail):
            fields = struct.unpack_from("<4s4H2LH", tail, position)
            disk, central_disk, disk_entries, total_entries = fields[1:5]
            comment_bytes = fields[-1]
            if position + 22 + comment_bytes == len(tail):
                if disk or central_disk or disk_entries != total_entries:
                    raise PublicationError("multi-disk campaign archives are not supported")
                if total_entries == 0xFFFF:
                    raise PublicationError("ZIP64 campaign member counts are not supported")
                return int(total_entries)
    raise PublicationError("campaign archive has no valid end record")


def extract_campaign_archive(archive_path: Path, output: Path) -> Path:
    """Safely extract and validate one Release bundle ZIP."""

    member_count = _zip_member_count(archive_path)
    if member_count == 0 or member_count > MAX_ARCHIVE_MEMBERS:
        raise PublicationError("campaign archive has an unsafe member count")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".extract-", dir=output.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(infos) != member_count or len(names) != len(set(names)):
                raise PublicationError("campaign archive has duplicate or inconsistent members")
            if sum(info.file_size for info in infos) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise PublicationError("campaign archive exceeds the uncompressed size limit")
            campaign_ids: set[str] = set()
            normalized_names: set[str] = set()
            for info in infos:
                path = PurePosixPath(info.filename)
                normalized_name = path.as_posix()
                mode = info.external_attr >> 16
                maximum = MAX_MANIFEST_BYTES if path.name == "manifest.json" else MAX_RESOURCE_BYTES
                if (
                    info.is_dir()
                    or info.file_size > maximum
                    or info.flag_bits & 0x1
                    or path.is_absolute()
                    or ".." in path.parts
                    or "\\" in info.filename
                    or info.filename != normalized_name
                    or normalized_name in normalized_names
                    or len(path.parts) < 3
                    or path.parts[0] != "campaigns"
                    or stat.S_ISLNK(mode)
                    or (mode and not stat.S_ISREG(mode))
                ):
                    raise PublicationError(f"unsafe campaign archive member {info.filename!r}")
                normalized_names.add(normalized_name)
                campaign_ids.add(path.parts[1])
                destination = temporary.joinpath(*path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
            if len(campaign_ids) != 1:
                raise PublicationError("campaign archive must contain exactly one campaign")
        campaign_root = temporary / "campaigns" / campaign_ids.pop()
        validate_campaign_bundle(campaign_root)
        destination = output / "campaigns" / campaign_root.name
        if destination.exists():
            if not _same_tree(campaign_root, destination):
                raise PublicationError(f"campaign bundle collision for {campaign_root.name}")
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(campaign_root, destination)
        return destination
    except (OSError, zipfile.BadZipFile) as error:
        raise PublicationError("cannot read campaign archive") from error
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
