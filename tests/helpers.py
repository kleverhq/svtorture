from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from svtorture.campaign import _selection_payload
from svtorture.catalog import Catalog, LoadedCase
from svtorture.hashing import hash_json
from svtorture.models import (
    Campaign,
    CampaignTool,
    CampaignTrust,
    CapturedStream,
    Diagnostic,
    EvidenceLevel,
    EvidenceMode,
    ImageIdentity,
    ManifestHashes,
    NormalizedResult,
    Phase,
    RawOutcome,
    ReasonCode,
    RepositoryIdentity,
    ResultStatus,
    StageKind,
    StageObservation,
    ToolDefinition,
    ToolSelection,
    phase_reaches,
)

ZERO_SHA = "0" * 40
ONE_SHA = "1" * 40
ZERO_HASH = "0" * 64


def stream(text: str = "", *, truncated: bool = False) -> CapturedStream:
    encoded = text.encode()
    return CapturedStream(
        excerpt=text,
        size_bytes=len(encoded),
        sha256=hashlib.sha256(encoded).hexdigest(),
        truncated=truncated,
    )


def observation(
    *,
    attempted_through_phase: Phase,
    stage_id: str | None = None,
    exit_code: int | None = 0,
    outcome: RawOutcome = RawOutcome.NORMAL_EXIT,
    signal: int | None = None,
    stdout: str = "",
    stderr: str = "",
    diagnostics: tuple[Diagnostic, ...] = (),
    internal_error: bool = False,
    artifact_present: bool | None = None,
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
) -> StageObservation:
    kind = StageKind.RUN if attempted_through_phase is Phase.SIMULATE else StageKind.COMPILE
    return StageObservation(
        stage_id=stage_id or ("run" if kind is StageKind.RUN else "compile"),
        kind=kind,
        attempted_through_phase=attempted_through_phase,
        outcome=outcome,
        exit_code=exit_code,
        signal=signal,
        duration_seconds=0.01,
        stdout=stream(stdout, truncated=stdout_truncated),
        stderr=stream(stderr, truncated=stderr_truncated),
        diagnostics=diagnostics,
        internal_error=internal_error,
        artifact_present=artifact_present,
        portable_argv=("tool", "$CASE/top.sv"),
    )


def targeted(case: LoadedCase, *, line_offset: int = 0) -> Diagnostic:
    assert case.anchor_line is not None
    return Diagnostic(
        severity="error",
        message="target diagnostic",
        source="$CASE/top.sv",
        line=case.anchor_line + line_offset,
        target_case_id=(case.definition.id if line_offset == 0 else None),
    )


def image_identity() -> ImageIdentity:
    return ImageIdentity(
        reference=f"ghcr.io/example/svtorture-tool@sha256:{ZERO_HASH}",
        image_id=f"sha256:{ZERO_HASH}",
        digest=f"sha256:{ZERO_HASH}",
        recipe_sha256=ZERO_HASH,
        base_image=f"ubuntu@sha256:{ZERO_HASH}",
        base_image_digest=f"sha256:{ZERO_HASH}",
        platform="linux/amd64",
    )


def campaign_tool(
    definition: ToolDefinition,
    profile_ids: tuple[str, ...],
) -> CampaignTool:
    selection = None
    image = None
    if definition.execution.value == "docker":
        image = image_identity()
    if definition.distribution.value == "open-source":
        selection = ToolSelection(
            tool=definition.id,
            requested_ref=ONE_SHA,
            resolved_sha=ONE_SHA,
            resolved_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    return CampaignTool(
        definition=definition,
        selection=selection,
        image=image,
        reported_version="test-version",
        profile_ids=profile_ids,
    )


def normalized(
    case: LoadedCase,
    tool_id: str,
    profile_id: str,
    *,
    status: ResultStatus = ResultStatus.CONFORMING,
    reason: ReasonCode = ReasonCode.EXPECTATION_MET,
    observations: tuple[StageObservation, ...] = (),
) -> NormalizedResult:
    if not observations and status in {
        ResultStatus.CONFORMING,
        ResultStatus.NONCONFORMING,
        ResultStatus.INCONCLUSIVE,
    }:
        if case.definition.target_phase is Phase.SIMULATE:
            observations = (
                observation(attempted_through_phase=Phase.ELABORATE),
                observation(
                    attempted_through_phase=Phase.SIMULATE,
                    stdout=case.definition.oracle.marker or "",
                ),
            )
        else:
            observations = (observation(attempted_through_phase=case.definition.target_phase),)
    covering = next(
        (
            item
            for item in observations
            if phase_reaches(item.attempted_through_phase, case.definition.target_phase)
        ),
        None,
    )
    mode = EvidenceMode.NOT_OBSERVED
    if covering is not None:
        mode = (
            EvidenceMode.DIRECT
            if covering.attempted_through_phase is case.definition.target_phase
            else EvidenceMode.CUMULATIVE
        )
    return NormalizedResult(
        schema_version=2,
        case_id=case.definition.id,
        requirement_id=case.definition.primary_requirement,
        tool_id=tool_id,
        profile_id=profile_id,
        target_phase=case.definition.target_phase,
        evidence_mode=mode,
        status=status,
        reason=reason,
        summary="Synthetic deterministic test result.",
        evidence=EvidenceLevel.MANDATORY,
        observations=observations,
    )


def make_campaign(
    catalog: Catalog,
    *,
    cases: tuple[LoadedCase, ...],
    tool: CampaignTool,
    results: tuple[NormalizedResult, ...],
    repository: RepositoryIdentity | None = None,
    trust: CampaignTrust | None = None,
    expected_tool_ids: tuple[str, ...] | None = None,
    missing_tool_ids: tuple[str, ...] = (),
    complete: bool = True,
    campaign_id: str = "20260101T000000Z-test-campaign",
) -> Campaign:
    repository = repository or RepositoryIdentity(commit=ZERO_SHA, dirty=False)
    trust = trust or CampaignTrust(source="local")
    expected = expected_tool_ids or (tool.definition.id,)
    case_ids = tuple(case.definition.id for case in cases)
    selection_hash = hash_json(_selection_payload("test", case_ids, (tool,), expected))
    return Campaign(
        schema_version=5,
        id=campaign_id,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
        repository=repository,
        platform="Linux x86_64",
        selection_name="test",
        case_ids=case_ids,
        cases=catalog.case_identities(cases),
        tools=(tool,),
        expected_tool_ids=expected,
        missing_tool_ids=missing_tool_ids,
        hashes=ManifestHashes(
            requirements=catalog.requirement_manifest_hash(),
            cases=catalog.case_manifest_hash(cases),
            selection=selection_hash,
        ),
        corpus_metrics=catalog.corpus_metrics(),
        results=results,
        complete=complete,
        trust=trust,
    )


def copy_catalog(
    catalog: Catalog,
    *,
    cases: dict[str, LoadedCase] | None = None,
) -> Catalog:
    return Catalog(
        root=Path(catalog.root),
        anchor_index=Path(catalog.anchor_index),
        inventory=catalog.inventory,
        tags=catalog.tags,
        cases=cases or dict(catalog.cases),
        suites=dict(catalog.suites),
        suite_cases=dict(catalog.suite_cases),
        tools=catalog.tools,
    )
