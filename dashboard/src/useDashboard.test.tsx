import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import catalogBody from "./testdata/campaign/catalog.json?raw";
import evidenceBody from "./testdata/campaign/evidence/0000.json?raw";
import manifestBody from "./testdata/campaign/manifest.json?raw";
import verdictsBody from "./testdata/campaign/verdicts.json?raw";
import type {
  CampaignCatalog,
  CampaignEvidence,
  CampaignManifest,
  CampaignTrends,
  CampaignVerdicts,
  DashboardIndex,
} from "./types";
import { clearResourceCache, useDashboard } from "./useDashboard";

function fixture() {
  const manifest = JSON.parse(manifestBody) as CampaignManifest;
  const catalog = JSON.parse(catalogBody) as CampaignCatalog;
  const verdicts = JSON.parse(verdictsBody) as CampaignVerdicts;
  const evidence = JSON.parse(evidenceBody) as CampaignEvidence;
  const trends: CampaignTrends = {
    schema_version: 6,
    kind: "campaign-trends",
    campaigns: [
      {
        schema_version: 6,
        kind: "campaign-summary",
        id: manifest.id,
        started_at: manifest.started_at,
        finished_at: manifest.finished_at,
        complete: manifest.complete,
        repository: { commit: manifest.repository.commit },
        trust: manifest.trust,
        hashes: manifest.hashes,
        corpus_metrics: manifest.corpus_metrics,
        tool_metrics: manifest.metrics,
      },
    ],
  };
  const index: DashboardIndex = {
    schema_version: 6,
    kind: "dashboard-index",
    default_campaign_id: manifest.id,
    campaigns: [{ id: manifest.id, manifest: `campaigns/${manifest.id}/manifest.json` }],
    trends: "trends.json",
    schemas: {
      summary: "schemas/campaign-summary.schema.json",
      trends: "schemas/campaign-trends.schema.json",
      campaign: "schemas/campaign-manifest.schema.json",
      catalog: "schemas/campaign-catalog.schema.json",
      verdicts: "schemas/campaign-verdicts.schema.json",
      evidence: "schemas/campaign-evidence.schema.json",
    },
  };
  const prefix = `/data/campaigns/${manifest.id}/`;
  return {
    manifest,
    catalog,
    verdicts,
    evidence,
    trends,
    index,
    resources: new Map<string, string>([
      ["/data/index.json", JSON.stringify(index)],
      ["/data/trends.json", JSON.stringify(trends)],
      [`${prefix}manifest.json`, manifestBody],
      [`${prefix}catalog.json`, catalogBody],
      [`${prefix}verdicts.json`, verdictsBody],
      [`${prefix}evidence/0000.json`, evidenceBody],
    ]),
  };
}

