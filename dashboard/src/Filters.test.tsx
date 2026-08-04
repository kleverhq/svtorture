import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { Filters, type FilterMode } from "./Filters";
import { EMPTY_FILTERS, selectedCampaign, type TrendKind } from "./model";
import { makeTestDataset } from "./testDataset";
import type { Dataset } from "./types";

afterEach(cleanup);

function FilterHarness({
  mode = "cases",
  dataset = makeTestDataset(),
  trendKind = "pass-rate",
  requirement = "",
}: {
  mode?: FilterMode;
  dataset?: Dataset;
  trendKind?: TrendKind;
  requirement?: string;
}) {
  const [filters, setFilters] = useState({
    ...EMPTY_FILTERS,
    status: "conforming",
    requirement,
  });
  const [selectedParts, setSelectedParts] = useState<string[]>([]);
  return (
    <Filters
      dataset={dataset}
      campaign={selectedCampaign(dataset, "")}
      filters={filters}
      setFilters={setFilters}
      onReset={() => setFilters({ ...EMPTY_FILTERS })}
      mode={mode}
      trendKind={mode === "trends" ? trendKind : undefined}
      standardParts={dataset.corpus_coverage.requirements.breakdown}
      selectedParts={selectedParts}
      onSelectedPartsChange={setSelectedParts}
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

  it("keeps quick filters but removes Advanced filters from Requirements", () => {
    render(<FilterHarness mode="requirements" />);

    expect(screen.getByRole("group", { name: "Tools" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Profiles" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Results" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Comparison" })).toBeTruthy();
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.queryByLabelText("Search")).toBeNull();
  });

  it("expands a multi-select Requirement tag cloud", () => {
    render(<FilterHarness mode="requirements" />);

    const disclosure = screen.getByText("Tags");
    expect(disclosure.closest("details")?.open).toBe(false);
    fireEvent.click(disclosure);
    const cloud = within(screen.getByRole("group", { name: "Requirement tags" }));
    const copyOut = cloud.getByRole("button", { name: /copy-out/ });
    const output = cloud.getByRole("button", { name: /output/ });
    fireEvent.click(copyOut);
    fireEvent.click(output);

    expect(copyOut.getAttribute("aria-pressed")).toBe("true");
    expect(output.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("2 selected")).toBeTruthy();
  });

  it("opens Advanced filters for an exact Requirement on Cases", () => {
    const dataset = makeTestDataset();
    const requirement = dataset.requirements[0];
    if (!requirement) throw new Error("incomplete test dataset");

    const view = render(
      <FilterHarness dataset={dataset} requirement={requirement.id} />,
    );

    const select = screen.getByLabelText("Requirement") as HTMLSelectElement;
    expect(select.value).toBe(requirement.id);
    const summary = screen.getByText("Advanced filters");
    expect(summary.closest("details")?.open).toBe(true);

    fireEvent.click(summary);
    view.rerender(
      <FilterHarness
        dataset={dataset}
        requirement={requirement.id}
        mode="overview"
      />,
    );
    view.rerender(
      <FilterHarness dataset={dataset} requirement={requirement.id} />,
    );
    expect(screen.getByText("Advanced filters").closest("details")?.open).toBe(true);
  });

  it("shows quick trend facets without Advanced filters", () => {
    render(<FilterHarness mode="trends" />);

    expect(screen.getByRole("group", { name: "Tools" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Profiles" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Results" })).toBeNull();
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.queryByLabelText("Search")).toBeNull();
  });

  it("replaces tool facets with an all-default chapter and annex multiselect", () => {
    render(<FilterHarness mode="trends" trendKind="coverage" />);

    expect(screen.queryByRole("group", { name: "Tools" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Profiles" })).toBeNull();
    const disclosure = screen.getByLabelText("Chapter and annex filter: All 3");
    fireEvent.click(disclosure);
    const chapters = within(screen.getByRole("group", { name: "Standard parts" }));
    expect((chapters.getByLabelText("All") as HTMLInputElement).checked).toBe(true);

    fireEvent.click(chapters.getByLabelText(/Chapter 5/));
    fireEvent.click(chapters.getByLabelText(/Annex A/));
    expect(screen.getByText("2 selected")).toBeTruthy();
    expect((chapters.getByLabelText("All") as HTMLInputElement).checked).toBe(false);
    expect((chapters.getByLabelText(/Chapter 5/) as HTMLInputElement).checked).toBe(
      true,
    );
    expect((chapters.getByLabelText(/Annex A/) as HTMLInputElement).checked).toBe(
      true,
    );

    const multiselect = disclosure.closest("details") as HTMLDetailsElement;
    expect(multiselect.open).toBe(true);
    fireEvent.pointerDown(document.body);
    expect(multiselect.open).toBe(false);

    fireEvent.click(disclosure);
    expect(multiselect.open).toBe(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(multiselect.open).toBe(false);
    expect(document.activeElement).toBe(disclosure);

    fireEvent.click(disclosure);
    fireEvent.click(chapters.getByLabelText("All"));
    expect(screen.getByText("All 3")).toBeTruthy();
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

    render(<FilterHarness mode="trends" dataset={dataset} />);

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

  it("shows quick Campaigns facets across all records without Advanced filters", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const tool = campaign?.tools[0];
    const profile = tool?.definition.profiles[0];
    if (!campaign || !tool || !profile) throw new Error("incomplete test dataset");
    dataset.campaigns.push({
      ...campaign,
      id: "older-campaign",
      finished_at: "2026-01-01T00:00:00Z",
      tools: [
        {
          ...tool,
          definition: {
            ...tool.definition,
            id: "historical-tool",
            display_name: "Historical Tool",
            profiles: [{ ...profile, id: "parser" }],
          },
          profile_ids: ["parser"],
        },
      ],
    });

    render(<FilterHarness mode="campaigns" dataset={dataset} />);

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
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.queryByLabelText("Search")).toBeNull();
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
