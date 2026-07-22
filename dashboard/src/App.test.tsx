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
import { makeTestDataset } from "./testDataset";
import type { Dataset } from "./types";

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
