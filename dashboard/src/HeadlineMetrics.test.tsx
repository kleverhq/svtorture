import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HeadlineMetrics } from "./HeadlineMetrics";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

describe("HeadlineMetrics", () => {
  it("shows tool coverage without the campaign summary", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");

    render(
      <HeadlineMetrics dataset={dataset} campaign={campaign} onSelectTool={vi.fn()} />,
    );

    expect(screen.getByText("Verified requirement coverage by tool")).toBeTruthy();
    expect(screen.queryByText("Selected campaign summary")).toBeNull();
    expect(screen.queryByText("Covered requirements")).toBeNull();
  });

  it("reports an unmatched campaign selection", () => {
    const dataset = makeTestDataset();

    render(<HeadlineMetrics dataset={dataset} onSelectTool={vi.fn()} />);

    expect(
      screen.getByText("No campaign matches the current campaign and date selection."),
    ).toBeTruthy();
  });

  it("links a tool row to its requirements without presenting invalid counts", () => {
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
      conforming: 1,
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
    const onSelectTool = vi.fn();

    const view = render(
      <HeadlineMetrics
        dataset={dataset}
        campaign={campaign}
        onSelectTool={onSelectTool}
      />,
    );

    const row = screen.getByRole("button", {
      name: "View requirements for fake/simulator",
    });
    fireEvent.click(row);
    expect(onSelectTool).toHaveBeenCalledWith("fake/simulator");
    expect(row.classList).toContain("tool-metric--unavailable");
    expect(screen.getByText("Unavailable · harness errors present")).toBeTruthy();
    expect(screen.getByText("Unavailable")).toBeTruthy();
    expect(screen.queryByLabelText("fake requirement outcomes")).toBeNull();

    metric.valid = true;
    metric.numerator = 11;
    metric.denominator = 12;
    metric.conforming = 11;
    metric.nonconforming = 1;
    metric.inconclusive = 0;
    view.rerender(
      <HeadlineMetrics
        dataset={dataset}
        campaign={campaign}
        onSelectTool={onSelectTool}
      />,
    );

    const outcomes = screen.getByLabelText("fake requirement outcomes");
    expect(outcomes.querySelector(".tool-outcome--pass")?.textContent).toBe("11PASS");
    expect(outcomes.querySelector(".tool-outcome--fail")?.textContent).toBe("1FAIL");
    expect(outcomes.querySelector(".tool-outcome--unclear")?.textContent).toBe(
      "0UNCLEAR",
    );
    expect(
      screen.getByText("92% of IEEE 1800-2023 applicable requirements"),
    ).toBeTruthy();
  });
});
