import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";


import { CorpusCoverage } from "./CorpusCoverage";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

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
    const formulaId = summary.getAttribute("aria-describedby");
    const formula = formulaId ? document.getElementById(formulaId) : null;
    expect(formula).toBeTruthy();
    expect(details.contains(formula)).toBe(false);
    expect(formula?.textContent).toContain(
      "unique referenced anchors / eligible standard anchors after waiver-only exclusions",
    );
    expect(
      within(summary).getByText("Standard anchors vs requirements:"),
    ).toBeTruthy();
    expect(within(summary).getByText("0.02%")).toBeTruthy();
    expect(within(summary).getByText("1")).toBeTruthy();
    expect(
      within(summary)
        .getByText("Coverage")
        .parentElement?.getAttribute("title"),
    ).toContain(
      "unique referenced anchors / eligible standard anchors after waiver-only exclusions × 100",
    );
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
    expect(within(region).getByRole("columnheader", { name: "Waived" })).toBeTruthy();
    const annex = within(region).getByRole("row", {
      name: /Annex A: Formal syntax/,
    });
    expect(within(annex).getByText("0 / 224")).toBeTruthy();
    expect(within(annex).getByText("17")).toBeTruthy();
    expect(within(annex).getByText("—")).toBeTruthy();
  });

  it("colors requirement breakdown rows at the exact coverage boundaries", () => {
    const base = makeTestDataset().corpus_coverage.requirements;
    const coverage = [
      { id: "1", numerator: 0, denominator: 100, tone: "zero" },
      { id: "2", numerator: 29, denominator: 100, tone: "low" },
      { id: "3", numerator: 30, denominator: 100, tone: "medium" },
      { id: "4", numerator: 79, denominator: 100, tone: "medium" },
      { id: "5", numerator: 80, denominator: 100, tone: "high" },
      { id: "6", numerator: 0, denominator: 0, tone: "zero" },
    ];
    render(
      <CorpusCoverage
        kind="requirements"
        metric={{
          ...base,
          breakdown: coverage.map((item) => ({
            id: item.id,
            kind: "chapter",
            title: `Boundary ${item.id}`,
            coverage: {
              numerator: item.numerator,
              denominator: item.denominator,
            },
            density: { numerator: 0, denominator: 0 },
            waived: 0,
          })),
        }}
      />,
    );

    fireEvent.click(screen.getByText("Breakdown"));
    for (const item of coverage) {
      expect(
        screen
          .getByRole("row", { name: new RegExp(`Chapter ${item.id}:`) })
          .classList.contains(`corpus-coverage__row--${item.tone}`),
      ).toBe(true);
    }
  });

  it("explains case coverage and renders zero denominators safely", () => {
    const metric = makeTestDataset().corpus_coverage.cases;
    render(<CorpusCoverage kind="cases" metric={metric} />);

    const region = screen.getByRole("region", { name: "Case corpus coverage" });
    const summary = region.querySelector("summary");
    if (!summary) throw new Error("coverage disclosure is missing");

    expect(within(summary).getByText("100%")).toBeTruthy();
    expect(within(summary).getByText("Requirements vs cases:")).toBeTruthy();
    expect(
      within(summary).queryByText("Standard anchors vs requirements:"),
    ).toBeNull();
    expect(
      within(summary).getByText("Coverage").parentElement?.getAttribute("title"),
    ).toContain("unique requirements linked from cases / all catalog requirements");
    expect(
      within(summary).getByText("Density").parentElement?.getAttribute("title"),
    ).toContain("cases per covered requirement");

    fireEvent.click(summary);
    expect(within(region).queryByRole("columnheader", { name: "Waived" })).toBeNull();
    const annex = within(region).getByRole("row", {
      name: /Annex A: Formal syntax/,
    });
    expect(within(annex).getAllByText("—")).toHaveLength(2);
    expect(within(annex).getAllByText("0 / 0")).toHaveLength(2);
    expect(annex.classList.contains("corpus-coverage__row--zero")).toBe(true);
  });
});
