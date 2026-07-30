from __future__ import annotations

import json
from dataclasses import replace
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
                        attempted_through_phase=Phase.PARSE,
                        stage_id="parse",
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


def test_merge_rechecks_offline_public_campaign_invariants(catalog: Catalog) -> None:
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
                        attempted_through_phase=Phase.PARSE,
                        stage_id="parse",
                        exit_code=1,
                        diagnostics=(targeted(case),),
                    ),
                ),
            ),
        ),
        trust=_trusted(),
    )
    dataset = publication.build_dataset(catalog, (campaign,), visibility="local")
    dataset["visibility"] = "public"
    assert merge_datasets(dataset, dataset)["visibility"] == "public"

    for mutate, message in (
        (
            lambda value: value["campaigns"][0]["repository"].update({"dirty": True}),
            "clean committed checkout",
        ),
        (
            lambda value: value["campaigns"][0]["trust"].update({"checkout_sha": "f" * 40}),
            "trusted checkout SHA",
        ),
        (
            lambda value: value["campaigns"][0]["tools"][0]["definition"].update(
                {"publish": False}
            ),
            "metadata policy",
        ),
    ):
        tampered = json.loads(json.dumps(dataset))
        mutate(tampered)
        with pytest.raises(PublicationError, match=message):
            merge_datasets(tampered, dataset)


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
                attempted_through_phase=Phase.PARSE,
                stage_id="parse",
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
                attempted_through_phase=Phase.PARSE,
                stage_id="parse",
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
                        attempted_through_phase=Phase.PARSE,
                        stage_id="parse",
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
                        attempted_through_phase=Phase.PARSE,
                        stage_id="parse",
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
                        attempted_through_phase=Phase.PARSE,
                        stage_id="parse",
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


def test_dataset_embeds_campaign_corpus_metrics(catalog: Catalog) -> None:
    case = catalog.cases["ch13-output-copyout-width"]
    campaign = make_campaign(
        catalog,
        cases=(case,),
        tool=campaign_tool(catalog.tools.tool("fake"), ("simulator",)),
        results=(normalized(case, "fake", "simulator"),),
    )

    dataset = publication.build_dataset(catalog, (campaign,), visibility="local")
    assert dataset["schema_version"] == 5
    assert dataset["campaigns"][0]["schema_version"] == 5
    assert all(
        isinstance(requirement["part"], str) and "chapter" not in requirement
        for requirement in dataset["requirements"]
    )
    assert dataset["campaigns"][0]["corpus_metrics"] == dataset["corpus_coverage"]
    assert len(dataset["campaigns"][0]["corpus_metrics"]["requirements"]["breakdown"]) == 58
    assert len(dataset["campaigns"][0]["corpus_metrics"]["cases"]["breakdown"]) == 58


def test_dataset_reports_corpus_coverage_by_standard_part(catalog: Catalog) -> None:
    dataset = publication.build_dataset(catalog, (), visibility="local")
    assert dataset["schema_version"] == 5
    coverage = dataset["corpus_coverage"]

    assert coverage["requirements"]["coverage"] == {
        "numerator": 16,
        "denominator": 16963,
    }
    assert coverage["requirements"]["density"] == {
        "numerator": 17,
        "denominator": 16,
    }
    assert coverage["cases"]["coverage"] == {
        "numerator": 12,
        "denominator": 12,
    }
    assert coverage["cases"]["density"] == {
        "numerator": 12,
        "denominator": 12,
    }

    requirement_parts = coverage["requirements"]["breakdown"]
    case_parts = coverage["cases"]["breakdown"]
    assert len(requirement_parts) == len(case_parts) == 58
    assert [(part["kind"], part["id"]) for part in requirement_parts] == [
        *[("chapter", str(chapter)) for chapter in range(1, 42)],
        *[("annex", letter) for letter in "ABCDEFGHIJKLMNOPQ"],
    ]
    chapter_six = next(part for part in requirement_parts if part["id"] == "6")
    assert chapter_six["coverage"]["numerator"] == 1
    assert chapter_six["density"] == {"numerator": 2, "denominator": 1}
    chapter_three = next(part for part in requirement_parts if part["id"] == "3")
    assert chapter_three["coverage"]["numerator"] == 1
    annex_a = next(part for part in case_parts if part["id"] == "A")
    assert annex_a["coverage"] == {"numerator": 0, "denominator": 0}
    assert annex_a["density"] == {"numerator": 0, "denominator": 0}


