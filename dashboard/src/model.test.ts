import { describe, expect, it } from "vitest";

import {
  aggregateStatus,
  EMPTY_FILTERS,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  selectedCampaign,
} from "./model";
import { makeTestDataset } from "./testDataset";
import type { Result } from "./types";

const dataset = makeTestDataset();

describe("URL-backed filters", () => {
  it("round-trips meaningful filter state", () => {
    const value = {
      ...EMPTY_FILTERS,
      search: "copy-out",
      chapter: "13",
      changed: true,
      disagreement: true,
    };
    const encoded = filtersToSearch(value, "evidence");
    expect(encoded).toContain("view=evidence");
    expect(filtersFromSearch(encoded)).toEqual(value);
  });
});

describe("requirements model", () => {
  it("filters requirement units from a small local dataset", () => {
    const campaign = selectedCampaign(dataset, "");
    const filtered = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, chapter: "13" },
      campaign,
    );
    expect(filtered.requirements).toHaveLength(1);
    expect(filtered.cases[0]?.id).toBe("ch13-output-copyout-width");
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

  it("uses a failure-safe aggregate precedence", () => {
    const base = {
      case_id: "case",
      requirement_id: "requirement",
      tool_id: "tool",
      profile_id: "profile",
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
