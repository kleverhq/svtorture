from __future__ import annotations

import json
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

import svtorture.bundle as bundle
import svtorture.github_publish as publication
from svtorture.catalog import Catalog
from svtorture.github_publish import (
    build_pages_from_releases,
    load_release_summaries,
    publish_campaign_release,
)
from svtorture.models import (
    Campaign,
    CampaignTrust,
    ImageIdentity,
    Phase,
    RepositoryIdentity,
    ToolSelection,
)
from svtorture.publish import PublicationError
from tests.helpers import campaign_tool, make_campaign, normalized, observation, targeted


class FakeGitHub:
    def __init__(self, repository: str, commit: str) -> None:
        self.repository = repository
        self.commit = commit
        self.tags: dict[str, str] = {}
        self.releases: dict[str, dict[str, Any]] = {}
        self.commands: list[list[str]] = []

    def _result(
        self, arguments: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["gh", *arguments], returncode, stdout, stderr)

    def _assets(self, tag: str) -> list[dict[str, Any]]:
        release = self.releases[tag]
        return [
            {
                "name": name,
                "size": len(data),
                "browser_download_url": (
                    f"https://github.com/{self.repository}/releases/download/{tag}/{name}"
                ),
            }
            for name, data in release["assets"].items()
        ]

    def __call__(
        self, arguments: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(arguments)
        result = self._dispatch(arguments)
        if check and result.returncode:
            raise PublicationError(result.stderr)
        return result

    def _dispatch(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        if arguments[:2] == ["api", f"repos/{self.repository}/commits/{self.commit}"]:
            return self._result(arguments, stdout=f"{self.commit}\n")
        if arguments[:2] == ["api", "--paginate"]:
            releases = [
                {
                    "tag_name": tag,
                    "draft": release["draft"],
                    "prerelease": False,
                    "html_url": f"https://github.com/{self.repository}/releases/tag/{tag}",
                    "assets": self._assets(tag),
                }
                for tag, release in self.releases.items()
            ]
            return self._result(arguments, stdout=json.dumps([releases]))
        if arguments[0] == "api" and "/git/ref/tags/" in arguments[1]:
            tag = arguments[1].split("/git/ref/tags/", 1)[1]
            target = self.tags.get(tag)
            if target is None:
                return self._result(arguments, 1, stderr="HTTP 404: Not Found")
            return self._result(
                arguments,
                stdout=json.dumps({"object": {"type": "commit", "sha": target}}),
            )
        if arguments[:2] == ["release", "view"]:
            tag = arguments[2]
            release = self.releases.get(tag)
            if release is None:
                return self._result(arguments, 1, stderr="release not found")
            return self._result(
                arguments,
                stdout=json.dumps(
                    {
                        "isDraft": release["draft"],
                        "tagName": tag,
                        "targetCommitish": release["target"],
                        "url": f"https://github.com/{self.repository}/releases/tag/{tag}",
                        "assets": self._assets(tag),
                    }
                ),
            )
        if arguments[:2] == ["release", "create"]:
            tag = arguments[2]
            target = arguments[arguments.index("--target") + 1]
            self.tags.setdefault(tag, target)
            self.releases[tag] = {"draft": True, "target": target, "assets": {}}
            return self._result(arguments)
        if arguments[:2] == ["release", "upload"]:
            tag = arguments[2]
            repository_index = arguments.index("--repo")
            for path_value in arguments[3:repository_index]:
                path = Path(path_value)
                self.releases[tag]["assets"][path.name] = path.read_bytes()
            return self._result(arguments)
        if arguments[:2] == ["release", "edit"]:
            self.releases[arguments[2]]["draft"] = False
            return self._result(arguments)
        if arguments[:2] == ["release", "download"]:
            tag = arguments[2]
            name = arguments[arguments.index("--pattern") + 1]
            directory = Path(arguments[arguments.index("--dir") + 1])
            directory.mkdir(parents=True, exist_ok=True)
            data = self.releases.get(tag, {}).get("assets", {}).get(name)
            if data is None:
                return self._result(arguments, 1, stderr="asset not found")
            (directory / name).write_bytes(data)
            return self._result(arguments)
        return self._result(arguments, 1, stderr=f"unsupported fake gh command: {arguments}")


@pytest.fixture
def public_campaign(catalog: Catalog) -> Campaign:
    loaded = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    selected = tool.model_copy(
        update={
            "selection": ToolSelection(
                tool="slang",
                requested_ref="latest",
                resolved_sha="2" * 40,
                resolved_at="2026-01-01T00:00:00Z",
                exact_tags=("v1.0.0",),
                nearest_tag=None,
                default_branch="main",
            ),
            "image": ImageIdentity(
                reference=f"ghcr.io/example/slang@sha256:{'3' * 64}",
                image_id=f"sha256:{'4' * 64}",
                digest=f"sha256:{'3' * 64}",
                recipe_sha256="5" * 64,
                base_image="example/base:1",
                base_image_digest=f"sha256:{'6' * 64}",
                platform="linux/amd64",
            ),
        }
    )
    result = normalized(
        loaded,
        "slang",
        "parser",
        observations=(
            observation(
                attempted_through_phase=Phase.PARSE,
                stage_id="parse",
                exit_code=1,
                diagnostics=(targeted(loaded),),
            ),
        ),
    )
    return make_campaign(
        catalog,
        cases=(loaded,),
        tool=selected,
        results=(result,),
        repository=RepositoryIdentity(commit="1" * 40, dirty=False),
        trust=CampaignTrust(
            source="github-actions",
            repository="example/repo",
            workflow_run_id="123",
            checkout_sha="1" * 40,
        ),
    )


def test_release_lifecycle_is_immutable_idempotent_and_resumes_draft(
    catalog: Catalog,
    public_campaign: Campaign,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHub("example/repo", public_campaign.repository.commit)
    monkeypatch.setattr(publication, "_gh", fake)
    monkeypatch.setattr(bundle, "validate_public_campaign", lambda _catalog, _campaign: None)

    published = publish_campaign_release(
        catalog, public_campaign, fake.repository, tmp_path / "first"
    )
    tag = published.summary.archive.release_tag  # type: ignore[union-attr]
    assert fake.tags[tag] == public_campaign.repository.commit
    assert fake.releases[tag]["draft"] is False
    assert set(fake.releases[tag]["assets"]) == {
        published.archive_path.name,
        publication.SUMMARY_ASSET,
    }
    mutation_count = len(
        [
            command
            for command in fake.commands
            if command[:2] in (["release", "create"], ["release", "upload"], ["release", "edit"])
        ]
    )

    publish_campaign_release(catalog, public_campaign, fake.repository, tmp_path / "retry")
    assert (
        len(
            [
                command
                for command in fake.commands
                if command[:2]
                in (["release", "create"], ["release", "upload"], ["release", "edit"])
            ]
        )
        == mutation_count
    )

    fake.releases[tag]["draft"] = True
    del fake.releases[tag]["assets"][publication.SUMMARY_ASSET]
    publish_campaign_release(catalog, public_campaign, fake.repository, tmp_path / "resume")
    assert fake.releases[tag]["draft"] is False
    assert publication.SUMMARY_ASSET in fake.releases[tag]["assets"]

    fake.releases[tag]["assets"][published.archive_path.name] = b"collision"
    with pytest.raises(PublicationError, match="immutable Release asset collision"):
        publish_campaign_release(catalog, public_campaign, fake.repository, tmp_path / "collision")


def test_release_rejects_tagless_draft_targeting_another_commit(
    catalog: Catalog,
    public_campaign: Campaign,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHub("example/repo", public_campaign.repository.commit)
    fake.releases[f"campaign-{public_campaign.id}"] = {
        "draft": True,
        "target": "f" * 40,
        "assets": {},
    }
    monkeypatch.setattr(publication, "_gh", fake)
    monkeypatch.setattr(bundle, "validate_public_campaign", lambda _catalog, _campaign: None)

    with pytest.raises(PublicationError, match="targets an unexpected commit"):
        publish_campaign_release(catalog, public_campaign, fake.repository, tmp_path)


def test_release_rejects_existing_tag_on_another_commit(
    catalog: Catalog,
    public_campaign: Campaign,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHub("example/repo", public_campaign.repository.commit)
    fake.tags[f"campaign-{public_campaign.id}"] = "f" * 40
    monkeypatch.setattr(publication, "_gh", fake)
    monkeypatch.setattr(bundle, "validate_public_campaign", lambda _catalog, _campaign: None)

    with pytest.raises(PublicationError, match="immutable tag collision"):
        publish_campaign_release(catalog, public_campaign, fake.repository, tmp_path)


def test_release_history_uses_campaign_time_for_latest_pages(
    catalog: Catalog,
    public_campaign: Campaign,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHub("example/repo", public_campaign.repository.commit)
    monkeypatch.setattr(publication, "_gh", fake)
    monkeypatch.setattr(bundle, "validate_public_campaign", lambda _catalog, _campaign: None)
    latest = publish_campaign_release(
        catalog, public_campaign, fake.repository, tmp_path / "latest"
    )
    backfill_campaign = public_campaign.model_copy(
        update={
            "id": "20250101T000000Z-backfill",
            "started_at": public_campaign.started_at - timedelta(days=365),
            "finished_at": public_campaign.finished_at - timedelta(days=365),
        }
    )
    publish_campaign_release(
        catalog,
        backfill_campaign,
        fake.repository,
        tmp_path / "backfill",
    )

    summaries = load_release_summaries(fake.repository, tmp_path / "summaries")
    assert [summary.id for summary in summaries] == [backfill_campaign.id, public_campaign.id]

    built_site = tmp_path / "built"
    built_site.mkdir()
    (built_site / "index.html").write_text("<html></html>", encoding="utf-8")
    history, report = build_pages_from_releases(
        fake.repository,
        built_site,
        tmp_path / "pages",
        Path(__file__).resolve().parents[1] / "schemas",
        tmp_path / "pages-work",
    )
    index = json.loads((tmp_path / "pages" / "data" / "index.json").read_text(encoding="utf-8"))
    trends = json.loads((tmp_path / "pages" / "data" / "trends.json").read_text(encoding="utf-8"))
    assert index["default_campaign_id"] == public_campaign.id
    assert [item["id"] for item in trends["campaigns"]] == [
        backfill_campaign.id,
        public_campaign.id,
    ]
    assert history[-1] == latest.summary
    assert report.total_bytes > report.trends_bytes
