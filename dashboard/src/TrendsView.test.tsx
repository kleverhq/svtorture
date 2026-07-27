import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  formatUtcMinute,
  ratioValue,
  toolPassRate,
  trendPoints,
  TrendsView,
} from "./TrendsView";
import { corpusTrendPointKey, toolTrendPointKey } from "./model";
import { makeTestDataset } from "./testDataset";
import type { Campaign, Dataset, MetricPoint } from "./types";

const chartMock = vi.hoisted(() => ({
  option: undefined as Record<string, unknown> | undefined,
  handlers: {} as Record<string, (event: any) => void>,
  zrHandlers: {} as Record<string, (event: any) => void>,
  resize: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: vi.fn(() => ({
    setOption: (option: Record<string, unknown>) => {
      chartMock.option = option;
    },
    on: (event: string, handler: (value: any) => void) => {
      chartMock.handlers[event] = handler;
    },
    getZr: () => ({
      on: (event: string, handler: (value: any) => void) => {
        chartMock.zrHandlers[event] = handler;
      },
    }),
    resize: chartMock.resize,
    dispose: chartMock.dispose,
  })),
}));
vi.mock("echarts/charts", () => ({ LineChart: {}, ScatterChart: {} }));
vi.mock("echarts/components", () => ({
  DataZoomComponent: {},
  GridComponent: {},
  LegendComponent: {},
  MarkLineComponent: {},
  TooltipComponent: {},
}));
vi.mock("echarts/renderers", () => ({ SVGRenderer: {} }));

afterEach(() => {
  cleanup();
  chartMock.option = undefined;
  chartMock.handlers = {};
  chartMock.zrHandlers = {};
  vi.clearAllMocks();
});

function makeMetric(): { dataset: Dataset; point: MetricPoint } {
  const dataset = makeTestDataset();
  const campaign = dataset.campaigns[0];
  if (!campaign) throw new Error("test dataset has no campaign");
  const point: MetricPoint = {
    label: "verified support",
    revision: "1800-2023",
    tool_id: "fake",
    profile_id: "simulator",
    numerator: 3,
    denominator: 4,
    corpus_sha: "1".repeat(64),
    complete: true,
    valid: true,
    corpus_coverage: 1,
    execution_coverage: 1,
    conforming: 3,
    nonconforming: 1,
    inconclusive: 0,
    unsupported: 0,
    infrastructure_state: "available",
    campaign_id: campaign.id,
    timestamp: "2026-07-22T10:58:19Z",
    tool_sha: "2".repeat(40),
    exact_tags: ["v1.0"],
    nearest_tag: null,
    reported_version: "fake 1.0",
    image_digest: `sha256:${"3".repeat(64)}`,
    repository_commit: campaign.repository.commit,
  };
  dataset.metrics = [point];
  return { dataset, point };
}

function secondCampaign(dataset: Dataset): Campaign {
  const first = dataset.campaigns[0];
  if (!first) throw new Error("test dataset has no campaign");
  const second = {
    ...first,
    id: "20260201T000000Z-test",
    started_at: "2026-02-01T00:00:00Z",
    finished_at: "2026-02-01T00:01:00Z",
    hashes: {
      requirements: "a".repeat(64),
      cases: "b".repeat(64),
      selection: "c".repeat(64),
    },
    corpus_metrics: {
      requirements: {
        coverage: { numerator: 4, denominator: 16963 },
        density: { numerator: 5, denominator: 4 },
        breakdown: first.corpus_metrics.requirements.breakdown.map((part) =>
          part.kind === "chapter" && part.id === "5"
            ? {
                ...part,
                coverage: { numerator: 2, denominator: 300 },
                density: { numerator: 3, denominator: 2 },
              }
            : part,
        ),
      },
      cases: {
        coverage: { numerator: 2, denominator: 2 },
        density: { numerator: 4, denominator: 2 },
        breakdown: first.corpus_metrics.cases.breakdown.map((part) =>
          part.kind === "chapter" && part.id === "5"
            ? {
                ...part,
                coverage: { numerator: 1, denominator: 1 },
                density: { numerator: 2, denominator: 1 },
              }
            : part.kind === "chapter" && part.id === "13"
              ? { ...part, density: { numerator: 2, denominator: 1 } }
              : part,
        ),
      },
    },
  } satisfies Campaign;
  dataset.campaigns.push(second);
  return second;
}

