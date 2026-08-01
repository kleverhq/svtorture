from __future__ import annotations

import json
import urllib.request
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import svtorture.reproduce as reproduction
from svtorture.bundle import export_campaign_bundle, write_campaign_archive
from svtorture.catalog import Catalog
from svtorture.hashing import canonical_json_bytes, sha256_bytes
from svtorture.models import Phase
from tests.helpers import campaign_tool, make_campaign, normalized, observation


class CatalogLoaded(Exception):
    pass


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


def test_replay_uses_the_current_vendored_anchor_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "current"
    checkout = tmp_path / "recorded"
    observed: dict[str, Path] = {}
    metadata = SimpleNamespace(
        repository=SimpleNamespace(dirty=False, commit="1" * 40),
        id="campaign",
        platform="test",
    )
    source = SimpleNamespace(manifest=metadata)

    monkeypatch.setattr(reproduction, "_ensure_checkout", lambda *_args: checkout)

    def load_catalog(path: Path, *, anchor_index: Path) -> None:
        observed["checkout"] = path
        observed["anchor_index"] = anchor_index
        raise CatalogLoaded

    monkeypatch.setattr(reproduction, "load_catalog", load_catalog)
    with pytest.raises(CatalogLoaded):
        reproduction.reproduce_case(
            root,
            source,
            tool_id="tool",
            profile_id="profile",
            case_id="case",
        )

    assert observed == {
        "checkout": checkout,
        "anchor_index": root / "standards" / "ieee-1800-2023-anchors.json",
    }


