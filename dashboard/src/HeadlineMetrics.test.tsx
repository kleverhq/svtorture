import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HeadlineMetrics } from "./HeadlineMetrics";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

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

    const requirements = screen.getByText("Covered requirements").parentElement;
    expect(requirements?.querySelector("strong")?.textContent).toBe("1");
    expect(requirements?.textContent).toContain(
      "1 campaign case maps to these requirements.",
    );
    expect(screen.getByText("Selected campaign summary")).toBeTruthy();
    expect(
      screen.getByText(/Each evaluation is one tool\/profile running one case/),
    ).toBeTruthy();
    const unscored = screen.getByText("Unscored evaluations").parentElement;
    expect(unscored?.querySelector("strong")?.textContent).toBe("0");
    expect(unscored?.textContent).toContain(
      "Cases that were not run or do not apply to the selected tool profile.",
    );
  });

  it("reports an unmatched campaign selection instead of zero counts", () => {
    const dataset = makeTestDataset();

    render(<HeadlineMetrics dataset={dataset} />);

    expect(
      screen.getByText("No campaign matches the current campaign and date selection."),
    ).toBeTruthy();
    expect(screen.queryByText("Covered requirements")).toBeNull();
  });

  it("does not present an invalid metric as zero coverage", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");
    const metric = {
      label: "invalid because of harness errors",
      revision: "1800-2023",
      tool_id: "fake",
      profile_id: "simulator",
      numerator: 0,
      denominator: 1,
      corpus_sha: "0".repeat(64),
      complete: true,
      valid: false,
      corpus_coverage: 1,
      execution_coverage: 1,
      conforming: 0,
      nonconforming: 0,
      inconclusive: 0,
      unsupported: 0,
      infrastructure_state: "harness errors present",
      campaign_id: campaign.id,
      timestamp: campaign.finished_at,
      tool_sha: null,
      exact_tags: [],
      nearest_tag: null,
      reported_version: "test-tool 1.0",
      image_digest: null,
      repository_commit: campaign.repository.commit,
    };
    dataset.metrics.push(metric);

    const view = render(<HeadlineMetrics dataset={dataset} campaign={campaign} />);

    const unavailable = screen.getByText("Unavailable");
    expect(unavailable.parentElement?.classList).toContain(
      "tool-metric__score--unavailable",
    );
    expect(screen.getByText("Not scored · harness errors present")).toBeTruthy();
    expect(document.querySelector(".meter")).toBeNull();

    metric.valid = true;
    metric.numerator = 10;
    metric.denominator = 11;
    view.rerender(<HeadlineMetrics dataset={dataset} campaign={campaign} />);

    const score = screen.getByText("10 / 11");
    expect(score.parentElement?.classList).not.toContain(
      "tool-metric__score--unavailable",
    );
    expect(screen.getByText("91% of IEEE 1800-2023")).toBeTruthy();
    expect(screen.queryByText(/Not scored/)).toBeNull();
  });

  it("counts known issues only among failed evaluations", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const passingResult = campaign?.results[0];
    if (!campaign || !passingResult) throw new Error("incomplete test dataset");
    passingResult.known_issue = "Passing context must not count as a known failure.";
    campaign.results.push({
      ...passingResult,
      status: "nonconforming",
      reason: "unexpected-result",
      known_issue: null,
    });

    render(<HeadlineMetrics dataset={dataset} campaign={campaign} />);

    const failures = screen.getByText("Failed evaluations").parentElement;
    expect(failures?.querySelector("strong")?.textContent).toBe("1");
    expect(failures?.textContent).toContain(
      "2 recorded evaluations; 0 failures linked to a known issue.",
    );
    expect(screen.getByText("Needs inspection")).toBeTruthy();
    expect(
      screen.getByText("Inconclusive observations or harness errors."),
    ).toBeTruthy();
  });
});
