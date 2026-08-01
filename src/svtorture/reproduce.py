"""Replay one recorded tool/case observation and report environmental differences."""

from __future__ import annotations

import json
import os
import platform
import shlex
import stat
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from svtorture.adapters.registry import adapter_for
from svtorture.bundle import (
    MAX_ARCHIVE_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_RESOURCE_BYTES,
    inspect_campaign_archive,
)
from svtorture.campaign import (
    CampaignError,
    campaign_selection_hash,
    load_campaign,
    load_campaign_location,
    load_runner_config,
    validate_plan_for_profile,
    verify_campaign_against_catalog,
    verify_result_against_case,
    wrapper_available,
)
from svtorture.catalog import Catalog, load_catalog, repository_identity
from svtorture.dashboard_models import (
    CampaignCatalog,
    CampaignEvidenceShard,
    CampaignManifest,
    CampaignVerdicts,
    DashboardCase,
    DashboardResource,
)
from svtorture.evaluator import evaluate
from svtorture.executor import execute_plan
from svtorture.hashing import hash_json, sha256_bytes
from svtorture.images import build_image, recipe_hash
from svtorture.models import (
    Campaign,
    CampaignTool,
    CaseDefinition,
    NormalizedResult,
    RequirementInventory,
    StandardRevision,
    model_to_jsonable,
)
from svtorture.publish import PublicationError


class ReproductionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReproductionReport:
    recorded: NormalizedResult
    replayed: NormalizedResult
    differences: tuple[str, ...]


@dataclass(frozen=True)
class ReplayContext:
    """The selected, verified subset of one portable dashboard campaign."""

    manifest: CampaignManifest
    case: DashboardCase
    tool: CampaignTool
    result: NormalizedResult

    @property
    def id(self) -> str:
        return self.manifest.id


ReplaySource = Campaign | ReplayContext
ReplayMetadata = Campaign | CampaignManifest
ResourceReader = Callable[[DashboardResource], bytes]


def _ensure_checkout(root: Path, campaign: ReplayMetadata) -> Path:
    current = repository_identity(root)
    if campaign.repository.dirty or campaign.repository.commit == "unborn":
        return root
    if current.commit == campaign.repository.commit:
        return root
    destination = root / ".svtorture" / "reproduce" / campaign.repository.commit
    if destination.exists():
        identity = repository_identity(destination)
        if identity.commit != campaign.repository.commit or identity.dirty:
            raise ReproductionError("existing replay worktree is not the recorded clean checkout")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "--detach",
            str(destination),
            campaign.repository.commit,
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ReproductionError(completed.stderr.strip() or "cannot create replay worktree")
    identity = repository_identity(destination)
    if identity.commit != campaign.repository.commit or identity.dirty:
        raise ReproductionError("created replay worktree is not the recorded clean checkout")
    return destination