def test_rebuilt_image_must_match_recorded_image_id(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool = campaign_tool(catalog.tools.tool("icarus"), ("simulator",))
    assert tool.image is not None
    monkeypatch.setattr(
        reproduction.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(
        reproduction,
        "recipe_hash",
        lambda *_args: tool.image.recipe_sha256,
    )
    rebuilt = tool.image.model_copy(update={"image_id": "sha256:" + "f" * 64})
    monkeypatch.setattr(reproduction, "build_image", lambda *_args, **_kwargs: rebuilt)

    with pytest.raises(reproduction.ReproductionError, match="image ID differs"):
        reproduction._ensure_image(tmp_path, tool)


def test_replay_context_loads_only_selected_shard_from_manifest_and_zip(
    catalog: Catalog,
    tmp_path: Path,
) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(
        catalog,
        campaign,
        tmp_path / "bundle",
        max_shard_cases=1,
    )
    archive = write_campaign_archive(campaign_root, tmp_path / "campaign.zip")
    selected_case = campaign.case_ids[0]
    unselected_case = campaign.case_ids[1]
    manifest = json.loads((campaign_root / "manifest.json").read_text(encoding="utf-8"))
    verdicts = json.loads((campaign_root / "verdicts.json").read_text(encoding="utf-8"))
    href_by_case = {item["case_id"]: item["evidence_href"] for item in verdicts["cases"]}
    (campaign_root / href_by_case[unselected_case]).write_text("not json", encoding="utf-8")

    local = reproduction.load_replay_location(
        str(campaign_root / "manifest.json"),
        tool_id="fake",
        profile_id="simulator",
        case_id=selected_case,
    )
    zipped = reproduction.load_replay_location(
        str(archive),
        tool_id="fake",
        profile_id="simulator",
        case_id=selected_case,
    )
    assert isinstance(local, reproduction.ReplayContext)
    assert isinstance(zipped, reproduction.ReplayContext)
    assert local.result.model_copy(update={"reproduction_command": None}) == (
        zipped.result.model_copy(update={"reproduction_command": None})
    )
    assert str(campaign_root / "manifest.json") in (local.result.reproduction_command or "")
    assert str(archive) in (zipped.result.reproduction_command or "")
    assert local.case.id == selected_case
    assert href_by_case[selected_case] != href_by_case[unselected_case]
    assert manifest["resources"]["evidence"]

    metadata, tool, recorded = reproduction._select_context(
        catalog,
        local,
        tool_id="fake",
        profile_id="simulator",
        case_id=selected_case,
    )
    assert metadata.id == campaign.id
    assert tool.definition.id == "fake"
    assert recorded == local.result


def test_archive_directory_must_match_manifest_id(
    catalog: Catalog,
    tmp_path: Path,
) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(catalog, campaign, tmp_path / "bundle")
    archive = write_campaign_archive(campaign_root, tmp_path / "campaign.zip")
    renamed = tmp_path / "renamed.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(renamed, "w") as target:
        for info in source.infolist():
            name = info.filename.replace(
                f"campaigns/{campaign.id}/", "campaigns/different-campaign/", 1
            )
            renamed_info = zipfile.ZipInfo(name, info.date_time)
            renamed_info.external_attr = info.external_attr
            renamed_info.compress_type = info.compress_type
            target.writestr(renamed_info, source.read(info.filename))

    with pytest.raises(reproduction.ReproductionError, match="directory does not match"):
        reproduction.load_replay_location(
            str(renamed),
            tool_id="fake",
            profile_id="simulator",
            case_id=campaign.case_ids[0],
        )


def test_remote_release_zip_loads_selected_context(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(catalog, campaign, tmp_path / "bundle")
    archive = write_campaign_archive(campaign_root, tmp_path / "campaign.zip")
    location = (
        "https://github.com/example/repo/releases/download/"
        f"campaign-{campaign.id}/svtorture-campaign-{campaign.id}.zip"
    )
    downloads: list[str] = []

    def download(url: str, destination: Path) -> None:
        downloads.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(reproduction, "_download_https_archive", download)
    context = reproduction.load_replay_location(
        location,
        tool_id="fake",
        profile_id="simulator",
        case_id=campaign.case_ids[0],
    )
    assert isinstance(context, reproduction.ReplayContext)
    assert context.id == campaign.id
    assert downloads == [location]


def test_remote_manifest_replay_is_bounded_same_origin_and_one_shard(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(
        catalog,
        campaign,
        tmp_path / "bundle",
        max_shard_cases=1,
    )
    selected_case = campaign.case_ids[0]
    verdicts = json.loads((campaign_root / "verdicts.json").read_text(encoding="utf-8"))
    selected_href = next(
        item["evidence_href"] for item in verdicts["cases"] if item["case_id"] == selected_case
    )
    base = f"https://example.test/data/campaigns/{campaign.id}/"
    payloads = {
        base + path.relative_to(campaign_root).as_posix(): path.read_bytes()
        for path in campaign_root.rglob("*")
        if path.is_file()
    }
    requested: list[str] = []

    class Response:
        def __init__(self, url: str, payload: bytes) -> None:
            self.url = url
            self.payload = payload
            self.headers = {"Content-Length": str(len(payload))}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self) -> str:
            return self.url

        def read(self, maximum: int) -> bytes:
            return self.payload[:maximum]

    def urlopen(request: urllib.request.Request, *, timeout: int):
        assert timeout == 30
        requested.append(request.full_url)
        return Response(request.full_url, payloads[request.full_url])

    monkeypatch.setattr(reproduction.urllib.request, "urlopen", urlopen)
    context = reproduction.load_replay_location(
        base + "manifest.json",
        tool_id="fake",
        profile_id="simulator",
        case_id=selected_case,
    )
    assert isinstance(context, reproduction.ReplayContext)
    assert requested == [
        base + "manifest.json",
        base + "catalog.json",
        base + "verdicts.json",
        base + selected_href,
    ]
    assert len([url for url in requested if "/evidence/" in url]) == 1


def test_canonical_manifest_and_zip_share_replay_execution(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _campaign(catalog)
    canonical = tmp_path / "campaign.json"
    canonical.write_text(campaign.model_dump_json(), encoding="utf-8")
    campaign_root = export_campaign_bundle(catalog, campaign, tmp_path / "bundle")
    archive = write_campaign_archive(campaign_root, tmp_path / "campaign.zip")
    case_id = campaign.case_ids[0]
    recorded = next(result for result in campaign.results if result.case_id == case_id)
    plans = []

    monkeypatch.setattr(reproduction, "_ensure_checkout", lambda *_args: catalog.root)
    monkeypatch.setattr(reproduction, "load_catalog", lambda *_args, **_kwargs: catalog)
    monkeypatch.setattr(reproduction, "_ensure_image", lambda *_args: "test-image")

    def execute(plan, *_args, **_kwargs):
        plans.append(plan)
        return recorded.observations

    monkeypatch.setattr(reproduction, "execute_plan", execute)
    for location in (canonical, campaign_root / "manifest.json", archive):
        source = reproduction.load_replay_location(
            str(location),
            tool_id="fake",
            profile_id="simulator",
            case_id=case_id,
        )
        report = reproduction.reproduce_case(
            catalog.root,
            source,
            tool_id="fake",
            profile_id="simulator",
            case_id=case_id,
        )
        assert report.recorded.status == report.replayed.status
        assert report.recorded.reason == report.replayed.reason

    assert len(plans) == 3
    assert plans[0] == plans[1] == plans[2]


def test_remote_resource_path_rejects_nested_encoding() -> None:
    owner = "https://example.test/data/campaigns/id/manifest.json"
    with pytest.raises(reproduction.ReproductionError, match="unsafe remote"):
        reproduction._remote_resource_url(owner, "%252e%252e%252fsecret.json")


def test_local_manifest_read_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b"x" * 11)
    monkeypatch.setattr(reproduction, "MAX_MANIFEST_BYTES", 10)
    with pytest.raises(reproduction.ReproductionError, match="manifest exceeds"):
        reproduction.load_replay_location(
            str(manifest),
            tool_id="fake",
            profile_id="simulator",
            case_id="case",
        )


def test_replay_rejects_manifest_resource_count_tampering(catalog: Catalog, tmp_path: Path) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(catalog, campaign, tmp_path / "bundle")
    manifest_path = campaign_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verdicts_path = campaign_root / "verdicts.json"
    verdicts = json.loads(verdicts_path.read_text(encoding="utf-8"))
    verdicts["cases"][0]["results"].clear()
    verdicts["result_count"] -= 1
    verdict_bytes = canonical_json_bytes(verdicts)
    verdicts_path.write_bytes(verdict_bytes)
    manifest["resources"]["verdicts"]["bytes"] = len(verdict_bytes)
    manifest["resources"]["verdicts"]["sha256"] = sha256_bytes(verdict_bytes)
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    with pytest.raises(reproduction.ReproductionError, match="verdict counts"):
        reproduction.load_replay_location(
            str(manifest_path),
            tool_id="fake",
            profile_id="simulator",
            case_id=campaign.case_ids[0],
        )


def test_replay_rejects_selected_resource_tampering(catalog: Catalog, tmp_path: Path) -> None:
    campaign = _campaign(catalog)
    campaign_root = export_campaign_bundle(catalog, campaign, tmp_path / "bundle")
    verdicts = json.loads((campaign_root / "verdicts.json").read_text(encoding="utf-8"))
    href = verdicts["cases"][0]["evidence_href"]
    path = campaign_root / href
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(reproduction.ReproductionError, match="replay resource"):
        reproduction.load_replay_location(
            str(campaign_root / "manifest.json"),
            tool_id="fake",
            profile_id="simulator",
            case_id=campaign.case_ids[0],
        )
