import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { metricPointKey } from "./model";
import { makeTestDataset } from "./testDataset";
import type { Dataset, MetricPoint } from "./types";

vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: vi.fn(() => ({
    setOption: vi.fn(),
    on: vi.fn(),
    getZr: () => ({ on: vi.fn() }),
    resize: vi.fn(),
    dispose: vi.fn(),
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

function mockDataset(dataset: Dataset) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(dataset), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal("scrollTo", vi.fn());
  window.history.replaceState(null, "", "/");
});

describe("App overview navigation", () => {
  it("opens Requirements with the clicked tool profile selected", async () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");
    dataset.metrics.push({
      label: "test metric",
      revision: "1800-2023",
      tool_id: "fake",
      profile_id: "simulator",
      numerator: 1,
      denominator: 1,
      corpus_sha: "0".repeat(64),
      complete: true,
      valid: true,
      corpus_coverage: 1,
      execution_coverage: 1,
      conforming: 1,
      nonconforming: 0,
      inconclusive: 0,
      unsupported: 0,
      infrastructure_state: "available",
      campaign_id: campaign.id,
      timestamp: campaign.finished_at,
      tool_sha: null,
      exact_tags: [],
      nearest_tag: null,
      reported_version: "test-tool 1.0",
      image_digest: null,
      repository_commit: campaign.repository.commit,
    });
    mockDataset(dataset);

    render(<App />);
    expect(await screen.findByLabelText("Campaign")).toBeTruthy();
    expect(
      screen.getByText("SystemVerilog conformance framework for EDA tools"),
    ).toBeTruthy();
    expect(screen.getByLabelText("From")).toBeTruthy();
    expect(screen.getByLabelText("To")).toBeTruthy();
    fireEvent.click(
      await screen.findByRole("button", {
        name: "View requirements for fake/simulator",
      }),
    );

    expect(
      screen.getByRole("tab", { name: "Requirements" }).getAttribute("aria-selected"),
    ).toBe("true");
    expect(
      within(screen.getByRole("group", { name: "Tools" }))
        .getByRole("button", { name: "Fake 1" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      within(screen.getByRole("group", { name: "Profiles" }))
        .getByRole("button", { name: "Simulator 1" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    expect(window.location.search).toBe("?view=matrix&tool=fake&profile=simulator");
  });

  it("normalizes stale campaign and non-headline Overview filters", async () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const tool = campaign?.tools[0];
    const profile = tool?.definition.profiles[0];
    if (!campaign || !tool || !profile) throw new Error("incomplete test dataset");
    tool.profile_ids.push("parser");
    tool.definition.profiles.push({ ...profile, id: "parser", headline: false });
    window.history.replaceState(
      null,
      "",
      "/?view=overview&campaign=missing&profile=parser",
    );
    mockDataset(dataset);

    render(<App />);
    const campaignSelect = (await screen.findByLabelText(
      "Campaign",
    )) as HTMLSelectElement;
    await waitFor(() => {
      expect(window.location.search).toBe("?view=overview");
    });
    expect(campaignSelect.value).toBe("");
    expect(screen.queryByRole("button", { name: "Parser 1" })).toBeNull();
  });

  it("normalizes an impossible headline tool/profile pair", async () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const tool = campaign?.tools[0];
    const profile = tool?.definition.profiles[0];
    if (!campaign || !tool || !profile) throw new Error("incomplete test dataset");
    campaign.tools.push({
      ...tool,
      definition: {
        ...tool.definition,
        id: "other",
        display_name: "Other",
        profiles: [{ ...profile, id: "elaborator", headline: true }],
      },
      profile_ids: ["elaborator"],
    });
    window.history.replaceState(
      null,
      "",
      "/?view=overview&tool=fake&profile=elaborator",
    );
    mockDataset(dataset);

    render(<App />);
    await screen.findByLabelText("Campaign");
    await waitFor(() => {
      expect(window.location.search).toBe("?view=overview&tool=fake");
    });
  });

  it("keeps Changes independent from global campaign and date controls", async () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    if (!campaign) throw new Error("incomplete test dataset");
    const point: MetricPoint = {
      label: "history metric",
      revision: "1800-2023",
      tool_id: "fake",
      profile_id: "simulator",
      numerator: 1,
      denominator: 1,
      corpus_sha: "0".repeat(64),
      complete: true,
      valid: true,
      corpus_coverage: 1,
      execution_coverage: 1,
      conforming: 1,
      nonconforming: 0,
      inconclusive: 0,
      unsupported: 0,
      infrastructure_state: "available",
      campaign_id: campaign.id,
      timestamp: campaign.finished_at,
      tool_sha: null,
      exact_tags: [],
      nearest_tag: null,
      reported_version: "fake 1.0",
      image_digest: null,
      repository_commit: campaign.repository.commit,
    };
    dataset.metrics = [point];
    const parameters = new URLSearchParams({
      view: "history",
      campaign: campaign.id,
      dateFrom: "2099-01-01",
      dateTo: "2099-12-31",
      historyRange: "week",
      historyPoint: metricPointKey(point),
    });
    window.history.replaceState(null, "", `/?${parameters.toString()}`);
    mockDataset(dataset);

    render(<App />);
    expect(
      (await screen.findByRole("tab", { name: "Changes" })).getAttribute(
        "aria-selected",
      ),
    ).toBe("true");
    expect((screen.getByLabelText("Campaign") as HTMLSelectElement).disabled).toBe(
      true,
    );
    expect((screen.getByLabelText("From") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText("To") as HTMLInputElement).disabled).toBe(true);
    expect(screen.queryByText("Advanced filters")).toBeNull();
    expect(screen.getByRole("group", { name: "Tools" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Profiles" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Last week" }).getAttribute(
        "aria-pressed",
      ),
    ).toBe("true");
    expect(screen.getByText("fake 1.0")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Last 6 months" }));
    await waitFor(() => {
      expect(window.location.search).toContain("historyRange=six-months");
    });
    expect(window.location.search).toContain("dateFrom=2099-01-01");
    expect(window.location.search).toContain("dateTo=2099-12-31");
  });

  it("filters Campaigns with quick Tool and Profile facets", async () => {
    const dataset = makeTestDataset();
    const campaign = dataset.campaigns[0];
    const tool = campaign?.tools[0];
    const profile = tool?.definition.profiles[0];
    if (!campaign || !tool || !profile) throw new Error("incomplete test dataset");
    const otherId = "20260101T000000Z-other";
    const unavailableId = "20251201T000000Z-unavailable";
    dataset.campaigns.push({
      ...campaign,
      id: otherId,
      finished_at: "2026-01-01T00:00:00Z",
      tools: [
        {
          ...tool,
          definition: {
            ...tool.definition,
            id: "other",
            display_name: "Other",
            profiles: [{ ...profile, id: "parser" }],
          },
          profile_ids: ["parser"],
        },
      ],
    });
    dataset.campaigns.push({
      ...campaign,
      id: unavailableId,
      finished_at: "2025-12-01T00:00:00Z",
      tools: [],
      missing_tool_ids: ["fake"],
    });
    window.history.replaceState(null, "", "/?view=campaigns&search=no-match");
    mockDataset(dataset);

    render(<App />);
    const records = await screen.findByRole("region", { name: "Campaign records" });
    expect(within(records).getByText(campaign.id)).toBeTruthy();
    expect(within(records).getByText(otherId)).toBeTruthy();
    expect(within(records).getByText(unavailableId)).toBeTruthy();
    expect(screen.queryByText("Advanced filters")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Other 1" }));
    expect(within(records).queryByText(campaign.id)).toBeNull();
    expect(within(records).queryByText(unavailableId)).toBeNull();
    expect(within(records).getByText(otherId)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Parser 1" }));
    expect(within(records).getByText(otherId)).toBeTruthy();
  });

  it("filters campaign choices by an inclusive date range", async () => {
    const dataset = makeTestDataset();
    const seed = dataset.campaigns[0];
    if (!seed) throw new Error("incomplete test dataset");
    const older = {
      ...seed,
      id: "20260101T000000Z-older",
      finished_at: "2026-01-01T23:59:59Z",
    };
    const newer = {
      ...seed,
      id: "20260201T000000Z-newer",
      finished_at: "2026-02-01T00:00:01Z",
    };
    dataset.campaigns = [older, newer];
    mockDataset(dataset);

    render(<App />);
    const campaign = (await screen.findByLabelText("Campaign")) as HTMLSelectElement;
    expect(campaign.options).toHaveLength(3);

    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-02-01" },
    });
    fireEvent.change(screen.getByLabelText("To"), {
      target: { value: "2026-02-01" },
    });
    expect(campaign.options).toHaveLength(2);
    expect(campaign.options[1]?.value).toBe(newer.id);
    expect(campaign.value).toBe("");
    expect(window.location.search).toContain("dateFrom=2026-02-01");
    expect(window.location.search).toContain("dateTo=2026-02-01");

    fireEvent.change(campaign, { target: { value: newer.id } });
    expect(window.location.search).toContain(`campaign=${newer.id}`);
  });
});