def test_dataset_uses_catalog_runtime_anchor_index(catalog: Catalog, tmp_path: Path) -> None:
    external_catalog = replace(catalog, root=tmp_path)
    assert not (tmp_path / "standards" / "ieee-1800-2023-anchors.json").exists()

    coverage = publication.build_dataset(external_catalog, (), visibility="local")[
        "corpus_coverage"
    ]["requirements"]
    assert coverage["coverage"] == {"numerator": 16, "denominator": 16963}


def test_dataset_counts_related_case_requirements(catalog: Catalog) -> None:
    case_id = "ch04-nba-rhs-captured"
    loaded = catalog.cases[case_id]
    related_requirement = "SV-2023-05-BASED-LITERAL-TOKEN"
    modified_case = replace(
        loaded,
        definition=loaded.definition.model_copy(
            update={"related_requirements": (related_requirement,)}
        ),
    )
    modified_catalog = replace(
        catalog,
        cases={**catalog.cases, case_id: modified_case},
    )

    coverage = publication.build_dataset(modified_catalog, (), visibility="local")[
        "corpus_coverage"
    ]["cases"]
    assert coverage["coverage"] == {"numerator": 12, "denominator": 12}
    assert coverage["density"] == {"numerator": 13, "denominator": 12}
    chapter_five = next(part for part in coverage["breakdown"] if part["id"] == "5")
    assert chapter_five["density"] == {"numerator": 2, "denominator": 1}


