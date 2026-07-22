import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { Filters, type FilterMode } from "./Filters";
import { EMPTY_FILTERS, selectedCampaign } from "./model";
import { makeTestDataset } from "./testDataset";
import type { Dataset } from "./types";

afterEach(cleanup);

function FilterHarness({
  mode = "corpus",
  dataset = makeTestDataset(),
}: {
  mode?: FilterMode;
  dataset?: Dataset;
}) {
  const [filters, setFilters] = useState({
    ...EMPTY_FILTERS,
    status: "conforming",
  });
  return (
    <Filters
      dataset={dataset}
      campaign={selectedCampaign(dataset, "")}
      filters={filters}
      setFilters={setFilters}
      onReset={() => setFilters({ ...EMPTY_FILTERS })}
      mode={mode}
    />
  );
}

describe("Filters", () => {
  it("keeps broad and exact status filters mutually exclusive", () => {
    render(<FilterHarness />);

    const exact = screen.getByLabelText("Exact result") as HTMLSelectElement;
    expect(exact.value).toBe("conforming");

    fireEvent.click(screen.getByRole("button", { name: "Fail 0" }));
    expect(exact.value).toBe("");
    expect(
      screen.getByRole("button", { name: "Fail 0" }).getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("shows side-by-side corpus facets and clear result labels", () => {
    render(<FilterHarness />);

    const tools = within(screen.getByRole("group", { name: "Tools" }));
    const profiles = within(screen.getByRole("group", { name: "Profiles" }));
    fireEvent.click(tools.getByRole("button", { name: "Fake 1" }));
    fireEvent.click(profiles.getByRole("button", { name: "Simulator 1" }));
    expect(
      tools.getByRole("button", { name: "Fake 1" }).getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      profiles
        .getByRole("button", { name: "Simulator 1" })
        .getAttribute("aria-pressed"),
    ).toBe("true");

    const results = within(screen.getByRole("group", { name: "Results" }));
    expect(results.getByRole("button", { name: "Not applicable 0" })).toBeTruthy();
    expect(results.getByRole("button", { name: "Unclear 0" })).toBeTruthy();
    expect(results.getByRole("button", { name: "Infra error 0" })).toBeTruthy();
    expect(results.getByRole("button", { name: "Not evaluated 0" })).toBeTruthy();
    const comparison = within(screen.getByRole("group", { name: "Comparison" }));
    expect(
      comparison.getByRole("button", { name: "Changed since previous" }),
    ).toBeTruthy();
    expect(
      comparison.getByRole("button", { name: "Cross-tool disagreement" }),
    ).toBeTruthy();
  });

  it("shows quick history facets without Advanced filters", () => {
    render(<FilterHarness mode="history" />);

    expect(screen.getByRole("group", { name: "Tools" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Profiles" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Results" })).toBeNull();
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.queryByLabelText("Search")).toBeNull();
  });

  it("offers historical tools that are absent from the selected campaign", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("test dataset has no campaign");
    dataset.metrics.push({
      label: "historical metric",
      revision: "1800-2023",
      tool_id: "historical-tool",
      profile_id: "parser",
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
      infrastructure_state: "available",
      campaign_id: "older-campaign",
      timestamp: campaign.finished_at,
      tool_sha: null,
      exact_tags: [],
      nearest_tag: null,
      reported_version: "historical 1.0",
      image_digest: null,
      repository_commit: campaign.repository.commit,
    });
    dataset.metrics.push({
      ...dataset.metrics[0]!,
      campaign_id: "another-older-campaign",
    });

    render(<FilterHarness mode="history" dataset={dataset} />);

    expect(
      within(screen.getByRole("group", { name: "Tools" })).getByRole("button", {
        name: "Historical Tool 1",
      }),
    ).toBeTruthy();
    expect(
      within(screen.getByRole("group", { name: "Profiles" })).getByRole(
        "button",
        { name: "Parser 1" },
      ),
    ).toBeTruthy();
  });

  it("shows independent headline facets without result filters", () => {
    render(<FilterHarness mode="overview" />);

    expect(screen.getByRole("group", { name: "Tools" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Profiles" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Results" })).toBeNull();
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.queryByLabelText("Search")).toBeNull();
    expect(screen.queryByLabelText("Campaign")).toBeNull();
  });
});
