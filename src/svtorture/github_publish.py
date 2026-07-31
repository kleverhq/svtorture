"""Immutable GitHub Release publication and latest-only Pages assembly."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from svtorture.bundle import (
    MAX_ARCHIVE_BYTES,
    PagesBuildReport,
    assemble_public_pages,
    export_campaign_bundle,
    project_campaign_summary,
    sha256_file,
    validate_campaign_bundle,
    write_campaign_archive,
)
from svtorture.catalog import Catalog
from svtorture.dashboard_models import ArchiveMetadata, CampaignSummary
from svtorture.hashing import canonical_json_bytes
from svtorture.models import Campaign
from svtorture.publish import PublicationError

SUMMARY_ASSET = "campaign-summary.json"


@dataclass(frozen=True)
class PublishedCampaign:
    summary: CampaignSummary
    archive_path: Path
    summary_path: Path


def _gh(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["gh", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh failure"
        raise PublicationError(f"gh {' '.join(arguments)} failed: {detail}")
    return result


def _gh_json(arguments: list[str]) -> Any:
    result = _gh(arguments)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError(f"gh {' '.join(arguments)} returned invalid JSON") from error


def _is_missing(result: subprocess.CompletedProcess[str]) -> bool:
    detail = f"{result.stdout}\n{result.stderr}".lower()
    return result.returncode != 0 and ("not found" in detail or "http 404" in detail)


def _require_commit(repository: str, commit: str) -> None:
    result = _gh(
        ["api", f"repos/{repository}/commits/{commit}", "--jq", ".sha"],
        check=False,
    )
    if result.returncode or result.stdout.strip() != commit:
        raise PublicationError(f"recorded commit {commit} is absent from {repository}")


def _tag_target(repository: str, tag: str) -> str | None:
    encoded = quote(tag, safe="")
    result = _gh(["api", f"repos/{repository}/git/ref/tags/{encoded}"], check=False)
    if result.returncode:
        if _is_missing(result):
            return None
        raise PublicationError(result.stderr.strip() or f"cannot inspect tag {tag}")
    try:
        reference = json.loads(result.stdout)
        target_type = reference["object"]["type"]
        target = reference["object"]["sha"]
        while target_type == "tag":
            annotated = _gh_json(["api", f"repos/{repository}/git/tags/{target}"])
            target_type = annotated["object"]["type"]
            target = annotated["object"]["sha"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise PublicationError(f"tag {tag} has an invalid GitHub response") from error
    if target_type != "commit":
        raise PublicationError(f"tag {tag} does not resolve to a commit")
    return str(target)


def _release_view(repository: str, tag: str) -> dict[str, Any] | None:
    result = _gh(
        [
            "release",
            "view",
            tag,
            "--repo",
            repository,
            "--json",
            "isDraft,tagName,targetCommitish,url,assets",
        ],
        check=False,
    )
    if result.returncode:
        if _is_missing(result):
            return None
        raise PublicationError(result.stderr.strip() or f"cannot inspect Release {tag}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError(f"Release {tag} returned invalid JSON") from error
    if not isinstance(value, dict):
        raise PublicationError(f"Release {tag} returned an invalid object")
    return value


def _asset_names(release: dict[str, Any]) -> set[str]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise PublicationError("GitHub Release assets are missing")
    names: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
            raise PublicationError("GitHub Release asset metadata is invalid")
        names.append(asset["name"])
    if len(names) != len(set(names)):
        raise PublicationError("GitHub Release has duplicate asset names")
    return set(names)


def _download_asset(repository: str, tag: str, name: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    destination.unlink(missing_ok=True)
    _gh(
        [
            "release",
            "download",
            tag,
            "--repo",
            repository,
            "--pattern",
            name,
            "--dir",
            str(directory),
        ]
    )
    if not destination.is_file():
        raise PublicationError(f"Release {tag} did not provide asset {name}")
    return destination


def _verify_existing_assets(
    repository: str,
    tag: str,
    release: dict[str, Any],
    expected: dict[str, Path],
    directory: Path,
) -> set[str]:
    names = _asset_names(release)
    extras = names - set(expected)
    if extras:
        raise PublicationError(f"Release {tag} has unexpected assets: {', '.join(sorted(extras))}")
    for name in names:
        downloaded = _download_asset(repository, tag, name, directory)
        local = expected[name]
        if downloaded.stat().st_size != local.stat().st_size or sha256_file(downloaded) != (
            sha256_file(local)
        ):
            raise PublicationError(f"immutable Release asset collision for {tag}/{name}")
    return names


def _publish_draft_assets(
    repository: str,
    tag: str,
    release: dict[str, Any],
    expected: dict[str, Path],
    directory: Path,
    expected_commit: str,
) -> None:
    present = _verify_existing_assets(repository, tag, release, expected, directory)
    missing = [path for name, path in expected.items() if name not in present]
    if missing:
        _gh(
            [
                "release",
                "upload",
                tag,
                *(str(path) for path in missing),
                "--repo",
                repository,
            ]
        )
    refreshed = _release_view(repository, tag)
    if refreshed is None:
        raise PublicationError(f"draft Release {tag} disappeared after asset upload")
    verified = _verify_existing_assets(
        repository,
        tag,
        refreshed,
        expected,
        directory / "post-upload",
    )
    if verified != set(expected):
        raise PublicationError(f"draft Release {tag} does not contain exactly the expected assets")
    _gh(
        [
            "release",
            "edit",
            tag,
            "--repo",
            repository,
            "--draft=false",
            "--latest=false",
        ]
    )
    if _tag_target(repository, tag) != expected_commit:
        raise PublicationError(f"published Release {tag} has an unexpected tag target")


def publish_campaign_release(
    catalog: Catalog,
    campaign: Campaign,
    repository: str,
    workspace: Path,
) -> PublishedCampaign:
    """Create or verify one immutable campaign tag and Release."""

    bundle_root = workspace / "bundle"
    campaign_root = export_campaign_bundle(catalog, campaign, bundle_root, public=True)
    manifest = validate_campaign_bundle(campaign_root)
    tag = f"campaign-{campaign.id}"
    archive_name = f"svtorture-campaign-{campaign.id}.zip"
    archive_path = write_campaign_archive(campaign_root, workspace / archive_name)
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PublicationError(f"campaign archive {archive_name} exceeds GitHub's 2 GiB limit")
    archive = ArchiveMetadata(
        release_tag=tag,
        release_url=f"https://github.com/{repository}/releases/tag/{tag}",
        asset_name=archive_name,
        download_url=f"https://github.com/{repository}/releases/download/{tag}/{archive_name}",
        sha256=sha256_file(archive_path),
        bytes=archive_path.stat().st_size,
    )
    summary = project_campaign_summary(manifest, archive)
    summary_path = workspace / SUMMARY_ASSET
    summary_path.write_bytes(
        canonical_json_bytes(summary.model_dump(mode="json", exclude_none=True))
    )
    notes = workspace / "release-notes.md"
    notes.write_text(
        f"Immutable SVTORTURE campaign `{campaign.id}` from `{campaign.repository.commit}`.\n",
        encoding="utf-8",
    )

    _require_commit(repository, campaign.repository.commit)
    target = _tag_target(repository, tag)
    if target is not None and target != campaign.repository.commit:
        raise PublicationError(
            f"immutable tag collision: {tag} points to {target}, not {campaign.repository.commit}"
        )
    release = _release_view(repository, tag)
    expected = {archive_name: archive_path, SUMMARY_ASSET: summary_path}
    if release is not None:
        if release.get("tagName") != tag:
            raise PublicationError(f"Release tag identity mismatch for {tag}")
        if (
            target is None
            and release.get("isDraft") is True
            and release.get("targetCommitish") != campaign.repository.commit
        ):
            raise PublicationError(f"draft Release {tag} targets an unexpected commit")
        if release.get("isDraft") is False:
            present = _verify_existing_assets(
                repository,
                tag,
                release,
                expected,
                workspace / "existing-assets",
            )
            if present != set(expected):
                raise PublicationError(f"published Release {tag} is missing immutable assets")
            return PublishedCampaign(summary, archive_path, summary_path)
        if release.get("isDraft") is not True:
            raise PublicationError(f"Release {tag} has an unknown draft state")
        _publish_draft_assets(
            repository,
            tag,
            release,
            expected,
            workspace / "existing-assets",
            campaign.repository.commit,
        )
        return PublishedCampaign(summary, archive_path, summary_path)

    _gh(
        [
            "release",
            "create",
            tag,
            "--repo",
            repository,
            "--target",
            campaign.repository.commit,
            "--title",
            f"SVTORTURE campaign {campaign.id}",
            "--notes-file",
            str(notes),
            "--draft",
            "--latest=false",
        ]
    )
    draft = _release_view(repository, tag)
    if (
        draft is None
        or draft.get("isDraft") is not True
        or draft.get("tagName") != tag
        or draft.get("targetCommitish") != campaign.repository.commit
    ):
        raise PublicationError(f"GitHub created draft Release {tag} with an invalid identity")
    _publish_draft_assets(
        repository,
        tag,
        draft,
        expected,
        workspace / "existing-assets",
        campaign.repository.commit,
    )
    return PublishedCampaign(summary, archive_path, summary_path)


def _published_releases(repository: str) -> list[dict[str, Any]]:
    value = _gh_json(
        [
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repository}/releases?per_page=100",
        ]
    )
    if not isinstance(value, list):
        raise PublicationError("GitHub releases response is not a list")
    pages = value if value and isinstance(value[0], list) else [value]
    releases: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, list) or any(not isinstance(item, dict) for item in page):
            raise PublicationError("GitHub releases page is invalid")
        releases.extend(page)
    return releases


def load_release_summaries(repository: str, workspace: Path) -> tuple[CampaignSummary, ...]:
    """Download, validate, and return unchanged summaries from published Releases."""

    summaries: dict[str, CampaignSummary] = {}
    for release in _published_releases(repository):
        tag = release.get("tag_name")
        if (
            not isinstance(tag, str)
            or not tag.startswith("campaign-")
            or release.get("draft") is not False
            or release.get("prerelease") is not False
        ):
            continue
        release_url = release.get("html_url")
        assets = release.get("assets")
        if not isinstance(release_url, str) or not isinstance(assets, list):
            raise PublicationError(f"campaign Release {tag} has invalid metadata")
        asset_by_name: dict[str, dict[str, Any]] = {}
        for asset in assets:
            if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
                raise PublicationError(f"campaign Release {tag} has invalid asset metadata")
            name = asset["name"]
            if name in asset_by_name:
                raise PublicationError(f"campaign Release {tag} has duplicate assets")
            asset_by_name[name] = asset
        if SUMMARY_ASSET not in asset_by_name:
            raise PublicationError(f"campaign Release {tag} has no {SUMMARY_ASSET}")
        directory = workspace / tag
        path = _download_asset(repository, tag, SUMMARY_ASSET, directory)
        try:
            summary = CampaignSummary.model_validate_json(path.read_bytes())
        except ValidationError as error:
            raise PublicationError(f"campaign Release {tag} has an invalid summary") from error
        archive = summary.archive
        expected_id = tag.removeprefix("campaign-")
        if (
            summary.id != expected_id
            or archive is None
            or archive.release_tag != tag
            or archive.release_url != release_url
            or archive.asset_name not in asset_by_name
            or archive.bytes > MAX_ARCHIVE_BYTES
            or type(asset_by_name[archive.asset_name].get("size")) is not int
            or asset_by_name[archive.asset_name]["size"] != archive.bytes
            or asset_by_name[archive.asset_name].get("browser_download_url") != archive.download_url
        ):
            raise PublicationError(f"campaign Release {tag} summary identity mismatch")
        if summary.id in summaries:
            raise PublicationError(f"duplicate published campaign id {summary.id}")
        summaries[summary.id] = summary
    if not summaries:
        raise PublicationError("no published campaign Releases were found")
    return tuple(sorted(summaries.values(), key=lambda item: (item.finished_at, item.id)))


def build_pages_from_releases(
    repository: str,
    built_site: Path,
    output: Path,
    schema_directory: Path,
    workspace: Path,
) -> tuple[tuple[CampaignSummary, ...], PagesBuildReport]:
    """Rebuild public history and latest-only Pages data entirely from Releases."""

    summaries = load_release_summaries(repository, workspace / "summaries")
    latest = summaries[-1]
    assert latest.archive is not None
    archive_path = _download_asset(
        repository,
        latest.archive.release_tag,
        latest.archive.asset_name,
        workspace / "latest",
    )
    report = assemble_public_pages(
        built_site,
        summaries,
        archive_path,
        output,
        schema_directory,
    )
    return summaries, report


def publish_dashboard(
    catalog: Catalog,
    campaigns: tuple[Campaign, ...],
    repository: str,
    built_site: Path,
    output: Path,
    schema_directory: Path,
) -> tuple[tuple[CampaignSummary, ...], PagesBuildReport]:
    """Publish campaign Releases, then derive a clean Pages tree from all Releases."""

    if not campaigns:
        raise PublicationError("at least one campaign is required for publication")
    with tempfile.TemporaryDirectory(prefix="svtorture-publish-") as temporary:
        workspace = Path(temporary)
        for campaign in campaigns:
            publish_campaign_release(
                catalog,
                campaign,
                repository,
                workspace / campaign.id,
            )
        return build_pages_from_releases(
            repository,
            built_site,
            output,
            schema_directory,
            workspace,
        )
