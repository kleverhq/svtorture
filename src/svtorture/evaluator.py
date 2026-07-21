"""Generic standards-oracle evaluator shared by every tool."""

from __future__ import annotations

import shlex

from svtorture.catalog import LoadedCase
from svtorture.models import (
    EvidenceMode,
    Expectation,
    NormalizedResult,
    RawOutcome,
    ReasonCode,
    ResultStatus,
    StageObservation,
    phase_reaches,
)


def synthetic_result(
    case: LoadedCase,
    tool_id: str,
    profile_id: str,
    status: ResultStatus,
    reason: ReasonCode,
    summary: str,
) -> NormalizedResult:
    return NormalizedResult(
        schema_version=2,
        case_id=case.definition.id,
        requirement_id=case.definition.primary_requirement,
        tool_id=tool_id,
        profile_id=profile_id,
        target_phase=case.definition.target_phase,
        evidence_mode=EvidenceMode.NOT_OBSERVED,
        status=status,
        reason=reason,
        summary=summary,
        evidence=case.definition.evidence,
    )


def _target_observation(
    case: LoadedCase,
    observations: tuple[StageObservation, ...],
) -> StageObservation | None:
    return next(
        (
            observation
            for observation in observations
            if phase_reaches(
                observation.attempted_through_phase,
                case.definition.target_phase,
            )
        ),
        None,
    )


def _evidence_mode(
    case: LoadedCase,
    observations: tuple[StageObservation, ...],
) -> EvidenceMode:
    target = _target_observation(case, observations)
    if target is None:
        return EvidenceMode.NOT_OBSERVED
    if target.attempted_through_phase is case.definition.target_phase:
        return EvidenceMode.DIRECT
    return EvidenceMode.CUMULATIVE


def _result(
    case: LoadedCase,
    tool_id: str,
    profile_id: str,
    status: ResultStatus,
    reason: ReasonCode,
    summary: str,
    observations: tuple[StageObservation, ...],
) -> NormalizedResult:
    reproduction: str | None = None
    if observations:
        reproduction = " ".join(shlex.quote(item) for item in observations[-1].portable_argv)
    return NormalizedResult(
        schema_version=2,
        case_id=case.definition.id,
        requirement_id=case.definition.primary_requirement,
        tool_id=tool_id,
        profile_id=profile_id,
        target_phase=case.definition.target_phase,
        evidence_mode=_evidence_mode(case, observations),
        status=status,
        reason=reason,
        summary=summary,
        evidence=case.definition.evidence,
        observations=observations,
        reproduction_command=reproduction,
    )


def _operational_failure(
    case: LoadedCase,
    tool_id: str,
    profile_id: str,
    observations: tuple[StageObservation, ...],
) -> NormalizedResult | None:
    for observation in observations:
        if observation.outcome is RawOutcome.BACKEND_UNAVAILABLE:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.SKIPPED_UNAVAILABLE,
                ReasonCode.TOOL_UNAVAILABLE,
                "The configured private backend reported that the tool or license is unavailable.",
                observations,
            )
        if observation.outcome is RawOutcome.CONTAINER_FAILURE:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.HARNESS_ERROR,
                ReasonCode.CONTAINER_FAILURE,
                "The configured execution container could not be started reliably.",
                observations,
            )
        if observation.outcome is RawOutcome.LAUNCH_FAILURE:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.HARNESS_ERROR,
                ReasonCode.LAUNCH_FAILURE,
                "The framework could not launch the configured backend.",
                observations,
            )
        if observation.outcome is RawOutcome.TIMEOUT:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.INCONCLUSIVE,
                ReasonCode.TIMEOUT,
                "The tool exceeded the case time bound.",
                observations,
            )
        if observation.outcome is RawOutcome.SIGNAL:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.INCONCLUSIVE,
                ReasonCode.CRASH,
                f"The tool terminated from signal {observation.signal}.",
                observations,
            )
        if observation.internal_error:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.INCONCLUSIVE,
                ReasonCode.INTERNAL_ERROR,
                "The tool reported an internal error.",
                observations,
            )
    if any(
        observation.stdout.truncated or observation.stderr.truncated for observation in observations
    ):
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.INCONCLUSIVE,
            ReasonCode.OUTPUT_TRUNCATED,
            "The bounded observation cannot prove that all relevant output was retained.",
            observations,
        )
    return None


def _targeted(
    observation: StageObservation,
    case_id: str,
    severities: frozenset[str],
) -> bool:
    return any(
        item.target_case_id == case_id and item.severity in severities
        for item in observation.diagnostics
    )


def _marker_count(observation: StageObservation, marker: str) -> int:
    return sum(
        line.strip() == marker
        for excerpt in (observation.stdout.excerpt, observation.stderr.excerpt)
        for line in excerpt.splitlines()
    )


