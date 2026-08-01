"""Strict trust policy for public campaign bundle publication."""

from __future__ import annotations

import json
import os
import re
import subprocess
from urllib.parse import quote

from svtorture.campaign import CampaignError, verify_campaign_against_catalog
from svtorture.catalog import Catalog, repository_identity
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
    r"SNPSLMD_LICENSE_FILE|LM_LICENSE_FILE|license[_-]?(?:file|server))",
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


def _validate_offline_public_campaign(campaign: Campaign) -> None:
    if campaign.trust.source != "github-actions":
        raise PublicationError("public export requires trusted GitHub Actions provenance")
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
        image = tool.image
        if (
            image is None
            or image.digest is None
            or image.image_id is None
            or image.base_image_digest is None
        ):
            raise PublicationError(
                f"tool {definition.id} lacks complete immutable image provenance"
            )
        match = PUBLIC_IMAGE_RE.fullmatch(image.reference)
        if match is None or match.group(1) != image.digest:
            raise PublicationError(
                f"tool {definition.id} image is not a matching pullable GHCR digest"
            )
        if not image.base_image.endswith(f"@{image.base_image_digest}"):
            raise PublicationError(f"tool {definition.id} base image digest is inconsistent")
        if image.platform != "linux/amd64":
            raise PublicationError(f"tool {definition.id} has an unsupported public image platform")
        if not tool.reported_version:
            raise PublicationError(f"tool {definition.id} lacks a reported version")
    _reject_private_material(model_to_jsonable(campaign))


def validate_public_campaign(catalog: Catalog, campaign: Campaign) -> None:
    """Apply every trust, provenance, and public-image gate before projection."""

    _validate_offline_public_campaign(campaign)
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
        assert tool.image is not None
        _require_pullable_public_image(tool.image.reference)


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