def test_dataset_merge_is_strict_append_only_and_detects_collision(
    catalog: Catalog,
) -> None:
    case = catalog.cases["ch13-output-copyout-width"]
    tool = campaign_tool(catalog.tools.tool("fake"), ("simulator",))
    first = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
        campaign_id="20260101T000000Z-one",
    )
    second = make_campaign(
        catalog,
        cases=(case,),
        tool=tool,
        results=(normalized(case, "fake", "simulator"),),
        campaign_id="20260102T000000Z-two",
    )
    old = publication.build_dataset(catalog, (first,), visibility="local")
    new = publication.build_dataset(catalog, (second,), visibility="local")

    incompatible = dict(old)
    incompatible["schema_version"] = 4
    with pytest.raises(PublicationError, match="incompatible dashboard datasets"):
        merge_datasets(incompatible, new)

    relabelled = json.loads(json.dumps(old))
    relabelled["campaigns"][0]["schema_version"] = 2
    with pytest.raises(PublicationError, match="invalid campaign"):
        merge_datasets(relabelled, new)

    incomplete = dict(old)
    incomplete.pop("metrics")
    with pytest.raises(PublicationError, match="invalid metrics"):
        merge_datasets(incomplete, new)

    invalid_coverage = dict(old)
    invalid_coverage["corpus_coverage"] = {}
    with pytest.raises(PublicationError, match="invalid corpus_coverage"):
        merge_datasets(invalid_coverage, new)

    truncated_metric = json.loads(json.dumps(old))
    truncated_metric["metrics"][0].pop("numerator")
    with pytest.raises(PublicationError, match="invalid metric point"):
        merge_datasets(truncated_metric, new)

    coercive_metric = json.loads(json.dumps(old))
    coercive_metric["metrics"][0]["numerator"] = "1"
    with pytest.raises(PublicationError, match="invalid metric point"):
        merge_datasets(coercive_metric, new)

    numeric_timestamp = json.loads(json.dumps(old))
    numeric_timestamp["metrics"][0]["timestamp"] = 123
    with pytest.raises(PublicationError, match="ISO timestamp"):
        merge_datasets(numeric_timestamp, new)

    duplicate_metric = json.loads(json.dumps(old))
    duplicate_metric["metrics"].append(dict(duplicate_metric["metrics"][0]))
    with pytest.raises(PublicationError, match="duplicate metric points"):
        merge_datasets(duplicate_metric, new)

    mismatched_metric = json.loads(json.dumps(old))
    mismatched_metric["metrics"][0]["profile_id"] = "parser"
    with pytest.raises(PublicationError, match="does not match its campaign"):
        merge_datasets(mismatched_metric, new)

    for field, value in (
        ("numerator", old["metrics"][0]["numerator"] + 1),
        ("corpus_sha", "f" * 64),
        ("repository_commit", "f" * 40),
        ("timestamp", "2026-01-03T00:00:00Z"),
        ("revision", "1800-2017"),
        ("tool_sha", "f" * 40),
    ):
        forged_metric = json.loads(json.dumps(old))
        forged_metric["metrics"][0][field] = value
        with pytest.raises(PublicationError, match="inconsistent"):
            merge_datasets(forged_metric, new)

    forged_complete = json.loads(json.dumps(old))
    forged_complete["metrics"][0].update(
        {
            "numerator": 0,
            "execution_coverage": 0,
            "conforming": 0,
            "unsupported": 1,
        }
    )
    with pytest.raises(PublicationError, match="infrastructure state"):
        merge_datasets(forged_complete, new)

    forged_harness = json.loads(json.dumps(old))
    forged_harness["metrics"][0].update(
        {
            "complete": False,
            "valid": False,
            "infrastructure_state": "harness-error",
        }
    )
    with pytest.raises(PublicationError, match="infrastructure state"):
        merge_datasets(forged_harness, new)

    for field, value in (
        ("started_at", "2026-01-01"),
        ("finished_at", "2026-01-01T00:00:00"),
        ("finished_at", 123),
    ):
        malformed_campaign = json.loads(json.dumps(old))
        malformed_campaign["campaigns"][0][field] = value
        with pytest.raises(PublicationError, match=r"ISO timestamp|UTC timezone"):
            merge_datasets(malformed_campaign, new)

    public_with_local_campaign = json.loads(json.dumps(new))
    public_with_local_campaign["visibility"] = "public"
    with pytest.raises(PublicationError, match="trusted GitHub Actions"):
        merge_datasets(public_with_local_campaign, public_with_local_campaign)

    public = publication.build_dataset(catalog, (), visibility="public")
    with pytest.raises(PublicationError, match="different visibility"):
        merge_datasets(old, public)

    merged = merge_datasets(old, new)
    assert merged["schema_version"] == 5
    assert merged["corpus_coverage"] == new["corpus_coverage"]
    assert {item["id"] for item in merged["campaigns"]} == {first.id, second.id}
    assert merged["generated_from"] == sorted((first.id, second.id))

    collision = json.loads(json.dumps(new))
    collision["campaigns"][0]["id"] = first.id
    collision["campaigns"][0]["repository"]["dirty"] = True
    collision["generated_from"] = [first.id]
    for point in collision["metrics"]:
        point["campaign_id"] = first.id
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
                    observation(attempted_through_phase=Phase.ELABORATE),
                    observation(
                        attempted_through_phase=Phase.SIMULATE,
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
                    observation(attempted_through_phase=Phase.ELABORATE),
                    observation(
                        attempted_through_phase=Phase.SIMULATE,
                        stdout=case.definition.oracle.marker or "",
                    ),
                ),
            ),
        ),
        campaign_id="20260102T000000Z-second",
    )
    first = first.model_copy(
        update={
            "trust": CampaignTrust(
                source="github-actions",
                repository="kleverhq/svtorture",
                workflow_run_id="1",
                checkout_sha=first.repository.commit,
            )
        }
    )
    second = second.model_copy(
        update={
            "trust": CampaignTrust(
                source="github-actions",
                repository="kleverhq/svtorture",
                workflow_run_id="2",
                checkout_sha=second.repository.commit,
            )
        }
    )
    monkeypatch.setattr(publication, "validate_public_campaign", lambda *_args: None)
    monkeypatch.setattr(publication, "_validate_offline_public_campaign", lambda _campaign: None)
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
