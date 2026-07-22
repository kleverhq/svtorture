import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HistoryView, formatUtcMinute, metricPercentage } from "./HistoryView";
import { metricPointKey } from "./model";
import { makeTestDataset } from "./testDataset";
import type { MetricPoint } from "./types";

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

function makeMetric(): { dataset: ReturnType<typeof makeTestDataset>; point: MetricPoint } {
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

describe("HistoryView", () => {
  it("configures a fixed timeline, corpus boundaries, and invalid gaps", async () => {
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
    render(
      <HistoryView
        dataset={dataset}
        toolFilter=""
        profileFilter=""
        range="month"
        selectedPointKey=""
        onRangeChange={vi.fn()}
        onSelectPoint={vi.fn()}
      />,
    );

    await waitFor(() => expect(chartMock.option).toBeTruthy());
    const option = chartMock.option as any;
    expect(option.yAxis).toMatchObject({ min: 0, max: 100, interval: 20 });
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
    expect(option.series[1].data[0]).toMatchObject({
      unavailable: true,
      value: [expect.any(Number), 0],
    });
    expect(option.tooltip.formatter({ data: lineData[0] })).toBe(
      "<strong>75%</strong><br/>fake/simulator<br/>2026-07-22 10:58 UTC",
    );
    expect(option.tooltip.formatter({ data: option.series[1].data[0] })).toBe(
      "<strong>Unavailable</strong><br/>fake/simulator<br/>2026-07-22 12:58 UTC",
    );
    expect(metricPercentage(point)).toBe(75);
    expect(formatUtcMinute(point.timestamp)).toBe("2026-07-22 10:58");
  });

  it("selects chart points, clears on blank canvas, and renders provenance", async () => {
    const { dataset, point } = makeMetric();
    const onSelectPoint = vi.fn();
    const onRangeChange = vi.fn();
    const view = render(
      <HistoryView
        dataset={dataset}
        toolFilter=""
        profileFilter=""
        range="month"
        selectedPointKey=""
        onRangeChange={onRangeChange}
        onSelectPoint={onSelectPoint}
      />,
    );
    await waitFor(() => expect(chartMock.handlers.click).toBeTruthy());
    const key = metricPointKey(point);

    fireEvent.keyDown(
      screen.getByRole("group", { name: /Verified requirement coverage/ }),
      { key: "ArrowRight" },
    );
    expect(onSelectPoint).toHaveBeenLastCalledWith(key);

    act(() => {
      chartMock.handlers.click?.({
        componentType: "series",
        data: { pointKey: key },
      });
    });
    expect(onSelectPoint).toHaveBeenLastCalledWith(key);

    view.rerender(
      <HistoryView
        dataset={dataset}
        toolFilter=""
        profileFilter=""
        range="month"
        selectedPointKey={key}
        onRangeChange={onRangeChange}
        onSelectPoint={onSelectPoint}
      />,
    );
    const inspector = screen.getByRole("complementary", {
      name: "Metric point details",
    });
    expect(inspector).toBeTruthy();
    await waitFor(() => expect(document.activeElement).toBe(inspector));
    expect(screen.getByText("fake/simulator")).toBeTruthy();
    expect(screen.getByText("75% · 3/4")).toBeTruthy();
    expect(screen.getByText("IEEE 1800-2023")).toBeTruthy();
    expect(screen.getByText("fake 1.0")).toBeTruthy();
    expect(screen.getByText("v1.0")).toBeTruthy();
    expect(screen.getByText(point.campaign_id)).toBeTruthy();
    expect(screen.getByText(point.corpus_sha)).toBeTruthy();
    expect(chartMock.dispose).not.toHaveBeenCalled();

    await waitFor(() => expect(chartMock.zrHandlers.click).toBeTruthy());
    act(() => chartMock.zrHandlers.click?.({ target: null }));
    expect(onSelectPoint).toHaveBeenLastCalledWith("");

    fireEvent.click(screen.getByRole("button", { name: "Last week" }));
    expect(onRangeChange).toHaveBeenCalledWith("week");
    fireEvent.click(screen.getByRole("button", { name: "Close metric details" }));
    expect(onSelectPoint).toHaveBeenLastCalledWith("");
  });
});
