"""Requirement-weighted headline metric and detailed breakdown."""

from __future__ import annotations

from collections import defaultdict

from svtorture.catalog import Catalog, LoadedCase
from svtorture.models import (
    Applicability,
    Campaign,
    CoverageState,
    EvidenceLevel,
    MetricBreakdown,
    Normativity,
    ResultStatus,
    Testability,
    ToolDefinition,
    ToolProfile,
)


def compute_metric(
    catalog: Catalog,
    campaign: Campaign,
    tool: ToolDefinition,
    profile: ToolProfile,
) -> MetricBreakdown:
    """Count normative requirements once; every mandatory variant must conform."""

    scoped: dict[str, list[LoadedCase]] = defaultdict(list)
    for case_id in campaign.case_ids:
        loaded = catalog.cases[case_id]
        definition = loaded.definition
        requirement = catalog.requirements[definition.primary_requirement]
        if (
            definition.target_phase in profile.phases
            and definition.evidence is EvidenceLevel.MANDATORY
            and definition.revision_applicability[profile.standard_revision]
            in {
                Applicability.APPLICABLE,
                Applicability.SAME_RULE_DIFFERENT_CLAUSE,
            }
            and requirement.revision_applicability[profile.standard_revision].status
            in {
                Applicability.APPLICABLE,
                Applicability.SAME_RULE_DIFFERENT_CLAUSE,
            }
            and requirement.normativity is Normativity.NORMATIVE
            and requirement.testability is Testability.TESTABLE
            and requirement.coverage_state is CoverageState.COVERED
        ):
            scoped[requirement.id].append(loaded)

    by_key = {
        (result.case_id, result.tool_id, result.profile_id): result for result in campaign.results
    }
    conforming = nonconforming = inconclusive = unsupported = execution = 0
    harness = False
    numerator = 0
    for requirement_id, cases in scoped.items():
        del requirement_id
        results = [by_key.get((case.definition.id, tool.id, profile.id)) for case in cases]
        present = [result for result in results if result is not None]
        executed_statuses = {
            ResultStatus.CONFORMING,
            ResultStatus.NONCONFORMING,
            ResultStatus.INCONCLUSIVE,
            ResultStatus.HARNESS_ERROR,
        }
        if len(present) == len(cases) and all(
            result.status in executed_statuses for result in present
        ):
            execution += 1
        statuses = {result.status for result in present}
        if ResultStatus.HARNESS_ERROR in statuses:
            harness = True
        if len(present) == len(cases) and statuses == {ResultStatus.CONFORMING}:
            numerator += 1
            conforming += 1
        elif ResultStatus.NONCONFORMING in statuses:
            nonconforming += 1
        elif statuses & {ResultStatus.INCONCLUSIVE, ResultStatus.HARNESS_ERROR}:
            inconclusive += 1
        else:
            unsupported += 1
    denominator = len(scoped)
    profile_available = (
        tool.id in campaign.expected_tool_ids and tool.id not in campaign.missing_tool_ids
    )
    complete = profile_available and not harness and execution == denominator
    if harness:
        infrastructure_state = "harness-error"
    elif not profile_available:
        infrastructure_state = "missing-tool"
    elif execution != denominator:
        infrastructure_state = "incomplete-evidence"
    else:
        infrastructure_state = "valid"
    return MetricBreakdown(
        label="Verified support in the covered corpus",
        revision=profile.standard_revision,
        tool_id=tool.id,
        profile_id=profile.id,
        numerator=numerator,
        denominator=denominator,
        corpus_sha=campaign.hashes.cases,
        complete=complete,
        valid=not harness,
        corpus_coverage=denominator,
        execution_coverage=execution,
        conforming=conforming,
        nonconforming=nonconforming,
        inconclusive=inconclusive,
        unsupported=unsupported,
        infrastructure_state=infrastructure_state,
    )
