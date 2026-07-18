"""Dashboard dataset generation and strict public-export policy."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from svtorture.campaign import CampaignError, verify_campaign_against_catalog
from svtorture.catalog import Catalog, repository_identity
from svtorture.metric import compute_metric
from svtorture.models import (
    Campaign,
    Distribution,
    ExecutionBackend,
    model_to_jsonable,
)


class PublicationError(RuntimeError):
    pass


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
        "schema_version": 1,
        "generated_from": [item.id for item in selected_campaigns],
        "visibility": visibility,
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


def merge_datasets(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if existing.get("schema_version") != 1 or new.get("schema_version") != 1:
        raise PublicationError("cannot merge incompatible dashboard datasets")
    result = dict(new)
    for key, identity in (("campaigns", "id"), ("metrics", "campaign_id")):
        merged: dict[str, Any] = {}
        values = [*existing.get(key, []), *new.get(key, [])]
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
            *existing.get("generated_from", []),
            *new.get("generated_from", []),
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
