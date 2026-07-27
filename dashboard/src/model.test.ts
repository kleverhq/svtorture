import { describe, expect, it } from "vitest";

import {
  aggregateStatus,
  campaignsInDateRange,
  changedCaseKeys,
  compareCampaigns,
  EMPTY_FILTERS,
  corpusTrendPointKey,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  selectedCampaign,
  toolTrendPointKey,
  trendRangeBounds,
  trendStateFromSearch,
  standardLocationLabel,
  statusGroup,
} from "./model";
import { makeTestDataset } from "./testDataset";
import type { Campaign, MetricPoint, Result } from "./types";

const dataset = makeTestDataset();

describe("URL-backed filters", () => {
  it("round-trips meaningful filter state", () => {
    const value = {
      ...EMPTY_FILTERS,
      search: "copy-out",
      part: "13",
      statusGroup: "fail",
      requirement: "SV-2023-13-OUTPUT-COPYOUT",
      tool: "fake",
      profile: "simulator",
      dateFrom: "2026-01-01",
      dateTo: "2026-12-31",
      caseId: "ch13-output-copyout-width",
      requirementId: "SV-2023-13-OUTPUT-COPYOUT",
      changed: true,
      disagreement: true,
    };
    const encoded = filtersToSearch(value, "evidence");
    expect(encoded).toContain("view=evidence");
    expect(filtersFromSearch(encoded)).toEqual(value);
  });

  it("round-trips strict trend state and rejects unknown values", () => {
    const point = "corpus:campaign:cases";
    const encoded = filtersToSearch(EMPTY_FILTERS, "trends", {
      kind: "density",
      range: "six-months",
      point,
      parts: ["chapter:5", "annex:A"],
    });

    expect(encoded).toContain("trend=density");
    expect(encoded).toContain("trendRange=six-months");
    expect(encoded).toContain("trendPoint=corpus%3Acampaign%3Acases");
    expect(encoded).toContain("chapter=chapter%3A5");
    expect(encoded).toContain("chapter=annex%3AA");
    expect(filtersFromSearch(encoded).part).toBe("");
    expect(trendStateFromSearch(encoded)).toEqual({
      kind: "density",
      range: "six-months",
      point,
      parts: ["chapter:5", "annex:A"],
    });
    expect(
      trendStateFromSearch(
        "?trend=unknown&trendRange=forever&chapter=invalid&chapter=annex:Z",
      ),
    ).toEqual({
      kind: "pass-rate",
      range: "all",
      point: "",
      parts: [],
    });
    for (const kind of ["pass-rate", "coverage", "density"] as const) {
      const search = filtersToSearch(EMPTY_FILTERS, "trends", {
        kind,
        range: "month",
        point: "",
        parts: [],
      });
      expect(trendStateFromSearch(search).kind).toBe(kind);
    }
    expect(filtersToSearch(EMPTY_FILTERS, "trends")).toBe("?view=trends");
    expect(trendStateFromSearch("?view=trends").range).toBe("all");
    expect(filtersFromSearch("?chapter=13").part).toBe("");
    const mixed = filtersToSearch(
      { ...EMPTY_FILTERS, part: "13" },
      "trends",
      { kind: "coverage", range: "month", point: "", parts: ["annex:A"] },
    );
    expect(filtersFromSearch(mixed).part).toBe("13");
    expect(trendStateFromSearch(mixed).parts).toEqual(["annex:A"]);
    expect(
      filtersToSearch(EMPTY_FILTERS, "overview", {
        kind: "coverage",
        range: "week",
        point,
        parts: ["chapter:5"],
      }),
    ).toBe("?view=overview");
  });

  it("builds UTC daily trend windows with safe calendar subtraction", () => {
    const point = {
      campaign_id: "campaign",
      tool_id: "tool",
      profile_id: "profile",
      timestamp: "2025-01-15T12:30:00Z",
    } as MetricPoint;
    const now = new Date("2027-03-31T18:45:00Z");

    expect(trendRangeBounds([point], "week", now)).toMatchObject({
      domainStart: Date.parse("2025-01-15T00:00:00Z"),
      domainEnd: Date.parse("2027-04-01T00:00:00Z"),
      rangeStart: Date.parse("2027-03-25T00:00:00Z"),
    });
    expect(trendRangeBounds([point], "month", now).rangeStart).toBe(
      Date.parse("2027-02-28T00:00:00Z"),
    );
    expect(trendRangeBounds([point], "three-months", now).rangeStart).toBe(
      Date.parse("2026-12-31T00:00:00Z"),
    );
    expect(trendRangeBounds([point], "six-months", now).rangeStart).toBe(
      Date.parse("2026-09-30T00:00:00Z"),
    );
    expect(trendRangeBounds([point], "year", now).rangeStart).toBe(
      Date.parse("2026-03-31T00:00:00Z"),
    );
    expect(trendRangeBounds([point], "all", now).rangeStart).toBe(
      Date.parse("2025-01-15T00:00:00Z"),
    );
  });

  it("starts all-time trends at the project boundary when data is newer", () => {
    const bounds = trendRangeBounds([], "all", new Date("2026-07-22T12:00:00Z"));
    expect(bounds.domainStart).toBe(Date.parse("2026-07-01T00:00:00Z"));
    expect(bounds.rangeStart).toBe(bounds.domainStart);
    expect(
      toolTrendPointKey({
        campaign_id: "campaign",
        tool_id: "tool",
        profile_id: "profile",
      } as MetricPoint),
    ).toBe("tool:campaign:tool:profile");
    expect(corpusTrendPointKey(dataset.campaigns[0]!, "requirements")).toBe(
      "corpus:20260101T000000Z-test:requirements",
    );
  });
});

