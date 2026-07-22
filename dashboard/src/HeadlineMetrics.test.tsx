import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HeadlineMetrics } from "./HeadlineMetrics";
import { makeTestDataset } from "./testDataset";

afterEach(cleanup);

describe("HeadlineMetrics", () => {
  it("renders coverage as a six-column table without an extra title", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");

    render(
      <HeadlineMetrics
        dataset={dataset}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        searchFilter=""
        onSelectTool={vi.fn()}
      />,
    );

    for (const heading of ["Tool", "Pass", "Fail", "Unclear", "Coverage", "Version"]) {
      expect(screen.getByRole("columnheader", { name: heading })).toBeTruthy();
    }
    expect(screen.queryByText("Verified requirement coverage by tool")).toBeNull();
  });

  it("reports an unmatched campaign selection", () => {
    render(
      <HeadlineMetrics
        dataset={makeTestDataset()}
        toolFilter=""
        profileFilter=""
        searchFilter=""
        onSelectTool={vi.fn()}
      />,
    );

    expect(
      screen.getByText("No campaign matches the current campaign and date selection."),
    ).toBeTruthy();
  });

  it("links a tool row and filters it by profile or search", () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");
    const metric = {
      label: "invalid because of infrastructure errors",
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
      infrastructure_state: "infra errors present",
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
        toolFilter=""
        profileFilter=""
        searchFilter=""
        onSelectTool={onSelectTool}
      />,
    );

    const button = screen.getByRole("button", {
      name: "View requirements for fake/simulator",
    });
    fireEvent.click(button);
    expect(onSelectTool).toHaveBeenCalledWith("fake", "simulator");
    expect(button.closest("tr")?.classList).toContain("is-unavailable");
    expect(screen.getByText("Unavailable · infra errors present")).toBeTruthy();
    expect(screen.getAllByText("—")).toHaveLength(3);

    metric.valid = true;
    metric.numerator = 11;
    metric.denominator = 12;
    metric.conforming = 11;
    metric.nonconforming = 1;
    view.rerender(
      <HeadlineMetrics
        dataset={dataset}
        campaign={campaign}
        toolFilter=""
        profileFilter=""
        searchFilter="test-tool"
        onSelectTool={onSelectTool}
      />,
    );
    expect(screen.getByText("11")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
    expect(screen.getByText("92% · IEEE 1800-2023")).toBeTruthy();
    expect(screen.getByText("test-tool 1.0")).toBeTruthy();

    view.rerender(
      <HeadlineMetrics
        dataset={dataset}
        campaign={campaign}
        toolFilter=""
        profileFilter="parser"
        searchFilter=""
        onSelectTool={onSelectTool}
      />,
    );
    expect(
      screen.queryByRole("button", {
        name: "View requirements for fake/simulator",
      }),
    ).toBeNull();
    expect(
      screen.getByText("No tool profiles match the current Overview filters."),
    ).toBeTruthy();
  });
});
