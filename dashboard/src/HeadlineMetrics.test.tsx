import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HeadlineMetrics } from "./HeadlineMetrics";
import { makeTestDataset } from "./testDataset";

describe("HeadlineMetrics", () => {
  it("counts requirements covered by selected campaign cases", () => {
    const dataset = makeTestDataset();
    const requirement = dataset.requirements[0];
    const testCase = dataset.cases[0];
    const campaign = dataset.campaigns[0];
    if (!requirement || !testCase || !campaign) {
      throw new Error("incomplete test dataset");
    }
    dataset.requirements.push({
      ...requirement,
      id: "SV-2023-99-UNSELECTED",
      chapter: 99,
      clause: "99.1",
    });
    dataset.cases.push({
      ...testCase,
      id: "ch99-unselected",
      primary_requirement: "SV-2023-99-UNSELECTED",
    });

    render(<HeadlineMetrics dataset={dataset} campaign={campaign} />);

    const requirements = screen.getByText("Requirements").parentElement;
    expect(requirements?.querySelector("strong")?.textContent).toBe("1");
  });
});
