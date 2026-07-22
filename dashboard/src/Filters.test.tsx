import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { Filters } from "./Filters";
import { EMPTY_FILTERS, selectedCampaign } from "./model";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

function FilterHarness({
  campaignOnly = false,
  showQuickFilters = true,
}: {
  campaignOnly?: boolean;
  showQuickFilters?: boolean;
}) {
  const dataset = makeTestDataset();
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
      campaignOnly={campaignOnly}
      showQuickFilters={showQuickFilters}
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

  it("uses clear result and comparison labels", () => {
    render(<FilterHarness />);

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

  it("can hide result filters outside Requirements and Cases", () => {
    render(<FilterHarness showQuickFilters={false} />);

    expect(screen.queryByRole("group", { name: "Results" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Comparison" })).toBeNull();
    expect(screen.getByLabelText("Search")).toBeTruthy();
  });

  it("shows independent tool and profile facets in the overview", () => {
    render(<FilterHarness campaignOnly />);

    expect(screen.getByLabelText("Campaign")).toBeTruthy();
    expect(screen.getByLabelText("Campaign date")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Clear filters" })).toBeTruthy();
    expect(screen.queryByLabelText("Search")).toBeNull();
    expect(screen.queryByLabelText("Tool / profile")).toBeNull();
    expect(screen.queryByRole("button", { name: "Fail 0" })).toBeNull();

    const tools = within(screen.getByRole("group", { name: "Tools" }));
    const profiles = within(screen.getByRole("group", { name: "Profiles" }));
    expect(tools.getByRole("button", { name: "All 1" })).toBeTruthy();
    fireEvent.click(tools.getByRole("button", { name: "Fake 1" }));
    expect(
      tools.getByRole("button", { name: "Fake 1" }).getAttribute("aria-pressed"),
    ).toBe("true");
    fireEvent.click(profiles.getByRole("button", { name: "Simulator 1" }));
    expect(
      profiles
        .getByRole("button", { name: "Simulator 1" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });
});
