import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CorpusCoverage } from "./CorpusCoverage";
import { makeTestDataset } from "./testDataset";

describe("CorpusCoverage", () => {
  it("shows compact requirement metrics and an expandable part breakdown", () => {
    const metric = makeTestDataset().corpus_coverage.requirements;
    render(<CorpusCoverage kind="requirements" metric={metric} />);

    const region = screen.getByRole("region", {
      name: "Requirement corpus coverage",
    });
    const summary = region.querySelector("summary");
    const details = region.querySelector("details");
    if (!summary || !details) throw new Error("coverage disclosure is missing");

    expect(details.open).toBe(false);
    expect(within(summary).getByText("0.02%")).toBeTruthy();
    expect(within(summary).getByText("1")).toBeTruthy();
    expect(
      within(summary)
        .getByText("Coverage")
        .parentElement?.getAttribute("title"),
    ).toContain("unique referenced anchors / all standard anchors × 100");
    expect(
      within(summary).getByText("Density").parentElement?.getAttribute("title"),
    ).toContain("requirements per covered anchor");

    fireEvent.click(summary);
    expect(details.open).toBe(true);
    expect(
      within(region).getByRole("row", {
        name: /Chapter 13: Tasks and functions/,
      }),
    ).toBeTruthy();
    const annex = within(region).getByRole("row", {
      name: /Annex A: Formal syntax/,
    });
    expect(within(annex).getByText("0 / 224")).toBeTruthy();
    expect(within(annex).getByText("—")).toBeTruthy();
  });

  it("explains case coverage and renders zero denominators safely", () => {
    const metric = makeTestDataset().corpus_coverage.cases;
    render(<CorpusCoverage kind="cases" metric={metric} />);

    const region = screen.getByRole("region", { name: "Case corpus coverage" });
    const summary = region.querySelector("summary");
    if (!summary) throw new Error("coverage disclosure is missing");

    expect(within(summary).getByText("100%")).toBeTruthy();
    expect(
      within(summary).getByText("Coverage").parentElement?.getAttribute("title"),
    ).toContain("unique requirements linked from cases / all catalog requirements");
    expect(
      within(summary).getByText("Density").parentElement?.getAttribute("title"),
    ).toContain("cases per covered requirement");

    fireEvent.click(summary);
    const annex = within(region).getByRole("row", {
      name: /Annex A: Formal syntax/,
    });
    expect(within(annex).getAllByText("—")).toHaveLength(2);
    expect(within(annex).getAllByText("0 / 0")).toHaveLength(2);
  });
});
