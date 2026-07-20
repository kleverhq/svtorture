"""Replay one recorded tool/case observation and report environmental differences."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

from svtorture.adapters.registry import adapter_for
from svtorture.campaign import (
    CampaignError,
    load_private_config,
    verify_campaign_against_catalog,
    wrapper_available,
)
from svtorture.catalog import Catalog, load_catalog, repository_identity
from svtorture.evaluator import evaluate
from svtorture.executor import execute_plan
from svtorture.images import build_image, recipe_hash
from svtorture.models import Campaign, NormalizedResult


class ReproductionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReproductionReport:
    recorded: NormalizedResult
    replayed: NormalizedResult
    differences: tuple[str, ...]


def _ensure_checkout(root: Path, campaign: Campaign) -> Path:
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


def _ensure_image(
    checkout: Path,
    campaign_tool: object,
) -> str:
    from svtorture.models import CampaignTool

    assert isinstance(campaign_tool, CampaignTool)
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
    return rebuilt.reference


def reproduce_case(
    root: Path,
    campaign: Campaign,
    *,
    tool_id: str,
    profile_id: str,
    case_id: str,
) -> ReproductionReport:
    checkout = _ensure_checkout(root, campaign)
    anchor_index = root / "standards" / "ieee-1800-2023-anchors.json"
    catalog: Catalog = load_catalog(checkout, anchor_index=anchor_index)
    try:
        verify_campaign_against_catalog(catalog, campaign)
    except CampaignError as error:
        raise ReproductionError(str(error)) from error
    recorded = next(
        (
            item
            for item in campaign.results
            if item.tool_id == tool_id and item.profile_id == profile_id and item.case_id == case_id
        ),
        None,
    )
    if recorded is None:
        raise ReproductionError("recorded result was not found")
    campaign_tool = next((item for item in campaign.tools if item.definition.id == tool_id), None)
    if campaign_tool is None:
        raise ReproductionError("recorded tool identity was not found")
    profile = campaign_tool.definition.profile(profile_id)
    loaded = catalog.cases[case_id]
    adapter = adapter_for(
        campaign_tool.definition.adapter,
        rules_path=checkout / "tools" / "diagnostic-rules.toml",
    )
    wrapper = None
    image = None
    if campaign_tool.definition.execution.value == "docker":
        image = _ensure_image(checkout, campaign_tool)
    else:
        private = load_private_config(checkout)
        wrapper = private.wrapper(tool_id) if private else None
        if not wrapper_available(wrapper):
            raise ReproductionError("the required private wrapper is unavailable")
    plan = adapter.build_plan(
        loaded,
        campaign_tool.definition,
        profile,
        image=image,
        wrapper=wrapper.command[0] if wrapper else None,
    )
    observations = execute_plan(
        plan,
        loaded,
        adapter,
        checkout / ".svtorture" / "reproduce-work" / campaign.id / tool_id / profile_id / case_id,
        wrapper=wrapper,
    )
    replayed = evaluate(loaded, tool_id, profile_id, observations)
    differences: list[str] = []
    current_repository = repository_identity(root)
    if not campaign.repository.dirty and campaign.repository.commit != "unborn":
        if current_repository.commit != campaign.repository.commit:
            differences.append(
                "framework checkout: "
                f"recorded {campaign.repository.commit!r}, current "
                f"{current_repository.commit!r}"
            )
        if current_repository.dirty:
            differences.append("framework checkout: current worktree is dirty")
    current_platform = f"{platform.system()} {platform.machine()}"
    if current_platform != campaign.platform:
        differences.append(
            f"platform: recorded {campaign.platform!r}, current {current_platform!r}"
        )
    if replayed.status != recorded.status:
        differences.append(
            f"status: recorded {recorded.status.value}, replayed {replayed.status.value}"
        )
    if replayed.reason != recorded.reason:
        differences.append(
            f"reason: recorded {recorded.reason.value}, replayed {replayed.reason.value}"
        )
    return ReproductionReport(
        recorded=recorded,
        replayed=replayed,
        differences=tuple(differences),
    )