def evaluate(
    case: LoadedCase,
    tool_id: str,
    profile_id: str,
    observations: tuple[StageObservation, ...],
) -> NormalizedResult:
    """Compare observations to the case oracle without tool-specific policy."""

    if not observations:
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.HARNESS_ERROR,
            ReasonCode.INVALID_EXECUTION_PLAN,
            "The execution plan produced no observations.",
            observations,
        )
    operational = _operational_failure(case, tool_id, profile_id, observations)
    if operational is not None:
        return operational
    for observation in observations:
        missing_required_target_artifact = (
            observation.artifact_present is False
            and observation.exit_code == 0
            and (
                case.definition.target_phase.value == "simulate"
                or observation.attempted_through_phase is case.definition.target_phase
            )
        )
        if missing_required_target_artifact:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.NONCONFORMING,
                ReasonCode.MISSING_ARTIFACT,
                "The tool reported success but did not produce the required artifact.",
                observations,
            )

    target = _target_observation(case, observations)
    if target is None:
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.NONCONFORMING,
            ReasonCode.UNEXPECTED_REJECT,
            "The tool did not reach the target phase.",
            observations,
        )
    assert target.exit_code is not None
    cumulative = target.attempted_through_phase is not case.definition.target_phase

    if case.definition.expectation is Expectation.REJECT:
        if target.exit_code == 0:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.NONCONFORMING,
                ReasonCode.UNEXPECTED_ACCEPT,
                "The construct that requires rejection was accepted.",
                observations,
            )
        if _targeted(target, case.definition.id, frozenset({"error", "fatal"})):
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.CONFORMING,
                ReasonCode.EXPECTATION_MET,
                "The tool rejected the intended construct with target evidence.",
                observations,
            )
        reason = (
            ReasonCode.OFF_TARGET_DIAGNOSTIC
            if target.diagnostics
            else ReasonCode.MISSING_DIAGNOSTIC
        )
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.INCONCLUSIVE,
            reason,
            "The rejection lacks evidence tied to the intended source construct.",
            observations,
        )

    if case.definition.expectation is Expectation.DIAGNOSTIC:
        if not _targeted(
            target,
            case.definition.id,
            frozenset({"warning", "error", "fatal"}),
        ):
            reason = (
                ReasonCode.OFF_TARGET_DIAGNOSTIC
                if target.diagnostics
                else ReasonCode.MISSING_DIAGNOSTIC
            )
            if cumulative and target.exit_code != 0:
                return _result(
                    case,
                    tool_id,
                    profile_id,
                    ResultStatus.INCONCLUSIVE,
                    ReasonCode.TARGET_PHASE_UNPROVEN,
                    "A later-capable command failed without proving the target diagnostic.",
                    observations,
                )
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.NONCONFORMING,
                reason,
                "The required diagnostic was not tied to the intended construct.",
                observations,
            )
        marker = case.definition.oracle.marker
        if target.exit_code == 0 and marker is not None:
            count = _marker_count(target, marker)
            if count != 1:
                return _result(
                    case,
                    tool_id,
                    profile_id,
                    ResultStatus.NONCONFORMING,
                    (
                        ReasonCode.MISSING_PASS_MARKER
                        if count == 0
                        else ReasonCode.MULTIPLE_PASS_MARKERS
                    ),
                    "The warning path did not complete with exactly one pass marker.",
                    observations,
                )
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.CONFORMING,
            ReasonCode.EXPECTATION_MET,
            "The required target diagnostic was observed.",
            observations,
        )

    if case.definition.target_phase.value != "simulate":
        if target.exit_code == 0:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.CONFORMING,
                ReasonCode.EXPECTATION_MET,
                (
                    "A later-capable command accepted the case through the target phase."
                    if cumulative
                    else "The target phase accepted the case."
                ),
                observations,
            )
        if cumulative:
            return _result(
                case,
                tool_id,
                profile_id,
                ResultStatus.INCONCLUSIVE,
                ReasonCode.TARGET_PHASE_UNPROVEN,
                "A later-capable command failed without proving rejection at the target phase.",
                observations,
            )
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.NONCONFORMING,
            ReasonCode.UNEXPECTED_REJECT,
            "The target phase unexpectedly rejected a legal case.",
            observations,
        )

    marker = case.definition.oracle.marker
    assert marker is not None
    count = _marker_count(target, marker)
    if target.exit_code != 0:
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.NONCONFORMING,
            (ReasonCode.PASS_MARKER_NONZERO if count else ReasonCode.WRONG_RUNTIME_RESULT),
            "Simulation failed even though the case is required to complete successfully.",
            observations,
        )
    if count == 0:
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.NONCONFORMING,
            ReasonCode.MISSING_PASS_MARKER,
            "Simulation exited successfully without the required pass evidence.",
            observations,
        )
    if count != 1:
        return _result(
            case,
            tool_id,
            profile_id,
            ResultStatus.NONCONFORMING,
            ReasonCode.MULTIPLE_PASS_MARKERS,
            "Simulation emitted the pass marker more than once.",
            observations,
        )
    return _result(
        case,
        tool_id,
        profile_id,
        ResultStatus.CONFORMING,
        ReasonCode.EXPECTATION_MET,
        "Simulation completed with exactly one pass marker after all checks.",
        observations,
    )


def exit_code_for_results(results: tuple[NormalizedResult, ...], policy: str) -> int:
    if policy == "always-zero":
        return 0
    if policy == "infra-only":
        return 1 if any(result.status is ResultStatus.HARNESS_ERROR for result in results) else 0
    if policy == "strict":
        return 1 if any(result.status is not ResultStatus.CONFORMING for result in results) else 0
    raise ValueError(f"unknown exit policy {policy}")
