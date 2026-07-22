import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { makeTestDataset } from "./testDataset";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(dataset), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", {
        name: "View requirements for fake/simulator",
      }),
    );

    expect(
      screen.getByRole("tab", { name: "Requirements" }).getAttribute("aria-selected"),
    ).toBe("true");
    expect(
      (screen.getByLabelText("Tool / profile") as HTMLSelectElement).value,
    ).toBe("fake/simulator");
    expect(window.location.search).toBe("?view=matrix&tool=fake%2Fsimulator");
  });
});
