from __future__ import annotations

import json
from pathlib import Path

import pytest

import svtorture.publish as publication
from svtorture.catalog import Catalog
from svtorture.models import (
    CampaignTrust,
    Distribution,
    ExecutionBackend,
    Phase,
    ReasonCode,
    RepositoryIdentity,
    ResultStatus,
    ToolDefinition,
    ToolProfile,
)
from svtorture.publish import (
    PublicationError,
    merge_datasets,
    publish_pages_tree,
    validate_public_campaign,
)
from tests.helpers import (
    ZERO_SHA,
    campaign_tool,
    make_campaign,
    normalized,
    observation,
    targeted,
)


def _trusted() -> CampaignTrust:
    return CampaignTrust(
        source="github-actions",
        repository="example/sv-torture",
        workflow_run_id="42",
        checkout_sha=ZERO_SHA,
    )


def _trusted_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/sv-torture")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_SHA", ZERO_SHA)
    monkeypatch.setattr(publication, "_require_pullable_public_image", lambda _reference: None)


def test_public_campaign_accepts_only_clean_trusted_public_data(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "slang",
                "parser",
                observations=(
                    observation(
                        phase=Phase.PARSE,
                        exit_code=1,
                        diagnostics=(targeted(case),),
                    ),
                ),
            ),
        ),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    validate_public_campaign(catalog, campaign)


def test_publication_rejects_synthetic_commercial_tool_regardless_of_name(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch23-mixed-port-style-rejected"]
    definition = ToolDefinition(
        id="licensed-simulator",
        display_name="Synthetic Licensed Simulator",
        adapter="vcs",
        distribution=Distribution.COMMERCIAL,
        execution=ExecutionBackend.LOCAL_WRAPPER,
        ci=False,
        publish=False,
        profiles=(
            ToolProfile(
                id="elaborator",
                phases=(Phase.ELABORATE,),
                headline=True,
                standard_revision="1800-2017",
                effective_language="private wrapper",
            ),
        ),
    )
    tool = campaign_tool(definition, ("elaborator",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, definition.id, "elaborator"),),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    with pytest.raises(PublicationError, match="metadata policy"):
        validate_public_campaign(catalog, campaign)


def test_publication_rejects_private_path_leaks(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    result = normalized(
        case,
        "slang",
        "parser",
        observations=(
            observation(
                phase=Phase.PARSE,
                exit_code=1,
                stdout="/home/private-user/licensed/output",
                diagnostics=(targeted(case),),
            ),
        ),
    )
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(result,),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    with pytest.raises(PublicationError, match="private material"):
        validate_public_campaign(catalog, campaign)


def test_publication_rejects_credentials_in_bounded_evidence(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    result = normalized(
        case,
        "slang",
        "parser",
        observations=(
            observation(
                phase=Phase.PARSE,
                exit_code=1,
                stderr="token=github_pat_abcdefghijklmnopqrstuvwxyz012345",
                diagnostics=(targeted(case),),
            ),
        ),
    )
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(result,),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    with pytest.raises(PublicationError, match="private material"):
        validate_public_campaign(catalog, campaign)


def test_trust_fields_cannot_be_replayed_outside_github_actions(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "slang",
                "parser",
                observations=(
                    observation(
                        phase=Phase.PARSE,
                        exit_code=1,
                        diagnostics=(targeted(case),),
                    ),
                ),
            ),
        ),
        trust=_trusted(),
    )
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(PublicationError, match="inside GitHub Actions"):
        validate_public_campaign(catalog, campaign)


def test_publication_rechecks_judgment_against_observations(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "slang",
                "parser",
                status=ResultStatus.NONCONFORMING,
                reason=ReasonCode.UNEXPECTED_ACCEPT,
                observations=(
                    observation(
                        phase=Phase.PARSE,
                        exit_code=1,
                        diagnostics=(targeted(case),),
                    ),
                ),
            ),
        ),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    with pytest.raises(PublicationError, match="does not match observations"):
        validate_public_campaign(catalog, campaign)