describe("requirements model", () => {
  it("filters campaigns by an inclusive range and falls back to the latest match", () => {
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("test dataset has no campaign");
    const older = {
      ...seed,
      id: "20260101T000000Z-older",
      finished_at: "2026-01-01T23:59:59Z",
    } satisfies Campaign;
    const newer = {
      ...seed,
      id: "20260102T000000Z-newer",
      finished_at: "2026-01-02T00:00:01Z",
    } satisfies Campaign;
    const extended = { ...dataset, campaigns: [older, newer] };

    expect(campaignsInDateRange(extended, "2026-01-01", "2026-01-01")).toEqual([
      older,
    ]);
    expect(
      selectedCampaign(extended, newer.id, "2026-01-01", "2026-01-01")?.id,
    ).toBe(older.id);
    expect(selectedCampaign(extended, "")?.id).toBe(newer.id);
  });

  it("filters requirement units from a small local dataset", () => {
    const campaign = selectedCampaign(dataset, "");
    const filtered = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, part: "13" },
      campaign,
    );
    expect(filtered.requirements).toHaveLength(1);
    expect(filtered.cases[0]?.id).toBe("ch13-output-copyout-width");
  });

  it("filters and labels annex requirements", () => {
    const annexDataset = makeTestDataset();
    const requirement = annexDataset.requirements[0];
    if (!requirement) throw new Error("test dataset has no requirement");
    requirement.part = "A";
    requirement.clause = "A.1";

    const filtered = filterCorpus(
      annexDataset,
      { ...EMPTY_FILTERS, part: "A", clause: "A" },
      selectedCampaign(annexDataset, ""),
    );

    expect(filtered.requirements).toEqual([requirement]);
    expect(filtered.cases).toHaveLength(1);
    expect(standardLocationLabel(requirement.clause)).toBe("Annex A.1");
    expect(standardLocationLabel("13.5")).toBe("Clause 13.5");
  });

  it("searches exact annotated-standard anchors", () => {
    const filtered = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, search: "[2023:10.8:L007:p260]" },
      selectedCampaign(dataset, ""),
    );
    expect(filtered.requirements.map((requirement) => requirement.id)).toEqual([
      "SV-2023-13-OUTPUT-COPYOUT",
    ]);
    expect(filtered.cases.map((testCase) => testCase.id)).toEqual([
      "ch13-output-copyout-width",
    ]);
  });

  it("filters Cases by exact primary or related Requirement links", () => {
    const extended = makeTestDataset();
    const original = extended.requirements[0];
    const linkedCase = extended.cases[0];
    if (!original || !linkedCase) throw new Error("incomplete test dataset");
    const related = {
      ...original,
      id: "SV-2023-05-RELATED-FILTER",
      part: "5",
      clause: "5.4",
      summary: "Related-only filter target",
    };
    const unrelatedCase = {
      ...linkedCase,
      id: "ch13-unrelated-to-exact-filter",
      title: "Unrelated case",
      related_requirements: [],
    };
    linkedCase.related_requirements = [related.id];
    extended.requirements.push(related);
    extended.cases.push(unrelatedCase);

    const filtered = filterCorpus(
      extended,
      { ...EMPTY_FILTERS, requirement: related.id },
      selectedCampaign(extended, ""),
    );

    expect(filtered.requirements.map((requirement) => requirement.id)).toEqual([
      related.id,
    ]);
    expect(filtered.cases.map((testCase) => testCase.id)).toEqual([
      linkedCase.id,
    ]);
  });

  it("derives case coverage and keeps uncovered requirements visible", () => {
    const seed = dataset.requirements[0];
    if (!seed) throw new Error("test dataset has no requirements");
    const uncovered = {
      ...seed,
      id: "SV-2023-13-UNMAPPED-TEST",
      summary: "Test requirement without a mapped case.",
    };
    const extended = {
      ...dataset,
      requirements: [...dataset.requirements, uncovered],
    };
    const filtered = filterCorpus(
      extended,
      { ...EMPTY_FILTERS, casePresence: "without-cases" },
      selectedCampaign(extended, ""),
    );
    expect(filtered.requirements.map((requirement) => requirement.id)).toEqual([
      uncovered.id,
    ]);
    expect(filtered.cases).toHaveLength(0);
  });

  it("filters by broad status group without losing exact statuses", () => {
    const campaign = selectedCampaign(dataset, "");
    const passing = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, statusGroup: "pass" },
      campaign,
    );
    const failing = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, statusGroup: "fail" },
      campaign,
    );
    expect(passing.cases).toHaveLength(1);
    expect(failing.cases).toHaveLength(0);
  });

  it("maps exact statuses into six scan-level groups", () => {
    expect(statusGroup("conforming")).toBe("pass");
    expect(statusGroup("nonconforming")).toBe("fail");
    expect(statusGroup("unsupported-capability")).toBe("not-applicable");
    expect(statusGroup("unsupported-revision")).toBe("not-applicable");
    expect(statusGroup("not-applicable")).toBe("not-applicable");
    expect(statusGroup("inconclusive")).toBe("unclear");
    expect(statusGroup("harness-error")).toBe("infra");
    expect(statusGroup("skipped-unavailable")).toBe("not-evaluated");
    expect(statusGroup("not-run")).toBe("not-evaluated");
  });

  it("compares only campaigns with the same tool profiles", () => {
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("test dataset has no campaign");
    const prior = {
      ...seed,
      id: "20260101T000000Z-prior",
      finished_at: "2026-01-01T00:00:01Z",
      results: seed.results.map((result) => ({
        ...result,
        status: "nonconforming" as const,
      })),
    } satisfies Campaign;
    const current = {
      ...seed,
      id: "20260102T000000Z-current",
      started_at: "2026-01-02T00:00:00Z",
      finished_at: "2026-01-02T00:00:01Z",
    } satisfies Campaign;
    const unrelated = {
      ...prior,
      id: "20260101T120000Z-unrelated",
      finished_at: "2026-01-01T12:00:01Z",
      tools: [],
      results: [],
    } satisfies Campaign;
    const comparison = compareCampaigns(
      { ...dataset, campaigns: [prior, unrelated, current] },
      current,
    );
    expect(comparison.previousCampaignId).toBe(prior.id);
    expect(comparison.newPasses.map((change) => change.caseId)).toEqual([
      "ch13-output-copyout-width",
    ]);
    expect(comparison.regressions).toHaveLength(0);
    expect(
      changedCaseKeys({ ...dataset, campaigns: [prior, unrelated, current] }, current),
    ).toEqual(new Set(["ch13-output-copyout-width"]));
    expect(
      changedCaseKeys(
        { ...dataset, campaigns: [{ ...prior, results: [] }, current] },
        current,
      ),
    ).toEqual(new Set());
  });

  it("does not compare campaigns across a phase-scope boundary", () => {
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("test dataset has no campaign");
    const prior = {
      ...seed,
      id: "20260101T000000Z-prior",
      finished_at: "2026-01-01T00:00:01Z",
    } satisfies Campaign;
    const current = {
      ...seed,
      id: "20260102T000000Z-current",
      started_at: "2026-01-02T00:00:00Z",
      finished_at: "2026-01-02T00:00:01Z",
      tools: seed.tools.map((tool) => ({
        ...tool,
        definition: {
          ...tool.definition,
          profiles: tool.definition.profiles.map((profile) => ({
            ...profile,
            direct_phases: ["elaborate", "simulate"],
          })),
        },
      })),
    } satisfies Campaign;

    const comparison = compareCampaigns(
      { ...dataset, campaigns: [prior, current] },
      current,
    );
    expect(comparison.previousCampaignId).toBeUndefined();
  });

  it("reports tool, corpus, and denominator boundaries", () => {
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("test dataset has no campaign");
    const prior = {
      ...seed,
      id: "20260101T000000Z-prior",
      finished_at: "2026-01-01T00:00:01Z",
    } satisfies Campaign;
    const current = {
      ...seed,
      id: "20260102T000000Z-current",
      started_at: "2026-01-02T00:00:00Z",
      finished_at: "2026-01-02T00:00:01Z",
      hashes: { ...seed.hashes, cases: "1".repeat(64) },
      tools: seed.tools.map((tool) => ({ ...tool, reported_version: "test-tool 2.0" })),
    } satisfies Campaign;
    const baseMetric = {
      label: "verified support in the covered corpus",
      revision: "1800-2023",
      tool_id: "fake",
      profile_id: "simulator",
      numerator: 1,
      denominator: 1,
      corpus_sha: "0".repeat(64),
      complete: true,
      valid: true,
      corpus_coverage: 1,
      execution_coverage: 1,
      conforming: 1,
      nonconforming: 0,
      inconclusive: 0,
      unsupported: 0,
      infrastructure_state: "complete",
      timestamp: prior.finished_at,
      exact_tags: [],
      repository_commit: "0".repeat(40),
    };
    const metrics = [
      { ...baseMetric, campaign_id: prior.id },
      { ...baseMetric, campaign_id: current.id, denominator: 2 },
    ] satisfies MetricPoint[];
    const comparison = compareCampaigns(
      { ...dataset, campaigns: [prior, current], metrics },
      current,
    );
    expect(comparison.toolRevisionChanges).toHaveLength(1);
    expect(comparison.corpusChanged).toBe(true);
    expect(comparison.denominatorChanged).toBe(true);
  });

  it("classifies a loss of a verified pass as a regression", () => {
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("test dataset has no campaign");
    const prior = {
      ...seed,
      id: "20260101T000000Z-prior",
      finished_at: "2026-01-01T00:00:01Z",
    } satisfies Campaign;
    const current = {
      ...seed,
      id: "20260102T000000Z-current",
      started_at: "2026-01-02T00:00:00Z",
      finished_at: "2026-01-02T00:00:01Z",
      results: seed.results.map((result) => ({
        ...result,
        status: "nonconforming" as const,
      })),
    } satisfies Campaign;
    const comparison = compareCampaigns(
      { ...dataset, campaigns: [prior, current] },
      current,
    );
    expect(comparison.regressions).toHaveLength(1);
    expect(comparison.newPasses).toHaveLength(0);
  });

  it("uses a failure-safe aggregate precedence", () => {
    const base = {
      case_id: "case",
      requirement_id: "requirement",
      tool_id: "tool",
      profile_id: "profile",
      target_phase: "simulate",
      evidence_mode: "direct" as const,
      reason: "test",
      summary: "test",
      evidence: "mandatory",
      observations: [],
    };
    const pass = { ...base, status: "conforming" } as Result;
    const fail = { ...base, status: "nonconforming" } as Result;
    const harness = { ...base, status: "harness-error" } as Result;
    expect(aggregateStatus([pass, fail])).toBe("nonconforming");
    expect(aggregateStatus([pass, harness])).toBe("harness-error");
    expect(aggregateStatus([])).toBe("not-run");
  });
});
