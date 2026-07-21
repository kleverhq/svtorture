from __future__ import annotations

from dataclasses import replace

import pytest

from svtorture.catalog import Catalog
from svtorture.evaluator import evaluate, exit_code_for_results, synthetic_result
from svtorture.models import (
    EvidenceMode,
    Phase,
    RawOutcome,
    ReasonCode,
    ResultStatus,
)
from tests.helpers import observation, targeted


@pytest.mark.parametrize(
    ("outcome", "signal", "expected_status", "expected_reason"),
    (
        (RawOutcome.TIMEOUT, None, ResultStatus.INCONCLUSIVE, ReasonCode.TIMEOUT),
        (RawOutcome.SIGNAL, 11, ResultStatus.INCONCLUSIVE, ReasonCode.CRASH),
        (
            RawOutcome.CONTAINER_FAILURE,
            None,
            ResultStatus.HARNESS_ERROR,
            ReasonCode.CONTAINER_FAILURE,
        ),
        (
            RawOutcome.LAUNCH_FAILURE,
            None,
            ResultStatus.HARNESS_ERROR,
            ReasonCode.LAUNCH_FAILURE,
        ),
        (
            RawOutcome.BACKEND_UNAVAILABLE,
            None,
            ResultStatus.SKIPPED_UNAVAILABLE,
            ReasonCode.TOOL_UNAVAILABLE,
        ),
    ),
)
def test_operational_failure_never_satisfies_negative_case(
    catalog: Catalog,
    outcome: RawOutcome,
    signal: int | None,
    expected_status: ResultStatus,
    expected_reason: ReasonCode,
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "parser",
        (
            observation(
                attempted_through_phase=Phase.PARSE,
                outcome=outcome,
                exit_code=None,
                signal=signal,
            ),
        ),
    )
    assert (result.status, result.reason) == (expected_status, expected_reason)
    assert result.status is not ResultStatus.CONFORMING


def test_internal_error_never_satisfies_negative_case(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "parser",
        (
            observation(
                attempted_through_phase=Phase.PARSE,
                exit_code=1,
                diagnostics=(targeted(case),),
                internal_error=True,
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.INTERNAL_ERROR,
    )


@pytest.mark.parametrize("line_offset", (1, 7))
def test_wrong_diagnostic_location_is_not_a_negative_pass(
    catalog: Catalog, line_offset: int
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "parser",
        (
            observation(
                attempted_through_phase=Phase.PARSE,
                exit_code=1,
                diagnostics=(targeted(case, line_offset=line_offset),),
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.OFF_TARGET_DIAGNOSTIC,
    )


def test_unrelated_error_is_not_a_negative_pass(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "parser",
        (observation(attempted_through_phase=Phase.PARSE, exit_code=1, stderr="unparsed failure"),),
    )
    assert (result.status, result.reason) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.MISSING_DIAGNOSTIC,
    )


def test_targeted_rejection_conforms(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "parser",
        (
            observation(
                attempted_through_phase=Phase.PARSE,
                exit_code=1,
                diagnostics=(targeted(case),),
            ),
        ),
    )
    assert result.status is ResultStatus.CONFORMING
    assert result.evidence_mode is EvidenceMode.DIRECT


def test_targeted_cumulative_rejection_conforms(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.ELABORATE,
                exit_code=1,
                diagnostics=(targeted(case),),
            ),
        ),
    )
    assert (result.status, result.evidence_mode) == (
        ResultStatus.CONFORMING,
        EvidenceMode.CUMULATIVE,
    )


def test_later_success_proves_earlier_acceptance(catalog: Catalog) -> None:
    original = catalog.cases["ch22-include-trailing-comment"]
    case = replace(
        original,
        definition=original.definition.model_copy(update={"target_phase": Phase.PARSE}),
    )
    result = evaluate(
        case,
        "tool",
        "simulator",
        (observation(attempted_through_phase=Phase.ELABORATE),),
    )
    assert (result.status, result.evidence_mode) == (
        ResultStatus.CONFORMING,
        EvidenceMode.CUMULATIVE,
    )


def test_unrelated_later_failure_does_not_fail_earlier_acceptance(
    catalog: Catalog,
) -> None:
    original = catalog.cases["ch22-include-trailing-comment"]
    case = replace(
        original,
        definition=original.definition.model_copy(update={"target_phase": Phase.PARSE}),
    )
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.ELABORATE,
                exit_code=1,
                stderr="unrelated elaboration failure",
            ),
        ),
    )
    assert (result.status, result.reason, result.evidence_mode) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.TARGET_PHASE_UNPROVEN,
        EvidenceMode.CUMULATIVE,
    )


def test_success_without_runtime_marker_fails(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    result = evaluate(
        case,
        "tool",
        "simulator",
        (observation(attempted_through_phase=Phase.SIMULATE, exit_code=0),),
    )
    assert (result.status, result.reason) == (
        ResultStatus.NONCONFORMING,
        ReasonCode.MISSING_PASS_MARKER,
    )


def test_runtime_marker_must_be_a_complete_output_line(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    marker = case.definition.oracle.marker
    assert marker is not None
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.SIMULATE,
                exit_code=0,
                stdout=f"prefix-{marker}-suffix",
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.NONCONFORMING,
        ReasonCode.MISSING_PASS_MARKER,
    )


def test_pass_marker_with_nonzero_status_fails(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    assert case.definition.oracle.marker is not None
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.SIMULATE,
                exit_code=1,
                stdout=case.definition.oracle.marker,
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.NONCONFORMING,
        ReasonCode.PASS_MARKER_NONZERO,
    )


def test_wrong_runtime_value_ending_in_fatal_fails(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.SIMULATE,
                exit_code=1,
                stderr="FATAL: wrong value",
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.NONCONFORMING,
        ReasonCode.WRONG_RUNTIME_RESULT,
    )


def test_multiple_runtime_markers_fail(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    marker = case.definition.oracle.marker
    assert marker is not None
    result = evaluate(
        case,
        "tool",
        "simulator",
        (observation(attempted_through_phase=Phase.SIMULATE, stdout=f"{marker}\n{marker}\n"),),
    )
    assert result.reason is ReasonCode.MULTIPLE_PASS_MARKERS


def test_truncated_output_cannot_hide_a_second_runtime_marker(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    marker = case.definition.oracle.marker
    assert marker is not None
    result = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.SIMULATE,
                stdout=marker,
                stdout_truncated=True,
            ),
        ),
    )
    assert (result.status, result.reason) == (
        ResultStatus.INCONCLUSIVE,
        ReasonCode.OUTPUT_TRUNCATED,
    )


def test_exit_policies_keep_conformance_separate_from_infrastructure(
    catalog: Catalog,
) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    nonconforming = evaluate(
        case,
        "tool",
        "simulator",
        (
            observation(
                attempted_through_phase=Phase.SIMULATE,
                exit_code=1,
                stderr="FATAL: wrong value",
            ),
        ),
    )
    harness = synthetic_result(
        case,
        "tool",
        "simulator",
        ResultStatus.HARNESS_ERROR,
        ReasonCode.LAUNCH_FAILURE,
        "launch failure",
    )
    assert exit_code_for_results((nonconforming,), "infra-only") == 0
    assert exit_code_for_results((nonconforming,), "strict") == 1
    assert exit_code_for_results((harness,), "infra-only") == 1
    assert exit_code_for_results((harness,), "always-zero") == 0
