"""Dashboard dataset generation and strict public-export policy."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic import Field, StrictBool, StrictInt, ValidationError, field_validator

from svtorture.campaign import CampaignError, verify_campaign_against_catalog
from svtorture.catalog import Catalog, repository_identity
from svtorture.metric import compute_metric
from svtorture.models import (
    Campaign,
    Distribution,
    ExecutionBackend,
    MetricBreakdown,
    model_to_jsonable,
)


class PublicationError(RuntimeError):
    pass


class PublishedMetricPoint(MetricBreakdown):
    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    complete: StrictBool
    valid: StrictBool
    corpus_coverage: StrictInt = Field(ge=0)
    execution_coverage: StrictInt = Field(ge=0)
    conforming: StrictInt = Field(ge=0)
    nonconforming: StrictInt = Field(ge=0)
    inconclusive: StrictInt = Field(ge=0)
    unsupported: StrictInt = Field(ge=0)
    campaign_id: str
    timestamp: datetime
    tool_sha: str | None
    exact_tags: tuple[str, ...]
    nearest_tag: str | None
    reported_version: str | None
    image_digest: str | None
    repository_commit: str

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_is_an_iso_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            raise ValueError("metric timestamp must be an ISO string")
        return value


PRIVATE_PATTERN = re.compile(
    r"(?:/(?:home|Users|private|tmp|root)/|[A-Za-z]:\\\\|"
    r"SVTORTURE_TOOL_CONFIG|SNPSLMD_LICENSE_FILE|LM_LICENSE_FILE|"
    r"license[_-]?(?:file|server)|private[_-]?wrapper)",
    re.IGNORECASE,
)
SECRET_PATTERN = re.compile(
    r"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:password|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*"
    r"[\"']?[^\s\"']{8,})",
    re.IGNORECASE,
)
PUBLIC_IMAGE_RE = re.compile(r"^ghcr\.io/[^@\s]+@(sha256:[0-9a-f]{64})$")


def _require_pullable_public_image(reference: str) -> None:
    """Require anonymous registry access to the immutable public manifest."""

    try:
        result = subprocess.run(
            ["docker", "manifest", "inspect", reference],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PublicationError("cannot verify the public GHCR image manifest") from error
    if result.returncode != 0:
        raise PublicationError(f"image {reference!r} is not anonymously pullable from GHCR")


def _reject_private_material(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True)
    for pattern in (PRIVATE_PATTERN, SECRET_PATTERN):
        match = pattern.search(serialized)
        if match:
            raise PublicationError(f"public data contains private material: {match.group(0)!r}")


def validate_public_campaign(catalog: Catalog, campaign: Campaign) -> None:
    if campaign.trust.source != "github-actions":
        raise PublicationError("public export requires trusted GitHub Actions provenance")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise PublicationError("public export must execute inside GitHub Actions")
    trusted_environment = {
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "checkout_sha": os.environ.get("GITHUB_SHA"),
    }
    for field, actual in trusted_environment.items():
        if actual != getattr(campaign.trust, field):
            raise PublicationError(f"GitHub Actions {field} does not match campaign provenance")
    if campaign.repository.dirty or campaign.repository.commit == "unborn":
        raise PublicationError("public export requires a clean committed checkout")
    if campaign.trust.checkout_sha != campaign.repository.commit:
        raise PublicationError("trusted checkout SHA does not match the recorded corpus SHA")
    for tool in campaign.tools:
        definition = tool.definition
        if (
            not definition.publish
            or definition.distribution is not Distribution.OPEN_SOURCE
            or definition.execution is not ExecutionBackend.DOCKER
        ):
            raise PublicationError(
                f"tool {definition.id} is not publication eligible by metadata policy"
            )
    for expected_tool_id in campaign.expected_tool_ids:
        try:
            definition = catalog.tools.tool(expected_tool_id)
        except KeyError as error:
            raise PublicationError(
                f"campaign expects unknown public tool {expected_tool_id!r}"
            ) from error
        if (
            not definition.publish
            or definition.distribution is not Distribution.OPEN_SOURCE
            or definition.execution is not ExecutionBackend.DOCKER
        ):
            raise PublicationError(
                f"expected tool {definition.id} is not publication eligible by metadata policy"
            )
    try:
        verify_campaign_against_catalog(catalog, campaign)
    except CampaignError as error:
        raise PublicationError(str(error)) from error
    checkout = repository_identity(catalog.root)
    if checkout.dirty or checkout.commit != campaign.repository.commit:
        raise PublicationError(
            "public export must run from the clean checkout recorded by the campaign"
        )
    for tool in campaign.tools:
        image = tool.image
        if (
            image is None
            or image.digest is None
            or image.image_id is None
            or image.base_image_digest is None
        ):
            raise PublicationError(
                f"tool {tool.definition.id} lacks complete immutable image provenance"
            )
        match = PUBLIC_IMAGE_RE.fullmatch(image.reference)
        if match is None or match.group(1) != image.digest:
            raise PublicationError(
                f"tool {tool.definition.id} image is not a matching pullable GHCR digest"
            )
        _require_pullable_public_image(image.reference)
        if not image.base_image.endswith(f"@{image.base_image_digest}"):
            raise PublicationError(f"tool {tool.definition.id} base image digest is inconsistent")
        if image.platform != "linux/amd64":
            raise PublicationError(
                f"tool {tool.definition.id} has an unsupported public image platform"
            )
        if not tool.reported_version:
            raise PublicationError(f"tool {tool.definition.id} lacks a reported version")
    _reject_private_material(model_to_jsonable(campaign))


def _source_link(catalog: Catalog, campaign: Campaign, case_id: str, source: str) -> str:
    if campaign.trust.repository and campaign.repository.commit != "unborn":
        return (
            f"https://github.com/{campaign.trust.repository}/blob/"
            f"{campaign.repository.commit}/cases/{case_id}/{quote(source, safe='/')}"
        )
    try:
        text = (catalog.root / "cases" / case_id / source).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PublicationError(f"cannot embed local source {case_id}/{source}") from error
    return "data:text/plain;charset=utf-8," + quote(text, safe="")


def _corpus_coverage(catalog: Catalog) -> dict[str, Any]:
    index_path = catalog.anchor_index
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        sections = (
            ("chapter", index["clauses"]),
            ("annex", index["annexes"]),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise PublicationError(
            f"cannot read standard anchor index {index_path}: {error}"
        ) from error

    parts: list[dict[str, Any]] = []
    anchor_parts: dict[str, str] = {}
    for kind, entries in sections:
        for entry in entries:
            part_id = str(entry["id"])
            key = f"{kind}:{part_id}"
            anchors = frozenset(entry["anchors"])
            parts.append(
                {
                    "key": key,
                    "kind": kind,
                    "id": part_id,
                    "title": str(entry["title"]),
                    "anchors": anchors,
                }
            )
            for anchor in anchors:
                if anchor in anchor_parts:
                    raise PublicationError(f"standard anchor {anchor!r} appears more than once")
                anchor_parts[anchor] = key
    if index.get("anchor_count") != len(anchor_parts):
        raise PublicationError("standard anchor index has an inconsistent total anchor count")

    requirement_links = {
        (requirement.id, anchor)
        for requirement in catalog.inventory.requirements
        for anchor in requirement.anchors
    }
    requirement_anchors_by_part: defaultdict[str, set[str]] = defaultdict(set)
    requirement_links_by_part: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    for requirement_id, anchor in requirement_links:
        try:
            part_key = anchor_parts[anchor]
        except KeyError as error:
            raise PublicationError(f"requirement references unknown anchor {anchor!r}") from error
        requirement_anchors_by_part[part_key].add(anchor)
        requirement_links_by_part[part_key].add((requirement_id, anchor))

    requirements = {item.id: item for item in catalog.inventory.requirements}
    part_keys = {part["key"] for part in parts}
    requirements_by_part: defaultdict[str, set[str]] = defaultdict(set)
    for requirement in requirements.values():
        part_key = f"chapter:{requirement.chapter}"
        if part_key not in part_keys:
            raise PublicationError(
                f"requirement {requirement.id!r} belongs to unknown chapter {requirement.chapter}"
            )
        requirements_by_part[part_key].add(requirement.id)

    case_links = {
        (loaded.definition.id, requirement_id)
        for loaded in catalog.cases.values()
        for requirement_id in (
            loaded.definition.primary_requirement,
            *loaded.definition.related_requirements,
        )
    }
    case_requirements_by_part: defaultdict[str, set[str]] = defaultdict(set)
    case_links_by_part: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    for case_id, requirement_id in case_links:
        try:
            requirement = requirements[requirement_id]
        except KeyError as error:
            raise PublicationError(
                f"case references unknown requirement {requirement_id!r}"
            ) from error
        part_key = f"chapter:{requirement.chapter}"
        case_requirements_by_part[part_key].add(requirement_id)
        case_links_by_part[part_key].add((case_id, requirement_id))

    requirement_breakdown: list[dict[str, Any]] = []
    case_breakdown: list[dict[str, Any]] = []
    for part in parts:
        part_key = part["key"]
        covered_anchors = requirement_anchors_by_part[part_key]
        covered_requirements = case_requirements_by_part[part_key]
        common = {
            "kind": part["kind"],
            "id": part["id"],
            "title": part["title"],
        }
        requirement_breakdown.append(
            {
                **common,
                "coverage": {
                    "numerator": len(covered_anchors),
                    "denominator": len(part["anchors"]),
                },
                "density": {
                    "numerator": len(requirement_links_by_part[part_key]),
                    "denominator": len(covered_anchors),
                },
            }
        )
        case_breakdown.append(
            {
                **common,
                "coverage": {
                    "numerator": len(covered_requirements),
                    "denominator": len(requirements_by_part[part_key]),
                },
                "density": {
                    "numerator": len(case_links_by_part[part_key]),
                    "denominator": len(covered_requirements),
                },
            }
        )

    summary = model_to_jsonable(catalog.corpus_metrics())
    return {
        "requirements": {
            **summary["requirements"],
            "breakdown": requirement_breakdown,
        },
        "cases": {
            **summary["cases"],
            "breakdown": case_breakdown,
        },
    }


def build_dataset(
    catalog: Catalog,
    campaigns: Iterable[Campaign],
    *,
    visibility: str,
) -> dict[str, Any]:
    selected_campaigns = tuple(campaigns)
    if visibility not in {"local", "public"}:
        raise PublicationError("visibility must be local or public")
    for campaign in selected_campaigns:
        try:
            verify_campaign_against_catalog(catalog, campaign)
        except CampaignError as error:
            raise PublicationError(str(error)) from error
    if visibility == "public":
        for campaign in selected_campaigns:
            validate_public_campaign(catalog, campaign)
    latest = max(selected_campaigns, key=lambda item: item.finished_at, default=None)
    requirements = [
        model_to_jsonable(requirement)
        for requirement in sorted(
            catalog.inventory.requirements, key=lambda item: (item.chapter, item.clause)
        )
    ]
    cases = []
    for loaded in sorted(catalog.cases.values(), key=lambda item: item.definition.id):
        value = model_to_jsonable(loaded.definition)
        value["content_sha256"] = loaded.content_sha256
        if latest is not None:
            value["source_links"] = {
                source: _source_link(catalog, latest, loaded.definition.id, source)
                for source in loaded.definition.sources
            }
        cases.append(value)
    campaign_values = [model_to_jsonable(item) for item in selected_campaigns]
    metrics: list[dict[str, Any]] = []
    for campaign in selected_campaigns:
        for campaign_tool in campaign.tools:
            definition = campaign_tool.definition
            for profile_id in campaign_tool.profile_ids:
                profile = definition.profile(profile_id)
                metric = compute_metric(catalog, campaign, definition, profile)
                point = model_to_jsonable(metric)
                point.update(
                    {
                        "campaign_id": campaign.id,
                        "timestamp": campaign.finished_at.isoformat(),
                        "tool_sha": (
                            campaign_tool.selection.resolved_sha
                            if campaign_tool.selection
                            else None
                        ),
                        "exact_tags": (
                            list(campaign_tool.selection.exact_tags)
                            if campaign_tool.selection
                            else []
                        ),
                        "nearest_tag": (
                            campaign_tool.selection.nearest_tag if campaign_tool.selection else None
                        ),
                        "reported_version": campaign_tool.reported_version,
                        "image_digest": (
                            campaign_tool.image.digest if campaign_tool.image else None
                        ),
                        "repository_commit": campaign.repository.commit,
                    }
                )
                metrics.append(point)
    dataset = {
        "schema_version": 3,
        "generated_from": [item.id for item in selected_campaigns],
        "visibility": visibility,
        "corpus_coverage": _corpus_coverage(catalog),
        "requirements": requirements,
        "cases": cases,
        "campaigns": campaign_values,
        "metrics": metrics,
    }
    if visibility == "public":
        _reject_private_material(dataset)
    return dataset


def write_dataset(
    catalog: Catalog,
    campaigns: Iterable[Campaign],
    output: Path,
    *,
    visibility: str,
) -> Path:
    dataset = build_dataset(catalog, campaigns, visibility=visibility)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _validate_merge_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("schema_version") != 3:
        raise PublicationError("cannot merge incompatible dashboard datasets")
    required_sequences = ("generated_from", "requirements", "cases", "campaigns", "metrics")
    for key in required_sequences:
        if not isinstance(dataset.get(key), list):
            raise PublicationError(f"dashboard dataset has invalid {key}")
    if dataset.get("visibility") not in {"local", "public"}:
        raise PublicationError("dashboard dataset has invalid visibility")
    if not isinstance(dataset.get("corpus_coverage"), dict):
        raise PublicationError("dashboard dataset has invalid corpus_coverage")

    try:
        campaigns = [Campaign.model_validate(value) for value in dataset["campaigns"]]
    except ValidationError as error:
        raise PublicationError("dashboard dataset has an invalid campaign") from error
    campaign_ids = [campaign.id for campaign in campaigns]
    if len(campaign_ids) != len(set(campaign_ids)):
        raise PublicationError("dashboard dataset has duplicate campaigns")
    if dataset["visibility"] == "public" and any(
        campaign.trust.source != "github-actions" for campaign in campaigns
    ):
        raise PublicationError("public dashboard history contains a local campaign")
    generated_from = dataset["generated_from"]
    if not all(isinstance(value, str) for value in generated_from):
        raise PublicationError("dashboard dataset has invalid generated_from")
    if set(generated_from) != set(campaign_ids):
        raise PublicationError("dashboard dataset campaign provenance is incomplete")

    try:
        points = [PublishedMetricPoint.model_validate(value) for value in dataset["metrics"]]
    except ValidationError as error:
        raise PublicationError("dashboard dataset has an invalid metric point") from error
    campaign_profiles = {
        campaign.id: {
            (tool.definition.id, profile_id)
            for tool in campaign.tools
            for profile_id in tool.profile_ids
        }
        for campaign in campaigns
    }
    metric_ids: set[tuple[str, str, str]] = set()
    for point in points:
        identity = (point.campaign_id, point.tool_id, point.profile_id)
        if identity in metric_ids:
            raise PublicationError("dashboard dataset has duplicate metric points")
        metric_ids.add(identity)
        if point.campaign_id not in campaign_profiles:
            raise PublicationError("dashboard metric references an unknown campaign")
        if (point.tool_id, point.profile_id) not in campaign_profiles[point.campaign_id]:
            raise PublicationError("dashboard metric does not match its campaign")


def merge_datasets(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    _validate_merge_dataset(existing)
    _validate_merge_dataset(new)
    if existing["visibility"] != new["visibility"]:
        raise PublicationError("cannot merge dashboard datasets with different visibility")
    result = dict(new)
    for key, identity in (("campaigns", "id"), ("metrics", "campaign_id")):
        merged: dict[str, Any] = {}
        values = [*existing[key], *new[key]]
        for value in values:
            if key == "metrics":
                stable_id = f"{value[identity]}:{value['tool_id']}:{value['profile_id']}"
            else:
                stable_id = str(value[identity])
            previous = merged.get(stable_id)
            if previous is not None and previous != value:
                raise PublicationError(f"stable public identity {stable_id} changed")
            merged[stable_id] = value
        result[key] = list(merged.values())
    result["generated_from"] = sorted(
        {
            *existing["generated_from"],
            *new["generated_from"],
        }
    )
    return result


def publish_pages_tree(
    catalog: Catalog,
    campaigns: tuple[Campaign, ...],
    built_site: Path,
    pages_tree: Path,
) -> None:
    if not (built_site / "index.html").is_file():
        raise PublicationError("dashboard build does not contain index.html")
    new = build_dataset(catalog, campaigns, visibility="public")
    pages_tree.mkdir(parents=True, exist_ok=True)
    preserved_history = pages_tree / "history"
    preserved_data = pages_tree / "data" / "dataset.json"
    existing_dataset: dict[str, Any] | None = None
    if preserved_data.exists():
        try:
            existing_dataset = json.loads(preserved_data.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PublicationError("existing public dataset is corrupt") from error
    for source in built_site.iterdir():
        if source.name in {"data", "history"}:
            continue
        target = pages_tree / source.name
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    history = preserved_history
    campaign_history = history / "campaigns"
    campaign_history.mkdir(parents=True, exist_ok=True)
    for campaign in campaigns:
        path = campaign_history / f"{campaign.id}.json"
        serialized = json.dumps(model_to_jsonable(campaign), indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != serialized:
            raise PublicationError(f"campaign history collision for {campaign.id}")
        path.write_text(serialized, encoding="utf-8")
    if existing_dataset is not None:
        new = merge_datasets(existing_dataset, new)
    _reject_private_material(new)
    for campaign_value in new["campaigns"]:
        path = campaign_history / f"{campaign_value['id']}.json"
        if path.exists():
            try:
                existing_campaign = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise PublicationError(f"corrupt campaign history {path.name}") from error
            if existing_campaign != campaign_value:
                raise PublicationError(f"campaign history collision for {campaign_value['id']}")
        else:
            path.write_text(
                json.dumps(campaign_value, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    preserved_data.parent.mkdir(parents=True, exist_ok=True)
    preserved_data.write_text(json.dumps(new, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index = [
        {
            "id": campaign["id"],
            "finished_at": campaign["finished_at"],
            "repository_commit": campaign["repository"]["commit"],
            "tools": [tool["definition"]["id"] for tool in campaign["tools"]],
            "path": f"campaigns/{campaign['id']}.json",
        }
        for campaign in sorted(
            new["campaigns"],
            key=lambda value: (value["finished_at"], value["id"]),
        )
    ]
    history.mkdir(parents=True, exist_ok=True)
    (history / "index.json").write_text(
        json.dumps(
            {"schema_version": 1, "campaigns": index},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