function installFetch(resources: Map<string, string>) {
  const fetchMock = vi.fn(async (input: URL | RequestInfo) => {
    const path = new URL(String(input), window.location.href).pathname;
    const body = resources.get(path);
    return body === undefined
      ? new Response("not found", { status: 404 })
      : new Response(body, { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  clearResourceCache();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("useDashboard", () => {
  it("loads index, trends, selected compact resources, then one cached evidence shard", async () => {
    const data = fixture();
    const fetchMock = installFetch(data.resources);
    const { result } = renderHook(() => useDashboard("", "", ""));

    await waitFor(() => expect(result.current.dataset).toBeTruthy());
    const requested = fetchMock.mock.calls.map(([input]) => new URL(String(input)).pathname);
    expect(requested).toEqual([
      "/data/index.json",
      "/data/trends.json",
      `/data/campaigns/${data.manifest.id}/manifest.json`,
      `/data/campaigns/${data.manifest.id}/catalog.json`,
      `/data/campaigns/${data.manifest.id}/verdicts.json`,
    ]);
    expect(requested.some((path) => path.includes("/evidence/"))).toBe(false);
    expect(result.current.dataset?.standard_sections).toHaveLength(1740);
    expect(result.current.dataset?.standard_sections[0]).toEqual({
      clause: "1",
      title: "Overview",
    });

    let results = await result.current.loadCaseEvidence!(data.catalog.cases[0]!.id);
    expect(results[0]?.observations.length).toBeGreaterThan(0);
    const evidence = data.evidence.results[0]!;
    expect(results[0]?.reproduction_command).toBe(
      `just reproduce 'http://localhost:3000/data/campaigns/${data.manifest.id}/manifest.json' '${evidence.tool_id}' '${evidence.profile_id}' '${data.catalog.cases[0]!.id}'`,
    );
    results = await result.current.loadCaseEvidence!(data.catalog.cases[0]!.id);
    expect(results.length).toBeGreaterThan(0);
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes("evidence/0000.json")),
    ).toHaveLength(1);
  });

  it("renders summary-only consumers without requesting campaign detail", async () => {
    const data = fixture();
    const fetchMock = installFetch(data.resources);
    const { result } = renderHook(() => useDashboard("", "", "", true, false));

    await waitFor(() => expect(result.current.trends).toBeTruthy());
    expect(result.current.dataset).toBeUndefined();
    expect(fetchMock.mock.calls.map(([input]) => new URL(String(input)).pathname)).toEqual([
      "/data/index.json",
      "/data/trends.json",
    ]);
  });

  it("preserves a trend-only historical deep link and exposes its Release", async () => {
    const data = fixture();
    const historical = {
      ...data.trends.campaigns[0]!,
      id: "20250101T000000Z-historical",
      archive: {
        release_tag: "campaign-20250101T000000Z-historical",
        release_url: "https://github.com/example/repo/releases/tag/campaign-old",
        asset_name: "svtorture-campaign-20250101T000000Z-historical.zip",
        download_url: "https://github.com/example/repo/releases/download/campaign-old/archive.zip",
        sha256: "2".repeat(64),
        bytes: 123,
      },
    };
    data.trends.campaigns.unshift(historical);
    data.resources.set("/data/trends.json", JSON.stringify(data.trends));
    const fetchMock = installFetch(data.resources);
    const { result } = renderHook(() => useDashboard(historical.id, "", ""));

    await waitFor(() => expect(result.current.unavailable?.id).toBe(historical.id));
    expect(result.current.dataset).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([
    "../escape.json",
    "%2e%2e/escape.json",
    "https://example.com/manifest.json",
  ])(
    "rejects unsafe resource href %s without fetching it",
    async (href) => {
      const data = fixture();
      data.index.campaigns[0]!.manifest = href;
      data.resources.set("/data/index.json", JSON.stringify(data.index));
      const fetchMock = installFetch(data.resources);
      const { result } = renderHook(() => useDashboard("", "", ""));

      await waitFor(() => expect(result.current.error).toMatch(/resource path/));
      expect(fetchMock).toHaveBeenCalledTimes(2);
    },
  );

  it("rejects strict nested schema violations and referenced hash mismatches", async () => {
    const malformed = fixture();
    const malformedIndex = JSON.parse(JSON.stringify(malformed.index)) as Record<
      string,
      unknown
    >;
    const campaign = (malformedIndex.campaigns as Array<Record<string, unknown>>)[0]!;
    campaign.manifest = 42;
    malformed.resources.set("/data/index.json", JSON.stringify(malformedIndex));
    installFetch(malformed.resources);
    const first = renderHook(() => useDashboard("", "", ""));
    await waitFor(() => expect(first.result.current.error).toContain("dashboard-index is invalid"));
    expect(first.result.current.dataset).toBeUndefined();
    first.unmount();
    clearResourceCache();
    vi.unstubAllGlobals();

    const mismatched = fixture();
    const manifestPath = `/data/campaigns/${mismatched.manifest.id}/manifest.json`;
    const manifest = JSON.parse(manifestBody) as CampaignManifest;
    manifest.resources.catalog.sha256 = "f".repeat(64);
    mismatched.resources.set(manifestPath, JSON.stringify(manifest));
    installFetch(mismatched.resources);
    const second = renderHook(() => useDashboard("", "", ""));
    await waitFor(() => expect(second.result.current.error).toContain("resource hash mismatch"));
    expect(second.result.current.dataset).toBeUndefined();
  });
});