def _ensure_image(checkout: Path, campaign_tool: CampaignTool) -> str:
    if campaign_tool.image is None:
        raise ReproductionError("recorded tool has no image identity")
    reference = campaign_tool.image.reference
    inspect = subprocess.run(
        ["docker", "image", "inspect", reference],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if inspect.returncode == 0:
        return reference
    pull = subprocess.run(
        ["docker", "pull", reference],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if pull.returncode == 0:
        return reference
    if campaign_tool.selection is None:
        raise ReproductionError("recorded image is unavailable and has no source selection")
    if recipe_hash(checkout, campaign_tool.definition) != campaign_tool.image.recipe_sha256:
        raise ReproductionError("recorded build recipe is not present in the replay checkout")
    rebuilt = build_image(
        checkout,
        campaign_tool.definition,
        campaign_tool.selection,
        base_image_reference=campaign_tool.image.base_image,
    )
    if rebuilt.base_image_digest != campaign_tool.image.base_image_digest:
        raise ReproductionError("rebuilt image used a different base image digest")
    if campaign_tool.image.image_id is None:
        raise ReproductionError("recorded campaign lacks an exact image ID")
    if rebuilt.image_id != campaign_tool.image.image_id:
        raise ReproductionError("rebuilt image ID differs from the recorded image")
    return rebuilt.reference


def _parse_model[ModelT: BaseModel](data: bytes, model: type[ModelT], label: str) -> ModelT:
    try:
        return model.model_validate_json(data)
    except ValidationError as error:
        raise ReproductionError(f"invalid {label}: {error}") from error


def _verified_resource(reader: ResourceReader, resource: DashboardResource) -> bytes:
    if resource.bytes > MAX_RESOURCE_BYTES:
        raise ReproductionError(f"replay resource {resource.href} exceeds the size limit")
    data = reader(resource)
    if len(data) != resource.bytes or sha256_bytes(data) != resource.sha256:
        raise ReproductionError(f"replay resource integrity mismatch for {resource.href}")
    return data


def _build_replay_context(
    manifest_bytes: bytes,
    reader: ResourceReader,
    *,
    source_location: str,
    tool_id: str,
    profile_id: str,
    case_id: str,
    expected_campaign_id: str | None = None,
) -> ReplayContext:
    manifest = _parse_model(manifest_bytes, CampaignManifest, "campaign manifest")
    if expected_campaign_id is not None and manifest.id != expected_campaign_id:
        raise ReproductionError("campaign archive directory does not match its manifest")
    catalog = _parse_model(
        _verified_resource(reader, manifest.resources.catalog),
        CampaignCatalog,
        "campaign catalog",
    )
    verdicts = _parse_model(
        _verified_resource(reader, manifest.resources.verdicts),
        CampaignVerdicts,
        "campaign verdicts",
    )
    if catalog.campaign_id != manifest.id or verdicts.campaign_id != manifest.id:
        raise ReproductionError("replay campaign resource identity mismatch")
    if (
        verdicts.case_count != manifest.resources.verdicts.case_count
        or verdicts.result_count != manifest.resources.verdicts.result_count
    ):
        raise ReproductionError("replay verdict counts do not match manifest")
    manifest_case_ids = {item.id for item in manifest.cases}
    if {item.case_id for item in verdicts.cases} != manifest_case_ids:
        raise ReproductionError("replay case resources do not match manifest")
    catalog_cases = {item.id: item for item in catalog.cases}
    selected_cases: list[dict[str, str]] = []
    for item_identity in manifest.cases:
        catalog_case = catalog_cases.get(item_identity.id)
        if catalog_case is None:
            raise ReproductionError("replay case identity does not match catalog")
        definition = catalog_case.model_dump(
            mode="json",
            exclude={"content_sha256", "definition_sha256", "source_links"},
            exclude_none=True,
        )
        if (
            catalog_case.content_sha256 != item_identity.content_sha256
            or catalog_case.definition_sha256 != item_identity.definition_sha256
            or hash_json(definition) != item_identity.definition_sha256
        ):
            raise ReproductionError("replay case identity does not match catalog")
        for source, link in catalog_case.source_links.items():
            if manifest.trust.repository and manifest.repository.commit != "unborn":
                expected = (
                    f"https://github.com/{manifest.trust.repository}/blob/"
                    f"{manifest.repository.commit}/cases/{item_identity.id}/"
                    f"{urllib.parse.quote(source, safe='/')}"
                )
                if link != expected:
                    raise ReproductionError("replay source link does not match repository commit")
            elif not link.startswith("data:text/plain;charset=utf-8,"):
                raise ReproductionError("local replay source link must embed source data")
        selected_cases.append(
            {"id": item_identity.id, "content_sha256": item_identity.content_sha256}
        )
    if hash_json(selected_cases) != manifest.hashes.cases:
        raise ReproductionError("replay case hash does not match catalog")
    requirements = RequirementInventory(
        schema_version=3,
        authority=StandardRevision.IEEE_1800_2023,
        requirements=catalog.requirements,
    )
    if hash_json(model_to_jsonable(requirements)) != manifest.hashes.requirements:
        raise ReproductionError("replay requirement hash does not match catalog")
    if catalog.corpus_metrics != manifest.corpus_metrics:
        raise ReproductionError("replay corpus metrics do not match manifest")
    if (
        campaign_selection_hash(
            manifest.selection_name,
            (case.id for case in manifest.cases),
            manifest.tools,
            manifest.expected_tool_ids,
        )
        != manifest.hashes.selection
    ):
        raise ReproductionError("replay selection hash does not match manifest")

    case = next((item for item in catalog.cases if item.id == case_id), None)
    identity = next((item for item in manifest.cases if item.id == case_id), None)
    if case is None or identity is None:
        raise ReproductionError("recorded case identity was not found")
    definition = case.model_dump(
        mode="json",
        exclude={"content_sha256", "definition_sha256", "source_links"},
        exclude_none=True,
    )
    if (
        case.content_sha256 != identity.content_sha256
        or case.definition_sha256 != identity.definition_sha256
        or hash_json(definition) != case.definition_sha256
    ):
        raise ReproductionError("replay case identity does not match catalog")

    case_verdicts = next((item for item in verdicts.cases if item.case_id == case_id), None)
    if case_verdicts is None:
        raise ReproductionError("recorded case verdict was not found")
    evidence_resource = next(
        (item for item in manifest.resources.evidence if item.href == case_verdicts.evidence_href),
        None,
    )
    if evidence_resource is None:
        raise ReproductionError("recorded case references unknown evidence")
    shard = _parse_model(
        _verified_resource(reader, evidence_resource),
        CampaignEvidenceShard,
        "campaign evidence",
    )
    if (
        shard.campaign_id != manifest.id
        or case_id not in shard.case_ids
        or len(shard.case_ids) != evidence_resource.case_count
        or len(shard.results) != evidence_resource.result_count
    ):
        raise ReproductionError("replay evidence identity or counts mismatch")
    evidence = next(
        (
            item
            for item in shard.results
            if item.case_id == case_id and item.tool_id == tool_id and item.profile_id == profile_id
        ),
        None,
    )
    verdict = next(
        (
            item
            for item in case_verdicts.results
            if item.tool_id == tool_id and item.profile_id == profile_id
        ),
        None,
    )
    if evidence is None or verdict is None:
        raise ReproductionError("recorded result was not found")
    if (
        evidence.status,
        evidence.reason,
        evidence.evidence_mode,
        evidence.summary,
        evidence.known_issue,
    ) != (
        verdict.status,
        verdict.reason,
        verdict.evidence_mode,
        verdict.summary,
        verdict.known_issue,
    ):
        raise ReproductionError("replay verdict does not match evidence")
    reproduction_command = " ".join(
        (
            "just",
            "reproduce",
            shlex.quote(source_location),
            shlex.quote(tool_id),
            shlex.quote(profile_id),
            shlex.quote(case_id),
        )
    )
    try:
        result = NormalizedResult.model_validate(
            {
                **evidence.model_dump(mode="json"),
                "reproduction_command": reproduction_command,
            }
        )
    except ValidationError as error:
        raise ReproductionError(f"invalid replay result: {error}") from error
    if (
        result.requirement_id != case.primary_requirement
        or result.target_phase != case.target_phase
        or result.evidence != case.evidence
    ):
        raise ReproductionError("replay evidence does not match case definition")
    tool = next((item for item in manifest.tools if item.definition.id == tool_id), None)
    if tool is None or profile_id not in tool.profile_ids:
        raise ReproductionError("recorded tool/profile identity was not found")
    return ReplayContext(manifest=manifest, case=case, tool=tool, result=result)


def _read_local_resource(root: Path, resource: DashboardResource) -> bytes:
    path = root / resource.href
    descriptor = -1
    try:
        path.resolve().relative_to(root.resolve())
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > resource.bytes:
            raise ReproductionError(f"invalid replay resource file: {resource.href}")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            return source.read(resource.bytes + 1)
    except (OSError, ValueError) as error:
        raise ReproductionError(f"cannot read replay resource {resource.href}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _download_https(url: str, maximum: int) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ReproductionError("remote replay resources require credential-free HTTPS URLs")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "svtorture/0.1 campaign-reproduction"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or final.username or final.password:
                raise ReproductionError("remote replay resource redirected outside HTTPS")
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > maximum:
                raise ReproductionError("remote replay resource exceeds its size limit")
            payload = response.read(maximum + 1)
            final_url = response.geturl()
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ReproductionError(f"cannot download remote replay resource: {error}") from error
    if len(payload) > maximum:
        raise ReproductionError("remote replay resource exceeds its size limit")
    return payload, final_url


def _download_https_archive(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ReproductionError("remote campaign archives require credential-free HTTPS URLs")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "svtorture/0.1 campaign-reproduction"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or final.username or final.password:
                raise ReproductionError("remote campaign archive redirected outside HTTPS")
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > MAX_ARCHIVE_BYTES:
                raise ReproductionError("remote campaign archive exceeds GitHub's size limit")
            total = 0
            with destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ReproductionError(
                            "remote campaign archive exceeds GitHub's size limit"
                        )
                    output.write(chunk)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ReproductionError(f"cannot download remote campaign archive: {error}") from error


def _fully_unquote(value: str) -> str:
    decoded = value
    for _ in range(len(value) + 1):
        next_value = urllib.parse.unquote(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    raise ReproductionError("remote replay path has excessive encoding")


def _remote_resource_url(owner: str, href: str) -> str:
    decoded = _fully_unquote(href)
    parts = decoded.split("/")
    if (
        not decoded
        or decoded.startswith("/")
        or "\\" in decoded
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ReproductionError(f"unsafe remote replay resource path {href!r}")
    resolved = urllib.parse.urljoin(owner, href)
    owner_url = urllib.parse.urlparse(owner)
    resolved_url = urllib.parse.urlparse(resolved)
    owner_directory = _fully_unquote(owner_url.path.rsplit("/", 1)[0] + "/")
    resolved_path = _fully_unquote(resolved_url.path)
    if (
        resolved_url.scheme != "https"
        or resolved_url.netloc != owner_url.netloc
        or not resolved_path.startswith(owner_directory)
        or ".." in resolved_path[len(owner_directory) :].split("/")
        or "\\" in resolved_path
    ):
        raise ReproductionError(f"remote replay resource escapes its manifest: {href!r}")
    return resolved


def _load_remote_context(
    location: str,
    *,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> ReplaySource:
    manifest_bytes, manifest_url = _download_https(location, MAX_MANIFEST_BYTES)
    try:
        value = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReproductionError("remote replay manifest is invalid JSON") from error
    if not isinstance(value, dict) or value.get("kind") != "campaign-manifest":
        try:
            return load_campaign_location(location)
        except CampaignError as error:
            raise ReproductionError(str(error)) from error

    def read(resource: DashboardResource) -> bytes:
        url = _remote_resource_url(manifest_url, resource.href)
        payload, final_url = _download_https(url, min(resource.bytes, MAX_RESOURCE_BYTES))
        expected_url = urllib.parse.urlparse(url)
        final = urllib.parse.urlparse(final_url)
        owner_directory = _fully_unquote(
            urllib.parse.urlparse(manifest_url).path.rsplit("/", 1)[0] + "/"
        )
        final_path = _fully_unquote(final.path)
        if (
            final.netloc != expected_url.netloc
            or not final_path.startswith(owner_directory)
            or ".." in final_path[len(owner_directory) :].split("/")
            or "\\" in final_path
        ):
            raise ReproductionError("remote replay resource redirected outside its manifest")
        return payload

    return _build_replay_context(
        manifest_bytes,
        read,
        source_location=location,
        tool_id=tool_id,
        profile_id=profile_id,
        case_id=case_id,
    )


def _load_archive_context(
    path: Path,
    *,
    source_location: str,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> ReplayContext:
    try:
        campaign_id, names = inspect_campaign_archive(path)
    except PublicationError as error:
        raise ReproductionError(str(error)) from error
    prefix = f"campaigns/{campaign_id}/"
    manifest_name = f"{prefix}manifest.json"
    if manifest_name not in names:
        raise ReproductionError("campaign archive has no manifest")
    name_set = set(names)
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open(manifest_name) as source:
                manifest_bytes = source.read(MAX_MANIFEST_BYTES + 1)
            if len(manifest_bytes) > MAX_MANIFEST_BYTES:
                raise ReproductionError("campaign archive manifest exceeds the size limit")

            def read(resource: DashboardResource) -> bytes:
                name = f"{prefix}{resource.href}"
                if name not in name_set:
                    raise ReproductionError(f"campaign archive lacks {resource.href}")
                with archive.open(name) as source:
                    return source.read(min(resource.bytes, MAX_RESOURCE_BYTES) + 1)

            return _build_replay_context(
                manifest_bytes,
                read,
                source_location=source_location,
                tool_id=tool_id,
                profile_id=profile_id,
                case_id=case_id,
                expected_campaign_id=campaign_id,
            )
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise ReproductionError(f"cannot read replay campaign archive: {error}") from error


def load_replay_location(
    location: str,
    *,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> ReplaySource:
    """Load a canonical campaign or one selected v6 replay context."""

    parsed = urllib.parse.urlparse(location)
    if parsed.scheme:
        if parsed.path.lower().endswith(".zip"):
            with tempfile.TemporaryDirectory(prefix="svtorture-replay-") as temporary:
                archive = Path(temporary) / "campaign.zip"
                _download_https_archive(location, archive)
                return _load_archive_context(
                    archive,
                    source_location=location,
                    tool_id=tool_id,
                    profile_id=profile_id,
                    case_id=case_id,
                )
        return _load_remote_context(
            location,
            tool_id=tool_id,
            profile_id=profile_id,
            case_id=case_id,
        )
    path = Path(location)
    if path.is_dir():
        if (path / "campaign.json").is_file():
            return load_campaign(path)
        if (path / "manifest.json").is_file():
            path = path / "manifest.json"
        elif (path / "campaigns").is_dir():
            candidates = tuple((path / "campaigns").glob("*/manifest.json"))
            if len(candidates) != 1:
                raise ReproductionError("replay bundle directory must contain one campaign")
            path = candidates[0]
    if path.suffix.lower() == ".zip" or zipfile.is_zipfile(path):
        return _load_archive_context(
            path,
            source_location=location,
            tool_id=tool_id,
            profile_id=profile_id,
            case_id=case_id,
        )
    if path.name == "manifest.json":
        try:
            with path.open("rb") as source:
                manifest_bytes = source.read(MAX_MANIFEST_BYTES + 1)
        except OSError as error:
            raise ReproductionError(f"cannot read replay manifest: {error}") from error
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise ReproductionError("replay manifest exceeds its size limit")
        return _build_replay_context(
            manifest_bytes,
            lambda resource: _read_local_resource(path.parent, resource),
            source_location=location,
            tool_id=tool_id,
            profile_id=profile_id,
            case_id=case_id,
        )
    return load_campaign(path)


def _select_context(
    catalog: Catalog,
    source: ReplaySource,
    *,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> tuple[ReplayMetadata, CampaignTool, NormalizedResult]:
    if isinstance(source, Campaign):
        try:
            verify_campaign_against_catalog(catalog, source)
        except CampaignError as error:
            raise ReproductionError(str(error)) from error
        recorded = next(
            (
                item
                for item in source.results
                if item.tool_id == tool_id
                and item.profile_id == profile_id
                and item.case_id == case_id
            ),
            None,
        )
        campaign_tool = next(
            (item for item in source.tools if item.definition.id == tool_id),
            None,
        )
        metadata: ReplayMetadata = source
    else:
        manifest = source.manifest
        try:
            selected = tuple(catalog.cases[item.id] for item in manifest.cases)
        except KeyError as error:
            raise ReproductionError("current catalog lacks a recorded case") from error
        if catalog.requirement_manifest_hash() != manifest.hashes.requirements:
            raise ReproductionError("current requirements do not match replay manifest")
        if catalog.case_manifest_hash(selected) != manifest.hashes.cases:
            raise ReproductionError("current cases do not match replay manifest")
        if catalog.corpus_metrics() != manifest.corpus_metrics:
            raise ReproductionError("current corpus metrics do not match replay manifest")
        current_case = catalog.cases.get(case_id)
        if current_case is None or current_case.content_sha256 != source.case.content_sha256:
            raise ReproductionError("current case does not match replay context")
        if current_case.definition != CaseDefinition.model_validate(
            source.case.model_dump(exclude={"content_sha256", "definition_sha256", "source_links"})
        ):
            raise ReproductionError("current case definition does not match replay context")
        try:
            registered = catalog.tools.tool(tool_id)
        except KeyError as error:
            raise ReproductionError("current catalog lacks the recorded tool") from error
        if registered != source.tool.definition:
            raise ReproductionError("current tool definition does not match replay context")
        try:
            verify_result_against_case(current_case, source.tool, source.result)
        except CampaignError as error:
            raise ReproductionError(str(error)) from error
        recorded = source.result
        campaign_tool = source.tool
        metadata = manifest
    if recorded is None:
        raise ReproductionError("recorded result was not found")
    if campaign_tool is None:
        raise ReproductionError("recorded tool identity was not found")
    return metadata, campaign_tool, recorded


def reproduce_case(
    root: Path,
    source: ReplaySource,
    *,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> ReproductionReport:
    metadata: ReplayMetadata = source if isinstance(source, Campaign) else source.manifest
    checkout = _ensure_checkout(root, metadata)
    anchor_index = root / "standards" / "ieee-1800-2023-anchors.json"
    catalog: Catalog = load_catalog(checkout, anchor_index=anchor_index)
    metadata, campaign_tool, recorded = _select_context(
        catalog,
        source,
        tool_id=tool_id,
        profile_id=profile_id,
        case_id=case_id,
    )
    profile = campaign_tool.definition.profile(profile_id)
    loaded = catalog.cases[case_id]
    adapter = adapter_for(
        campaign_tool.definition.adapter,
        diagnostic_rules=campaign_tool.definition.diagnostic_rules,
    )
    wrapper = None
    image = None
    if campaign_tool.definition.execution.value == "docker":
        image = _ensure_image(checkout, campaign_tool)
    else:
        wrapper = load_runner_config(root, campaign_tool.definition)
        if not wrapper_available(wrapper):
            raise ReproductionError("the required local runner is unavailable")
    plan = adapter.build_plan(
        loaded,
        campaign_tool.definition,
        profile,
        image=image,
        wrapper=wrapper.command[0] if wrapper else None,
    )
    try:
        validate_plan_for_profile(
            plan,
            loaded,
            campaign_tool.definition,
            profile,
            image=image,
            wrapper=wrapper.command[0] if wrapper else None,
        )
    except ValueError as error:
        raise ReproductionError(f"invalid replay execution plan: {error}") from error
    observations = execute_plan(
        plan,
        loaded,
        adapter,
        checkout / ".svtorture" / "reproduce-work" / metadata.id / tool_id / profile_id / case_id,
        wrapper=wrapper,
    )
    replayed = evaluate(loaded, tool_id, profile_id, observations)
    differences: list[str] = []
    current_repository = repository_identity(root)
    if not metadata.repository.dirty and metadata.repository.commit != "unborn":
        if current_repository.commit != metadata.repository.commit:
            differences.append(
                "framework checkout: "
                f"recorded {metadata.repository.commit!r}, current "
                f"{current_repository.commit!r}"
            )
        if current_repository.dirty:
            differences.append("framework checkout: current worktree is dirty")
    current_platform = f"{platform.system()} {platform.machine()}"
    if current_platform != metadata.platform:
        differences.append(
            f"platform: recorded {metadata.platform!r}, current {current_platform!r}"
        )
    if replayed.status != recorded.status:
        differences.append(
            f"status: recorded {recorded.status.value}, replayed {replayed.status.value}"
        )
    if replayed.reason != recorded.reason:
        differences.append(
            f"reason: recorded {recorded.reason.value}, replayed {replayed.reason.value}"
        )
    if replayed.target_phase != recorded.target_phase:
        differences.append(
            "target phase: "
            f"recorded {recorded.target_phase.value}, replayed {replayed.target_phase.value}"
        )
    if replayed.evidence_mode != recorded.evidence_mode:
        differences.append(
            "evidence mode: "
            f"recorded {recorded.evidence_mode.value}, "
            f"replayed {replayed.evidence_mode.value}"
        )
    recorded_phases = tuple(
        (item.stage_id, item.kind.value, item.attempted_through_phase.value)
        for item in recorded.observations
    )
    replayed_phases = tuple(
        (item.stage_id, item.kind.value, item.attempted_through_phase.value)
        for item in replayed.observations
    )
    if replayed_phases != recorded_phases:
        differences.append(
            f"phase provenance: recorded {recorded_phases!r}, replayed {replayed_phases!r}"
        )
    return ReproductionReport(
        recorded=recorded,
        replayed=replayed,
        differences=tuple(differences),
    )
