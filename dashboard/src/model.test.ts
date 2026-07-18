import { describe, expect, it } from "vitest";

import fixture from "../public/data/dataset.json";
import {
  aggregateStatus,
  EMPTY_FILTERS,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  selectedCampaign,
} from "./model";
import type { Dataset, Result } from "./types";

const dataset = fixture as Dataset;

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
  it("loads the committed strict fixture and filters requirement units", () => {
    const campaign = selectedCampaign(dataset, "");
    const filtered = filterCorpus(
      dataset,
      { ...EMPTY_FILTERS, chapter: "13" },
      campaign,
    );
    expect(filtered.requirements).toHaveLength(1);
    expect(filtered.cases[0]?.id).toBe("ch13-output-copyout-width");
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
