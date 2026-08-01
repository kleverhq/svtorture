from __future__ import annotations

import pytest

import svtorture.publish as publication
from svtorture.catalog import Catalog
from svtorture.models import (
    Campaign,
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
from svtorture.publish import PublicationError, validate_public_campaign
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
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root: RepositoryIdentity(commit=ZERO_SHA, dirty=False),
    )


def _public_campaign(catalog: Catalog, *, stdout: str = "", stderr: str = "") -> Campaign:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = campaign_tool(catalog.tools.tool("slang"), ("parser",))
    result = normalized(
        case,
        "slang",
        "parser",
        observations=(
            observation(
                attempted_through_phase=Phase.PARSE,
                stage_id="parse",
                exit_code=1,
                stdout=stdout,
                stderr=stderr,
                diagnostics=(targeted(case),),
            ),
        ),
    )
    return make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(result,),
        trust=_trusted(),
    )


def test_public_campaign_accepts_only_clean_trusted_public_data(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _public_campaign(catalog)
    _trusted_environment(monkeypatch)
    validate_public_campaign(catalog, campaign)


@pytest.mark.parametrize(
    "campaign,message",
    [
        (
            lambda campaign: campaign.model_copy(
                update={"repository": RepositoryIdentity(commit=ZERO_SHA, dirty=True)}
            ),
            "clean committed checkout",
        ),
        (
            lambda campaign: campaign.model_copy(
                update={"trust": campaign.trust.model_copy(update={"checkout_sha": "f" * 40})}
            ),
            "trusted checkout SHA",
        ),
    ],
)
def test_publication_rechecks_offline_invariants(
    catalog: Catalog,
    campaign,
    message: str,
) -> None:
    with pytest.raises(PublicationError, match=message):
        publication._validate_offline_public_campaign(campaign(_public_campaign(catalog)))


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
                phase_ceiling=Phase.ELABORATE,
                direct_phases=(Phase.ELABORATE,),
                headline=True,
                standard_revision="1800-2017",
                effective_language="private wrapper",
            ),
        ),
    )
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=campaign_tool(definition, ("elaborator",)),
        results=(normalized(case, definition.id, "elaborator"),),
        trust=_trusted(),
    )
    _trusted_environment(monkeypatch)
    with pytest.raises(PublicationError, match="metadata policy"):
        validate_public_campaign(catalog, campaign)


@pytest.mark.parametrize(
    ("stdout", "stderr"),
    [
        ("/home/private-user/licensed/output", ""),
        ("", "token=github_pat_abcdefghijklmnopqrstuvwxyz012345"),
    ],
)
def test_publication_rejects_private_material(
    catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    stderr: str,
) -> None:
    campaign = _public_campaign(catalog, stdout=stdout, stderr=stderr)
    _trusted_environment(monkeypatch)
    with pytest.raises(PublicationError, match="private material"):
        validate_public_campaign(catalog, campaign)


def test_trust_fields_cannot_be_replayed_outside_github_actions(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _public_campaign(catalog)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(PublicationError, match="inside GitHub Actions"):
        validate_public_campaign(catalog, campaign)


def test_publication_rechecks_judgment_against_observations(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _public_campaign(catalog)
    result = campaign.results[0].model_copy(
        update={
            "status": ResultStatus.NONCONFORMING,
            "reason": ReasonCode.UNEXPECTED_ACCEPT,
        }
    )
    campaign = campaign.model_copy(update={"results": (result,)})
    _trusted_environment(monkeypatch)
    with pytest.raises(PublicationError, match="does not match observations"):
        validate_public_campaign(catalog, campaign)


def test_publication_requires_a_pullable_ghcr_digest(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _public_campaign(catalog)
    tool = campaign.tools[0]
    assert tool.image is not None
    tool = tool.model_copy(
        update={"image": tool.image.model_copy(update={"reference": tool.image.image_id})}
    )
    campaign = campaign.model_copy(update={"tools": (tool,)})
    _trusted_environment(monkeypatch)
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


def test_source_links_are_commit_pinned_or_locally_embedded(catalog: Catalog) -> None:
    campaign = _public_campaign(catalog)
    public = publication._source_link(catalog, campaign, "case", "source file.sv")
    assert public.endswith(f"/{ZERO_SHA}/cases/case/source%20file.sv")

    local = campaign.model_copy(update={"trust": CampaignTrust(source="local")})
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    source = case.definition.sources[0]
    embedded = publication._source_link(catalog, local, case.definition.id, source)
    assert embedded.startswith("data:text/plain;charset=utf-8,")
