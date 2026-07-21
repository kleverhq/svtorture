import type { Dataset } from "./types";

const HASH = "0".repeat(64);

export function makeTestDataset(): Dataset {
  const requirement = {
    id: "SV-2023-13-OUTPUT-COPYOUT",
    standard_revision: "1800-2023",
    chapter: 13,
    clause: "13.5",
    anchors: [
      "[2023:13.5:P005:p348]",
      "[2023:10.8:L007:p260]",
      "[2023:6.11.2:P004:p109-110]",
    ],
    summary:
      "A subroutine output is copied to its actual when the subroutine returns, using assignment conversion.",
    related_clauses: ["4.9.7", "6.11.2", "10.8"],
    tags: ["copy-out", "output", "subroutine"],
    revision_applicability: {
      "1800-2012": { status: "applicable", clause: "13.5" },
      "1800-2017": { status: "applicable", clause: "13.5" },
      "1800-2023": { status: "applicable", clause: "13.5" },
    },
  };
  const testCase = {
    id: "ch13-output-copyout-width",
    title: "Output copy-out converts to the actual width",
    description: "A small deterministic output copy-out boundary.",
    primary_requirement: requirement.id,
    related_requirements: [],
    standard_revision: "1800-2023",
    revision_applicability: {
      "1800-2012": "applicable",
      "1800-2017": "applicable",
      "1800-2023": "applicable",
    },
    target_phase: "simulate",
    expectation: "accept",
    evidence: "mandatory",
    sources: ["top.sv"],
    top: "top",
    defines: [],
    include_dirs: [],
    runtime_args: [],
    oracle: {
      kind: "runtime-pass-marker",
      marker: "SVTORTURE_PASS:ch13-output-copyout-width",
    },
    tags: ["copy-out", "output", "subroutine"],
    content_sha256: HASH,
  };
  const tool = {
    definition: {
      id: "fake",
      display_name: "Test tool",
      distribution: "internal",
      execution: "docker",
      ci: true,
      publish: false,
      profiles: [
        {
          id: "simulator",
          phase_ceiling: "simulate",
          direct_phases: ["preprocess", "parse", "elaborate", "simulate"],
          headline: true,
          standard_revision: "1800-2023",
          effective_language: "test protocol",
        },
      ],
    },
    profile_ids: ["simulator"],
    reported_version: "test-tool 1.0",
  };
  const campaign = {
    id: "20260101T000000Z-test",
    started_at: "2026-01-01T00:00:00Z",
    finished_at: "2026-01-01T00:00:01Z",
    repository: { commit: "0".repeat(40), dirty: false },
    platform: "test",
    selection_name: "test",
    case_ids: [testCase.id],
    tools: [tool],
    expected_tool_ids: [tool.definition.id],
    missing_tool_ids: [],
    hashes: {
      requirements: HASH,
      cases: HASH,
      selection: HASH,
    },
    results: [
      {
        case_id: testCase.id,
        requirement_id: requirement.id,
        tool_id: tool.definition.id,
        profile_id: "simulator",
        target_phase: "simulate",
        evidence_mode: "direct" as const,
        status: "conforming" as const,
        reason: "expectation-met",
        summary: "The expected result was observed.",
        evidence: "mandatory",
        observations: [],
      },
    ],
    complete: true,
    trust: { source: "local" },
  };
  return {
    schema_version: 2,
    generated_from: [campaign.id],
    visibility: "local",
    requirements: [requirement],
    cases: [testCase],
    campaigns: [campaign],
    metrics: [],
  };
}
