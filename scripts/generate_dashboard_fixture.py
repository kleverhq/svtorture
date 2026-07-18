#!/usr/bin/env python3
"""Build the dashboard's deterministic example dataset.

The checked-in fixture keeps frontend tests and the default static build useful
without requiring a real campaign. ``just fixture`` regenerates the single
canonical JSON file from strict catalog and campaign models; ``--check`` lets CI
detect model or corpus changes that were not reflected in that fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from svtorture.campaign import _selection_payload
from svtorture.catalog import Catalog, load_catalog
from svtorture.evaluator import evaluate, synthetic_result
from svtorture.hashing import hash_json
from svtorture.models import (
    Campaign,
    CampaignTool,
    CampaignTrust,
    CapturedStream,
    Diagnostic,
    EvidenceLevel,
    Expectation,
    ImageIdentity,
    ManifestHashes,
    NormalizedResult,
    RawOutcome,
    ReasonCode,
    RepositoryIdentity,
    ResultStatus,
    StageObservation,
    ToolSelection,
)
from svtorture.publish import build_dataset

ROOT = Path(__file__).resolve().parents[1]
CORPUS_COMMIT = "a" * 40


def _digest(character: str) -> str:
    return f"sha256:{character * 64}"


def _stream(text: str) -> CapturedStream:
    data = text.encode()
    return CapturedStream(
        excerpt=text,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        truncated=False,
    )


def _campaign_tools(catalog: Catalog, generation: int) -> tuple[CampaignTool, ...]:
    tools: list[CampaignTool] = []
    for index, tool_id in enumerate(("slang", "icarus", "verilator"), 1):
        definition = catalog.tools.tool(tool_id)
        profile = definition.headline_profile
        sha_character = f"{index + generation:x}"[-1]
        source_sha = sha_character * 40
        digest_character = f"{index + generation + 6:x}"[-1]
        tools.append(
            CampaignTool(
                definition=definition,
                selection=ToolSelection(
                    tool=tool_id,
                    requested_ref="latest",
                    resolved_sha=source_sha,
                    resolved_at=datetime(2026, 7, 10 + generation, 2, tzinfo=UTC),
                    exact_tags=(f"v{generation}.{index}.0",),
                    nearest_tag=f"v{generation}.{index}.0",
                    default_branch="master",
                ),
                image=ImageIdentity(
                    reference=f"ghcr.io/example/svtorture/{tool_id}@{_digest(digest_character)}",
                    image_id=_digest(digest_character),
                    digest=_digest(digest_character),
                    recipe_sha256=digest_character * 64,
                    base_image=f"ubuntu@{_digest('f')}",
                    base_image_digest=_digest("f"),
                    platform="linux/amd64",
                ),
                reported_version=f"{definition.display_name} fixture-{generation}.{index}",
                profile_ids=(profile.id,),
            )
        )
    return tuple(tools)


def _status_for(
    case_index: int,
    tool_index: int,
    *,
    supported: bool,
    generation: int,
) -> tuple[ResultStatus, ReasonCode]:
    if not supported:
        return ResultStatus.UNSUPPORTED_CAPABILITY, ReasonCode.UNSUPPORTED_PHASE
    selector = (case_index * 3 + tool_index + generation) % 13
    if selector == 0:
        return ResultStatus.NONCONFORMING, ReasonCode.UNEXPECTED_ACCEPT
    if selector == 1:
        return ResultStatus.INCONCLUSIVE, ReasonCode.OFF_TARGET_DIAGNOSTIC
    if generation == 0 and selector == 2:
        return ResultStatus.HARNESS_ERROR, ReasonCode.CONTAINER_FAILURE
    return ResultStatus.CONFORMING, ReasonCode.EXPECTATION_MET


def _result(
    case_id: str,
    catalog: Catalog,
    tool: CampaignTool,
    *,
    case_index: int,
    tool_index: int,
    generation: int,
) -> NormalizedResult:
    loaded = catalog.cases[case_id]
    profile = tool.definition.profile(tool.profile_ids[0])
    supported = loaded.definition.target_phase in profile.phases
    status, reason = _status_for(
        case_index,
        tool_index,
        supported=supported,
        generation=generation,
    )
    if status is ResultStatus.UNSUPPORTED_CAPABILITY:
        result = synthetic_result(
            loaded,
            tool.definition.id,
            profile.id,
            status,
            reason,
            "Fixture profile does not implement the target phase.",
        )
    else:
        marker = loaded.definition.oracle.marker or ""
        target_diagnostic = ()
        stdout = ""
        stderr = ""
        exit_code: int | None = 0
        outcome = RawOutcome.NORMAL_EXIT
        if status is ResultStatus.CONFORMING:
            if loaded.definition.expectation in {
                Expectation.REJECT,
                Expectation.DIAGNOSTIC,
            }:
                assert loaded.anchor_line is not None
                target_diagnostic = (
                    Diagnostic(
                        severity="error",
                        message="Fixture normalized target diagnostic",
                        source="$CASE/top.sv",
                        line=loaded.anchor_line,
                        target_case_id=loaded.definition.id,
                    ),
                )
            if loaded.definition.expectation is Expectation.REJECT:
                exit_code = 1
            elif marker:
                stdout = f"{marker}\n"
        elif status is ResultStatus.NONCONFORMING:
            stderr = "Fixture legal-source rejection or missing required evidence."
            if loaded.definition.expectation is Expectation.REJECT:
                exit_code = 0
            elif loaded.definition.expectation is Expectation.DIAGNOSTIC:
                exit_code = 0
                stdout = f"{marker}\n" if marker else ""
            else:
                exit_code = 1
        elif status is ResultStatus.INCONCLUSIVE:
            outcome = RawOutcome.TIMEOUT
            exit_code = None
        else:
            outcome = RawOutcome.CONTAINER_FAILURE
            exit_code = None
        observations = (
            StageObservation(
                stage_id="run" if loaded.definition.target_phase.value == "simulate" else "compile",
                phase=loaded.definition.target_phase,
                outcome=outcome,
                exit_code=exit_code,
                duration_seconds=0.125 + case_index / 1000,
                stdout=_stream(stdout),
                stderr=_stream(stderr),
                diagnostics=target_diagnostic,
                portable_argv=(
                    "docker",
                    "run",
                    "--network=none",
                    tool.image.reference if tool.image else "missing-image",
                    "tool",
                    "$CASE/top.sv",
                ),
            ),
        )
        result = evaluate(
            loaded,
            tool.definition.id,
            profile.id,
            observations,
        )
        if result.status is not status:
            raise AssertionError(
                f"fixture scenario produced {result.status.value}, expected {status.value}"
            )
    update: dict[str, object] = {
        "evidence": EvidenceLevel.MANDATORY,
        "reproduction_command": (
            f"just reproduce .svtorture/campaigns/"
            f"202607{10 + generation:02d}T030000Z-fixture-{generation}/campaign.json "
            f"{tool.definition.id} {profile.id} {case_id}"
        ),
    }
    if status is ResultStatus.NONCONFORMING:
        update["known_issue"] = "Fixture-only known issue annotation; status remains failing."
    return result.model_copy(update=update)


def _campaign(catalog: Catalog, generation: int) -> Campaign:
    tools = _campaign_tools(catalog, generation)
    selected = tuple(catalog.cases.values())
    case_ids = tuple(case.definition.id for case in selected)
    expected = tuple(tool.definition.id for tool in tools)
    finished = datetime(2026, 7, 10 + generation, 3, tzinfo=UTC)
    results = tuple(
        _result(
            case_id,
            catalog,
            tool,
            case_index=case_index,
            tool_index=tool_index,
            generation=generation,
        )
        for tool_index, tool in enumerate(tools)
        for case_index, case_id in enumerate(case_ids)
    )
    return Campaign(
        schema_version=1,
        id=f"202607{10 + generation:02d}T030000Z-fixture-{generation}",
        started_at=finished - timedelta(minutes=5),
        finished_at=finished,
        repository=RepositoryIdentity(commit=CORPUS_COMMIT, dirty=False),
        platform="Linux x86_64",
        selection_name="all",
        case_ids=case_ids,
        cases=catalog.case_identities(selected),
        tools=tools,
        expected_tool_ids=expected,
        missing_tool_ids=(),
        hashes=ManifestHashes(
            requirements=catalog.requirement_manifest_hash(),
            cases=catalog.case_manifest_hash(selected),
            selection=hash_json(_selection_payload("all", case_ids, tools, expected)),
        ),
        results=results,
        complete=not any(result.status is ResultStatus.HARNESS_ERROR for result in results),
        trust=CampaignTrust(source="local"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when a committed fixture differs.",
    )
    arguments = parser.parse_args()
    catalog = load_catalog(ROOT)
    campaigns = (_campaign(catalog, 0), _campaign(catalog, 1))
    dataset = build_dataset(catalog, campaigns, visibility="local")
    serialized = json.dumps(dataset, indent=2, sort_keys=True) + "\n"
    output = ROOT / "fixtures" / "dashboard" / "data" / "dataset.json"
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != serialized:
            print(f"stale fixture: {output.relative_to(ROOT)}")
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
