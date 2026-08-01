import Ajv, { type AnySchema, type ValidateFunction } from "ajv";
import addFormats from "ajv-formats";
import { useCallback, useEffect, useMemo, useState } from "react";

import catalogSchema from "../../schemas/campaign-catalog.schema.json";
import evidenceSchema from "../../schemas/campaign-evidence.schema.json";
import manifestSchema from "../../schemas/campaign-manifest.schema.json";
import summarySchema from "../../schemas/campaign-summary.schema.json";
import trendsSchema from "../../schemas/campaign-trends.schema.json";
import verdictsSchema from "../../schemas/campaign-verdicts.schema.json";
import indexSchema from "../../schemas/dashboard-index.schema.json";
import type {
  Campaign,
  CampaignCatalog,
  CampaignEvidence,
  CampaignManifest,
  CampaignSummary,
  CampaignTrends,
  CampaignVerdicts,
  CountedResourceReference,
  DashboardIndex,
  Dataset,
  MetricPoint,
  ResourceReference,
  Result,
} from "./types";

interface LoadedCampaign {
  manifest: CampaignManifest;
  catalog: CampaignCatalog;
  verdicts: CampaignVerdicts;
  campaign: Campaign;
  manifestUrl: URL;
  evidenceByCase: Map<string, CountedResourceReference>;
}

interface CoreData {
  index: DashboardIndex;
  trends: CampaignTrends;
  indexUrl: URL;
}

export interface DashboardState {
  index?: DashboardIndex;
  trends?: CampaignTrends;
  dataset?: Dataset;
  selectedId?: string;
  unavailable?: CampaignSummary;
  error?: string;
  loading: boolean;
  loadCaseEvidence?: (caseId: string) => Promise<Result[]>;
}

type Validator<T> = (value: unknown) => asserts value is T;

const byteCache = new Map<string, Promise<ArrayBuffer>>();
const validatedCache = new Map<string, Promise<unknown>>();
const MAX_RESOURCE_BYTES = 128 * 1024 * 1024;
const MAX_CACHE_ENTRIES = 16;
const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);
for (const schema of [
  summarySchema,
  trendsSchema,
  manifestSchema,
  catalogSchema,
  verdictsSchema,
  evidenceSchema,
  indexSchema,
]) {
  ajv.addSchema(schema as AnySchema);
}

function compiled(schemaId: string): ValidateFunction {
  const validate = ajv.getSchema(schemaId);
  if (!validate) throw new Error(`dashboard schema ${schemaId} is unavailable`);
  return validate;
}

const schemaValidators = {
  index: compiled("dashboard-index.schema.json"),
  trends: compiled("campaign-trends.schema.json"),
  manifest: compiled("campaign-manifest.schema.json"),
  catalog: compiled("campaign-catalog.schema.json"),
  verdicts: compiled("campaign-verdicts.schema.json"),
  evidence: compiled("campaign-evidence.schema.json"),
};

