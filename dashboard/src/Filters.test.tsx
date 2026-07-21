import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Filters } from "./Filters";
import { EMPTY_FILTERS, selectedCampaign } from "./model";
import { makeTestDataset } from "./testDataset";

function FilterHarness() {
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
});