function renderView(
  dataset: Dataset,
  overrides: Partial<ComponentProps<typeof TrendsView>> = {},
) {
  const props: ComponentProps<typeof TrendsView> = {
    dataset,
    toolFilter: "",
    profileFilter: "",
    trend: "pass-rate",
    range: "month",
    selectedPointKey: "",
    selectedParts: [],
    onTrendChange: vi.fn(),
    onRangeChange: vi.fn(),
    onSelectPoint: vi.fn(),
    ...overrides,
  };
  return { ...render(<TrendsView {...props} />), props };
}

describe("TrendsView", () => {
  it("normalizes grouped formulas and arbitrary chapter/annex combinations", () => {
    const { dataset, point } = makeMetric();
    const campaign = dataset.campaigns[0]!;

    expect(toolPassRate(point)).toBe(75);
    expect(ratioValue({ numerator: 3, denominator: 4 }, "percent")).toBe(75);
    expect(ratioValue({ numerator: 3, denominator: 2 }, "density")).toBe(1.5);
    expect(ratioValue({ numerator: 0, denominator: 0 }, "density")).toBeNull();
    expect(trendPoints(dataset, "pass-rate", "other", "")).toEqual([]);

    const coverage = trendPoints(dataset, "coverage", "other", "parser");
    expect(coverage).toHaveLength(2);
    expect(coverage.find((item) => item.seriesName === "Requirements")?.value).toBeCloseTo(
      (100 * 3) / 16963,
    );
    expect(coverage.find((item) => item.seriesName === "Cases")?.value).toBe(100);
    const selected = trendPoints(dataset, "coverage", "", "", [
      "chapter:13",
      "annex:A",
    ]);
    expect(selected.find((item) => item.seriesName === "Requirements")?.value).toBeCloseTo(
      (100 * 2) / 16663,
    );
    expect(selected.find((item) => item.seriesName === "Cases")?.value).toBe(100);
    expect(
      trendPoints(dataset, "density", "", "", ["chapter:5"]).find(
        (item) => item.seriesName === "Cases",
      )?.value,
    ).toBeNull();

    expect(corpusTrendPointKey(campaign, "requirements")).toBe(
      `corpus:${campaign.id}:requirements`,
    );
    const hashOnly = {
      ...campaign,
      id: "hash-only-change",
      hashes: {
        requirements: "d".repeat(64),
        cases: "e".repeat(64),
        selection: "f".repeat(64),
      },
    } satisfies Campaign;
    dataset.campaigns.push(hashOnly);
    const unchangedOperands = trendPoints(dataset, "coverage", "", "").filter(
      (item) => item.seriesName === "Requirements",
    );
    expect(unchangedOperands[0]?.boundaryKey).toBe(
      unchangedOperands[1]?.boundaryKey,
    );
    const changedOperands = secondCampaign(dataset);
    expect(
      trendPoints(dataset, "coverage", "", "").find(
        (item) =>
          item.campaignId === changedOperands.id &&
          item.seriesName === "Requirements",
      )?.boundaryKey,
    ).not.toBe(unchangedOperands[0]?.boundaryKey);
    expect(toolTrendPointKey(point)).toBe(`tool:${campaign.id}:fake:simulator`);
    expect(formatUtcMinute(point.timestamp)).toBe("2026-07-22 10:58");
  });

  it("offers three described trends with exactly one selected", () => {
    const { dataset } = makeMetric();
    const onTrendChange = vi.fn();
    renderView(dataset, { onTrendChange });

    expect(screen.getByRole("radiogroup", { name: "Trend" })).toBeTruthy();
    const ranges = document.querySelector(".trends__ranges");
    expect(ranges).not.toBeNull();
    expect(
      within(ranges as HTMLElement)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual([
      "All time",
      "Last year",
      "Last 6 months",
      "Last 3 months",
      "Last month",
      "Last week",
    ]);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    expect(radios.filter((radio) => (radio as HTMLInputElement).checked)).toHaveLength(
      1,
    );
    expect(
      (screen.getByRole("radio", { name: "Pass rate" }) as HTMLInputElement)
        .checked,
    ).toBe(true);
    const coverage = screen.getByRole("radio", { name: "Coverage" });
    const description = document.getElementById(
      coverage.getAttribute("aria-describedby")!,
    );
    expect(description?.textContent).toContain("referenced anchors");
    expect(coverage.closest("label")?.getAttribute("title")).toContain(
      "referenced anchors",
    );
    fireEvent.click(screen.getByRole("radio", { name: "Density" }));
    expect(onTrendChange).toHaveBeenCalledWith("density");
  });

  it("preserves tool zoom, boundaries, unavailable points, and 100% headroom", async () => {
    const { dataset, point } = makeMetric();
    dataset.metrics.push(
      {
        ...point,
        campaign_id: "boundary-campaign",
        timestamp: "2026-07-22T11:58:19Z",
        corpus_sha: "4".repeat(64),
      },
      {
        ...point,
        campaign_id: "invalid-campaign",
        timestamp: "2026-07-22T12:58:19Z",
        corpus_sha: "4".repeat(64),
        valid: false,
      },
    );
    renderView(dataset);

    await waitFor(() => expect(chartMock.option).toBeTruthy());
    const option = chartMock.option as any;
    expect(option.yAxis).toMatchObject({ min: 0, max: 110, interval: 20 });
    expect(option.yAxis.axisLabel.formatter(100)).toBe("100%");
    expect(option.yAxis.axisLabel.formatter(110)).toBe("");
    expect(option.xAxis.minInterval).toBe(24 * 60 * 60 * 1000);
    expect(option.dataZoom).toHaveLength(2);
    expect(option.dataZoom[0]).toMatchObject({
      type: "inside",
      zoomOnMouseWheel: true,
      moveOnMouseMove: true,
    });
    const lineData = option.series[0].data;
    expect(lineData[1]).toMatchObject({ value: [expect.any(Number), null] });
    expect(lineData[2]).toMatchObject({ boundary: true, symbol: "diamond" });
    expect(lineData[3].value[1]).toBeNull();
    expect(option.series[1]).toMatchObject({ type: "scatter" });
    expect(option.series.at(-1).markLine).toMatchObject({
      label: { position: "insideEndTop" },
      data: [{ yAxis: 100, label: { formatter: "100%" } }],
    });
    expect(option.tooltip.formatter({ data: lineData[0] })).toBe(
      "<strong>75%</strong><br/>fake/simulator<br/>3/4<br/>2026-07-22 10:58 UTC",
    );
  });

  it("renders Requirements and Cases lines with coverage and density markers", async () => {
    const { dataset } = makeMetric();
    secondCampaign(dataset);
    const view = renderView(dataset, { trend: "coverage" });

    await waitFor(() => expect(chartMock.option).toBeTruthy());
    let option = chartMock.option as any;
    expect(option.legend.data).toEqual(["Requirements", "Cases"]);
    expect(option.series.filter((series: any) => series.name !== "Reference")).toHaveLength(
      2,
    );
    expect(option.series[0].data[0].value[1]).toBeCloseTo((100 * 3) / 16963);
    expect(option.series[1].data[0].value[1]).toBe(100);
    expect(option.yAxis.max).toBe(110);
    expect(option.series.at(-1).markLine.data).toEqual([
      { yAxis: 100, label: { formatter: "100%" } },
    ]);

    view.rerender(<TrendsView {...view.props} trend="density" />);
    await waitFor(() => {
      option = chartMock.option as any;
      expect(option.yAxis.name).toBe("density");
    });
    expect(option.yAxis.max).toBeGreaterThan(2);
    expect(option.yAxis.axisLabel.formatter(2)).toBe("2×");
    expect(option.yAxis.axisLabel.formatter(option.yAxis.max)).toBe("");
    expect(option.series.at(-1).markLine.data).toEqual([
      { yAxis: 1, label: { formatter: "1×" } },
      { yAxis: 2, label: { formatter: "2×" } },
    ]);
    expect(option.series[0].data.at(-1).value[1]).toBe(1.25);
    expect(option.series[1].data.at(-1).value[1]).toBe(2);
  });

  it("renders a zero-denominator corpus point as unavailable", async () => {
    const { dataset } = makeMetric();
    const campaign = dataset.campaigns[0]!;
    campaign.corpus_metrics.cases.density = { numerator: 0, denominator: 0 };
    renderView(dataset, { trend: "density" });

    await waitFor(() => expect(chartMock.option).toBeTruthy());
    const option = chartMock.option as any;
    const casesLine = option.series.find(
      (series: any) => series.name === "Cases" && series.type === "line",
    );
    const casesUnavailable = option.series.find(
      (series: any) => series.name === "Cases" && series.type === "scatter",
    );
    expect(casesLine.data[0].value[1]).toBeNull();
    expect(casesUnavailable.data[0]).toMatchObject({
      unavailable: true,
      value: [expect.any(Number), 0],
    });
  });

  it("selects points, clears blank canvas, and renders tool and corpus provenance", async () => {
    const { dataset, point } = makeMetric();
    const onSelectPoint = vi.fn();
    const onRangeChange = vi.fn();
    const view = renderView(dataset, { onSelectPoint, onRangeChange });
    await waitFor(() => expect(chartMock.handlers.click).toBeTruthy());
    const key = toolTrendPointKey(point);

    const chartGroup = screen.getByRole("group", {
      name: /Pass rate over time/,
    });
    chartGroup.focus();
    fireEvent.keyDown(chartGroup, { key: "ArrowRight" });
    expect(onSelectPoint).toHaveBeenLastCalledWith(key);

    act(() => {
      chartMock.handlers.click?.({ componentType: "series", data: { pointKey: key } });
    });
    expect(onSelectPoint).toHaveBeenLastCalledWith(key);

    view.rerender(<TrendsView {...view.props} selectedPointKey={key} />);
    const inspector = screen.getByRole("complementary", {
      name: "Trend point details",
    });
    expect(document.activeElement).toBe(chartGroup);
    fireEvent.keyDown(chartGroup, { key: "ArrowRight" });
    expect(onSelectPoint).toHaveBeenLastCalledWith(key);
    fireEvent.keyDown(chartGroup, { key: "Escape" });
    expect(onSelectPoint).toHaveBeenLastCalledWith("");
    expect(screen.getByText("fake/simulator")).toBeTruthy();
    expect(screen.getByText("75%")).toBeTruthy();
    expect(screen.getByText("3/4")).toBeTruthy();
    expect(screen.getByText("IEEE 1800-2023")).toBeTruthy();
    expect(screen.getByText("fake 1.0")).toBeTruthy();
    expect(screen.getByText("v1.0")).toBeTruthy();
    expect(screen.getByText(point.campaign_id)).toBeTruthy();
    expect(chartMock.dispose).not.toHaveBeenCalled();

    await waitFor(() => expect(chartMock.zrHandlers.click).toBeTruthy());
    act(() => chartMock.zrHandlers.click?.({ target: null }));
    expect(onSelectPoint).toHaveBeenLastCalledWith("");
    fireEvent.click(screen.getByRole("button", { name: "Last week" }));
    expect(onRangeChange).toHaveBeenCalledWith("week");
    fireEvent.click(screen.getByRole("button", { name: "Close trend details" }));
    expect(onSelectPoint).toHaveBeenLastCalledWith("");

    const campaign = dataset.campaigns[0]!;
    const corpusKey = corpusTrendPointKey(campaign, "requirements");
    view.rerender(
      <TrendsView
        {...view.props}
        trend="density"
        selectedPointKey={corpusKey}
      />,
    );
    const corpusInspector = await screen.findByRole("complementary", {
      name: "Trend point details",
    });
    expect(
      within(corpusInspector).getByRole("heading", { name: "Requirements" }),
    ).toBeTruthy();
    expect(within(corpusInspector).getByText("Density")).toBeTruthy();
    expect(within(corpusInspector).getByText("1×")).toBeTruthy();
    expect(
      within(corpusInspector).getAllByText(campaign.hashes.requirements),
    ).toHaveLength(3);
    expect(within(corpusInspector).getByText(campaign.repository.commit)).toBeTruthy();
  });
});