function requireSchema(validate: ValidateFunction, value: unknown, label: string): void {
  if (!validate(value)) {
    const detail = validate.errors?.[0];
    throw new Error(
      `${label} is invalid${detail ? ` at ${detail.instancePath || "/"}: ${detail.message}` : ""}`,
    );
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (!record(value)) throw new Error(`${label} must be an object`);
  return value;
}

function requireArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label} must be an array`);
  return value;
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value) throw new Error(`${label} must be a string`);
  return value;
}

function requireHeader(
  value: unknown,
  kind: string,
): Record<string, unknown> {
  const item = requireRecord(value, kind);
  if (item.schema_version !== 6 || item.kind !== kind) {
    throw new Error(`expected schema version 6 ${kind}`);
  }
  return item;
}

function validateResource(value: unknown, label: string): void {
  const resource = requireRecord(value, label);
  requireString(resource.href, `${label}.href`);
  if (!/^[0-9a-f]{64}$/.test(String(resource.sha256))) {
    throw new Error(`${label}.sha256 is invalid`);
  }
  if (!Number.isSafeInteger(resource.bytes) || Number(resource.bytes) < 0) {
    throw new Error(`${label}.bytes is invalid`);
  }
}

function validateIndex(value: unknown): asserts value is DashboardIndex {
  requireSchema(schemaValidators.index, value, "dashboard-index");
  const item = requireHeader(value, "dashboard-index");
  requireString(item.default_campaign_id, "dashboard-index.default_campaign_id");
  const campaigns = requireArray(item.campaigns, "dashboard-index.campaigns");
  if (!campaigns.length) throw new Error("dashboard-index.campaigns must not be empty");
  for (const campaign of campaigns) {
    const entry = requireRecord(campaign, "dashboard campaign entry");
    requireString(entry.id, "dashboard campaign id");
    requireString(entry.manifest, "dashboard campaign manifest");
  }
  requireString(item.trends, "dashboard-index.trends");
  requireRecord(item.schemas, "dashboard-index.schemas");
}

function validateTrends(value: unknown): asserts value is CampaignTrends {
  requireSchema(schemaValidators.trends, value, "campaign-trends");
  const item = requireHeader(value, "campaign-trends");
  const campaigns = requireArray(item.campaigns, "campaign-trends.campaigns");
  for (const campaign of campaigns) {
    const summary = requireHeader(campaign, "campaign-summary");
    requireString(summary.id, "campaign-summary.id");
    requireString(summary.started_at, "campaign-summary.started_at");
    requireString(summary.finished_at, "campaign-summary.finished_at");
    requireArray(summary.tool_metrics, "campaign-summary.tool_metrics");
    requireRecord(summary.corpus_metrics, "campaign-summary.corpus_metrics");
  }
}

function validateManifest(value: unknown): asserts value is CampaignManifest {
  requireSchema(schemaValidators.manifest, value, "campaign-manifest");
  const item = requireHeader(value, "campaign-manifest");
  requireString(item.id, "campaign-manifest.id");
  requireArray(item.cases, "campaign-manifest.cases");
  requireArray(item.tools, "campaign-manifest.tools");
  requireArray(item.metrics, "campaign-manifest.metrics");
  const resources = requireRecord(item.resources, "campaign-manifest.resources");
  validateResource(resources.catalog, "campaign-manifest.resources.catalog");
  validateResource(resources.verdicts, "campaign-manifest.resources.verdicts");
  for (const resource of requireArray(
    resources.evidence,
    "campaign-manifest.resources.evidence",
  )) {
    validateResource(resource, "campaign evidence resource");
  }
}

function validateCatalog(value: unknown): asserts value is CampaignCatalog {
  requireSchema(schemaValidators.catalog, value, "campaign-catalog");
  const item = requireHeader(value, "campaign-catalog");
  requireString(item.campaign_id, "campaign-catalog.campaign_id");
  requireArray(item.requirements, "campaign-catalog.requirements");
  requireArray(item.cases, "campaign-catalog.cases");
  requireRecord(item.corpus_metrics, "campaign-catalog.corpus_metrics");
}

function validateVerdicts(value: unknown): asserts value is CampaignVerdicts {
  requireSchema(schemaValidators.verdicts, value, "campaign-verdicts");
  const item = requireHeader(value, "campaign-verdicts");
  requireString(item.campaign_id, "campaign-verdicts.campaign_id");
  for (const itemCase of requireArray(item.cases, "campaign-verdicts.cases")) {
    const caseVerdicts = requireRecord(itemCase, "campaign verdict case");
    requireString(caseVerdicts.case_id, "campaign verdict case id");
    requireString(caseVerdicts.evidence_href, "campaign verdict evidence href");
    requireArray(caseVerdicts.results, "campaign verdict results");
  }
}

function validateEvidence(value: unknown): asserts value is CampaignEvidence {
  requireSchema(schemaValidators.evidence, value, "campaign-evidence");
  const item = requireHeader(value, "campaign-evidence");
  requireString(item.campaign_id, "campaign-evidence.campaign_id");
  requireArray(item.case_ids, "campaign-evidence.case_ids");
  requireArray(item.results, "campaign-evidence.results");
}

async function sha256(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function remember<K, V>(cache: Map<K, V>, key: K, value: V): void {
  cache.set(key, value);
  while (cache.size > MAX_CACHE_ENTRIES) {
    const oldest = cache.keys().next().value as K | undefined;
    if (oldest === undefined) break;
    cache.delete(oldest);
  }
}

async function fetchBytes(url: URL, maximum: number): Promise<ArrayBuffer> {
  const key = url.toString();
  let pending = byteCache.get(key);
  if (!pending) {
    pending = (async () => {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
      const declared = Number(response.headers.get("Content-Length"));
      if (Number.isFinite(declared) && declared > maximum) {
        throw new Error(`${url.pathname}: resource exceeds size limit`);
      }
      if (!response.body) {
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > maximum) {
          throw new Error(`${url.pathname}: resource exceeds size limit`);
        }
        return bytes;
      }
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let received = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        received += value.byteLength;
        if (received > maximum) {
          await reader.cancel();
          throw new Error(`${url.pathname}: resource exceeds size limit`);
        }
        chunks.push(value);
      }
      const joined = new Uint8Array(received);
      let offset = 0;
      for (const chunk of chunks) {
        joined.set(chunk, offset);
        offset += chunk.byteLength;
      }
      return joined.buffer;
    })();
    remember(byteCache, key, pending);
    pending.catch(() => byteCache.delete(key));
  }
  return pending;
}

const validatorIds = new WeakMap<object, number>();
let nextValidatorId = 0;

function validatorId(validate: Validator<unknown>): number {
  const key = validate as unknown as object;
  const existing = validatorIds.get(key);
  if (existing !== undefined) return existing;
  nextValidatorId += 1;
  validatorIds.set(key, nextValidatorId);
  return nextValidatorId;
}

async function fetchResource<T>(
  url: URL,
  validate: Validator<T>,
  expected?: ResourceReference,
): Promise<T> {
  if (expected && expected.bytes > MAX_RESOURCE_BYTES) {
    throw new Error(`${url.pathname}: resource exceeds size limit`);
  }
  const cacheKey = [
    url.toString(),
    expected?.bytes ?? "unreferenced",
    expected?.sha256 ?? "unreferenced",
    validatorId(validate as Validator<unknown>),
  ].join("|");
  let pending = validatedCache.get(cacheKey);
  if (!pending) {
    pending = (async () => {
      const bytes = await fetchBytes(url, expected?.bytes ?? MAX_RESOURCE_BYTES);
      if (expected) {
        if (bytes.byteLength !== expected.bytes) {
          throw new Error(`${url.pathname}: resource size mismatch`);
        }
        if ((await sha256(bytes)) !== expected.sha256) {
          throw new Error(`${url.pathname}: resource hash mismatch`);
        }
      }
      let value: unknown;
      try {
        value = JSON.parse(new TextDecoder().decode(bytes));
      } catch {
        throw new Error(`${url.pathname}: invalid JSON`);
      }
      validate(value);
      return value;
    })();
    remember(validatedCache, cacheKey, pending);
    pending.catch(() => validatedCache.delete(cacheKey));
  }
  return (await pending) as T;
}

function resolve(href: string, owner: URL): URL {
  let decoded: string;
  try {
    decoded = decodeURIComponent(href);
  } catch {
    throw new Error(`unsafe relative dashboard resource path: ${href}`);
  }
  const segments = decoded.split("/");
  if (
    !decoded ||
    decoded.startsWith("/") ||
    decoded.includes("\\") ||
    decoded.includes("\0") ||
    decoded.includes("?") ||
    decoded.includes("#") ||
    segments.some((segment) => !segment || segment === "." || segment === "..")
  ) {
    throw new Error(`unsafe relative dashboard resource path: ${href}`);
  }
  const resolved = new URL(href, owner);
  const ownerDirectory = new URL(".", owner);
  if (
    resolved.origin !== owner.origin ||
    !resolved.pathname.startsWith(ownerDirectory.pathname)
  ) {
    throw new Error(`cross-origin or escaping dashboard resource path: ${href}`);
  }
  return resolved;
}

function metricPoint(
  metric: CampaignManifest["metrics"][number],
  manifest: CampaignManifest,
): MetricPoint {
  return {
    ...metric,
    campaign_id: manifest.id,
    timestamp: manifest.finished_at,
    repository_commit: manifest.repository.commit,
  };
}

function compactCampaign(
  manifest: CampaignManifest,
  catalog: CampaignCatalog,
  verdicts: CampaignVerdicts,
): Campaign {
  const cases = new Map(catalog.cases.map((item) => [item.id, item]));
  const results = verdicts.cases.flatMap((item) => {
    const testCase = cases.get(item.case_id);
    if (!testCase) throw new Error(`verdict references unknown case ${item.case_id}`);
    return item.results.map(
      (verdict): Result => ({
        case_id: item.case_id,
        requirement_id: testCase.primary_requirement,
        tool_id: verdict.tool_id,
        profile_id: verdict.profile_id,
        target_phase: testCase.target_phase,
        evidence_mode: verdict.evidence_mode,
        status: verdict.status,
        reason: verdict.reason,
        summary: verdict.summary,
        evidence: testCase.evidence,
        observations: [],
        ...(verdict.known_issue !== undefined
          ? { known_issue: verdict.known_issue }
          : {}),
        reproduction_command: null,
      }),
    );
  });
  return {
    schema_version: 5,
    id: manifest.id,
    started_at: manifest.started_at,
    finished_at: manifest.finished_at,
    repository: manifest.repository,
    platform: manifest.platform,
    selection_name: manifest.selection_name,
    case_ids: manifest.cases.map((item) => item.id),
    tools: manifest.tools,
    expected_tool_ids: manifest.expected_tool_ids,
    missing_tool_ids: manifest.missing_tool_ids,
    hashes: manifest.hashes,
    corpus_metrics: manifest.corpus_metrics,
    results,
    complete: manifest.complete,
    trust: manifest.trust,
  };
}

async function loadManifest(
  core: CoreData,
  id: string,
): Promise<{ manifest: CampaignManifest; manifestUrl: URL }> {
  const entry = core.index.campaigns.find((campaign) => campaign.id === id);
  if (!entry) throw new Error(`campaign ${id} has no local detail`);
  const manifestUrl = resolve(entry.manifest, core.indexUrl);
  const manifest = await fetchResource(manifestUrl, validateManifest);
  if (manifest.id !== id) throw new Error(`manifest identity mismatch for ${id}`);
  return { manifest, manifestUrl };
}

async function loadCampaign(
  core: CoreData,
  id: string,
  known?: { manifest: CampaignManifest; manifestUrl: URL },
): Promise<LoadedCampaign> {
  const { manifest, manifestUrl } = known ?? (await loadManifest(core, id));
  const catalogUrl = resolve(manifest.resources.catalog.href, manifestUrl);
  const verdictsUrl = resolve(manifest.resources.verdicts.href, manifestUrl);
  const [catalog, verdicts] = await Promise.all([
    fetchResource(catalogUrl, validateCatalog, manifest.resources.catalog),
    fetchResource(verdictsUrl, validateVerdicts, manifest.resources.verdicts),
  ]);
  if (catalog.campaign_id !== id || verdicts.campaign_id !== id) {
    throw new Error(`campaign resource identity mismatch for ${id}`);
  }
  const resources = new Map(
    manifest.resources.evidence.map((resource) => [resource.href, resource]),
  );
  const evidenceByCase = new Map<string, CountedResourceReference>();
  for (const item of verdicts.cases) {
    const resource = resources.get(item.evidence_href);
    if (!resource) throw new Error(`case ${item.case_id} references unknown evidence`);
    evidenceByCase.set(item.case_id, resource);
  }
  return {
    manifest,
    catalog,
    verdicts,
    campaign: compactCampaign(manifest, catalog, verdicts),
    manifestUrl,
    evidenceByCase,
  };
}

function metricProfileSignature(
  metrics: Array<{ tool_id: string; profile_id: string }>,
): string {
  return metrics
    .map((metric) => `${metric.tool_id}/${metric.profile_id}`)
    .sort()
    .join("|");
}

async function loadPreviousComparable(
  core: CoreData,
  selected: { manifest: CampaignManifest; manifestUrl: URL },
): Promise<LoadedCampaign | undefined> {
  const signature = metricProfileSignature(selected.manifest.metrics);
  const candidate = core.trends.campaigns
    .filter(
      (campaign) =>
        core.index.campaigns.some((entry) => entry.id === campaign.id) &&
        metricProfileSignature(campaign.tool_metrics) === signature &&
        (campaign.finished_at < selected.manifest.finished_at ||
          (campaign.finished_at === selected.manifest.finished_at &&
            campaign.id < selected.manifest.id)),
    )
    .sort(
      (left, right) =>
        right.finished_at.localeCompare(left.finished_at) || right.id.localeCompare(left.id),
    )[0];
  return candidate ? loadCampaign(core, candidate.id) : undefined;
}

function availableSummaries(
  core: CoreData,
  dateFrom: string,
  dateTo: string,
): CampaignSummary[] {
  const available = new Set(core.index.campaigns.map((campaign) => campaign.id));
  return core.trends.campaigns
    .filter((campaign) => {
      const date = campaign.finished_at.slice(0, 10);
      return (
        available.has(campaign.id) &&
        (!dateFrom || date >= dateFrom) &&
        (!dateTo || date <= dateTo)
      );
    })
    .sort(
      (left, right) =>
        right.finished_at.localeCompare(left.finished_at) || right.id.localeCompare(left.id),
    );
}

function datasetFrom(
  core: CoreData,
  selected: LoadedCampaign,
  previous?: LoadedCampaign,
): Dataset {
  const loaded = previous ? [selected, previous] : [selected];
  return {
    schema_version: 5,
    generated_from: loaded.map((item) => item.manifest.id),
    visibility: core.trends.campaigns.every((campaign) => campaign.archive)
      ? "public"
      : "local",
    corpus_coverage: selected.catalog.corpus_metrics,
    requirements: selected.catalog.requirements,
    cases: selected.catalog.cases,
    campaigns: loaded.map((item) => item.campaign),
    metrics: loaded.flatMap((item) =>
      item.manifest.metrics.map((metric) => metricPoint(metric, item.manifest)),
    ),
  };
}

export function useDashboard(
  requestedCampaignId: string,
  dateFrom: string,
  dateTo: string,
  ignoreDateRange = false,
  loadDetail = true,
  loadComparison = false,
): DashboardState {
  const [core, setCore] = useState<CoreData>();
  const [coreError, setCoreError] = useState<string>();
  const [selection, setSelection] = useState<{
    dataset: Dataset;
    loaded: LoadedCampaign;
  }>();
  const [selectionError, setSelectionError] = useState<string>();
  const [selectionLoading, setSelectionLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const indexUrl = new URL("./data/index.json", window.location.href);
    fetchResource(indexUrl, validateIndex)
      .then(async (index) => ({
        index,
        trends: await fetchResource(resolve(index.trends, indexUrl), validateTrends),
        indexUrl,
      }))
      .then((value) => {
        if (active) setCore(value);
      })
      .catch((error: unknown) => {
        if (active) setCoreError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      active = false;
    };
  }, []);

  const summaries = useMemo(
    () =>
      core
        ? availableSummaries(
            core,
            ignoreDateRange ? "" : dateFrom,
            ignoreDateRange ? "" : dateTo,
          )
        : [],
    [core, dateFrom, dateTo, ignoreDateRange],
  );
  const requestedAvailable = core?.index.campaigns.some(
    (campaign) => campaign.id === requestedCampaignId,
  );
  const selectedId = requestedCampaignId
    ? requestedAvailable
      ? requestedCampaignId
      : undefined
    : summaries[0]?.id;
  const unavailable =
    requestedCampaignId && core && !requestedAvailable
      ? core.trends.campaigns.find((campaign) => campaign.id === requestedCampaignId)
      : undefined;

  useEffect(() => {
    setSelection(undefined);
    if (!core || !selectedId || !loadDetail) {
      setSelectionError(undefined);
      setSelectionLoading(false);
      return;
    }
    let active = true;
    setSelectionLoading(true);
    setSelectionError(undefined);
    loadManifest(core, selectedId)
      .then(async (known) => {
        const loaded = await loadCampaign(core, selectedId, known);
        const previous = loadComparison
          ? await loadPreviousComparable(core, known)
          : undefined;
        return { loaded, previous };
      })
      .then(({ loaded, previous }) => {
        if (active) setSelection({ dataset: datasetFrom(core, loaded, previous), loaded });
      })
      .catch((error: unknown) => {
        if (active) setSelectionError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (active) setSelectionLoading(false);
      });
    return () => {
      active = false;
    };
  }, [core, loadComparison, loadDetail, selectedId]);

  const loadCaseEvidence = useCallback(
    async (caseId: string): Promise<Result[]> => {
      const loaded =
        selection && selection.loaded.manifest.id === selectedId
          ? selection.loaded
          : undefined;
      if (!loaded) throw new Error("campaign detail is not loaded");
      const resource = loaded.evidenceByCase.get(caseId);
      if (!resource) throw new Error(`case ${caseId} has no evidence resource`);
      const evidence = await fetchResource(
        resolve(resource.href, loaded.manifestUrl),
        validateEvidence,
        resource,
      );
      if (evidence.campaign_id !== loaded.manifest.id || !evidence.case_ids.includes(caseId)) {
        throw new Error(`evidence identity mismatch for ${caseId}`);
      }
      return evidence.results
        .filter((result) => result.case_id === caseId)
        .map((result) => ({
          ...result,
          reproduction_command: `just reproduce '${loaded.manifestUrl.toString()}' '${result.tool_id}' '${result.profile_id}' '${caseId}'`,
        }));
    },
    [selectedId, selection],
  );

  const currentSelection =
    loadDetail && selection?.loaded.manifest.id === selectedId ? selection : undefined;
  const error = coreError ?? selectionError;
  return {
    ...(core ? { index: core.index, trends: core.trends } : {}),
    ...(currentSelection ? { dataset: currentSelection.dataset } : {}),
    ...(selectedId ? { selectedId } : {}),
    ...(unavailable ? { unavailable } : {}),
    ...(error ? { error } : {}),
    loading: !core && !coreError ? true : selectionLoading,
    ...(currentSelection ? { loadCaseEvidence } : {}),
  };
}

export function clearResourceCache(): void {
  byteCache.clear();
  validatedCache.clear();
}