def test_publication_requires_a_pullable_ghcr_digest(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    assert tool.image is not None
    tool = tool.model_copy(
        update={
            "image": tool.image.model_copy(
                update={"reference": tool.image.image_id},
            )
        }
    )
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "slang",
                "parser",
                observations=(
                    observation(
                        phase=Phase.PARSE,
                        exit_code=1,
                        diagnostics=(targeted(case),),
                    ),
                ),
            ),
        ),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )
    with pytest.raises(PublicationError, match="pullable GHCR digest"):
        validate_public_campaign(catalog, campaign)


def test_publication_probes_anonymous_registry_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publication.subprocess,
        "run",
        lambda *_args, **_kwargs: publication.subprocess.CompletedProcess([], 1),
    )
    with pytest.raises(PublicationError, match="not anonymously pullable"):
        publication._require_pullable_public_image(
            "ghcr.io/example/svtorture-slang@sha256:" + "0" * 64
        )


def test_dataset_merge_is_append_only_and_detects_collision() -> None:
    old = {
        "schema_version": 2,
        "campaigns": [{"id": "one", "value": 1}],
        "metrics": [{"campaign_id": "one", "tool_id": "t", "profile_id": "p"}],
        "generated_from": ["one"],
    }
    new = {
        "schema_version": 2,
        "campaigns": [{"id": "two", "value": 2}],
        "metrics": [{"campaign_id": "two", "tool_id": "t", "profile_id": "p"}],
        "generated_from": ["two"],
    }
    legacy = dict(old)
    legacy["schema_version"] = 1
    with pytest.raises(PublicationError, match="incompatible dashboard datasets"):
        merge_datasets(legacy, new)

    merged = merge_datasets(old, new)
    assert merged["schema_version"] == 2
    assert {item["id"] for item in merged["campaigns"]} == {"one", "two"}
    collision = dict(new)
    collision["campaigns"] = [{"id": "one", "value": 999}]
    with pytest.raises(PublicationError, match="stable public identity"):
        merge_datasets(old, collision)


def test_pages_publish_preserves_history_and_regenerates_index(
    catalog: Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    first = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "fake",
                "simulator",
                observations=(
                    observation(
                        phase=Phase.SIMULATE,
                        stdout=case.definition.oracle.marker or "",
                    ),
                ),
            ),
        ),
        campaign_id="20260101T000000Z-first",
    )
    second = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(
            normalized(
                case,
                "fake",
                "simulator",
                observations=(
                    observation(
                        phase=Phase.SIMULATE,
                        stdout=case.definition.oracle.marker or "",
                    ),
                ),
            ),
        ),
        campaign_id="20260102T000000Z-second",
    )
    monkeypatch.setattr(publication, "validate_public_campaign", lambda *_args: None)
    built = tmp_path / "dist"
    built.mkdir()
    (built / "index.html").write_text("first", encoding="utf-8")
    pages = tmp_path / "pages"
    publish_pages_tree(catalog, (first,), built, pages)
    (built / "index.html").write_text("second", encoding="utf-8")
    publish_pages_tree(catalog, (second,), built, pages)
    dataset = json.loads((pages / "data" / "dataset.json").read_text(encoding="utf-8"))
    assert {item["id"] for item in dataset["campaigns"]} == {
        first.id,
        second.id,
    }
    index = json.loads((pages / "history" / "index.json").read_text(encoding="utf-8"))
    assert len(index["campaigns"]) == 2
    assert (pages / "history" / "campaigns" / f"{first.id}.json").exists()
    assert (pages / "index.html").read_text(encoding="utf-8") == "second"
    dataset["campaigns"][0]["platform"] = "/home/private-user/forged"
    (pages / "data" / "dataset.json").write_text(
        json.dumps(dataset),
        encoding="utf-8",
    )
    with pytest.raises(PublicationError, match="private material"):
        publish_pages_tree(catalog, (second,), built, pages)
