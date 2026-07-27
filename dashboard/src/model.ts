import type {
  Campaign,
  CaseDefinition,
  Dataset,
  MetricPoint,
  Requirement,
  Result,
  Status,
} from "./types";

export const STATUS_LABELS: Record<Status, string> = {
  conforming: "Pass",
  nonconforming: "Fail",
  inconclusive: "Unclear",
  "unsupported-capability": "Not applicable",
  "unsupported-revision": "Not applicable · revision",
  "not-applicable": "Not applicable",
  "skipped-unavailable": "Not evaluated · tool unavailable",
  "harness-error": "Infra error",
  "not-run": "Not evaluated · not run",
};

export function standardLocationLabel(location: string): string {
  return /^[A-Q](?:\.|$)/.test(location) ? `Annex ${location}` : `Clause ${location}`;
}

export const STATUS_SYMBOLS: Record<Status, string> = {
  conforming: "✓",
  nonconforming: "×",
  inconclusive: "?",
  "unsupported-capability": "—",
  "unsupported-revision": "—",
  "not-applicable": "○",
  "skipped-unavailable": "·",
  "harness-error": "!",
  "not-run": "·",
};

export type StatusGroup =
  | "pass"
  | "fail"
  | "not-applicable"
  | "unclear"
  | "infra"
  | "not-evaluated";

export const STATUS_GROUP_LABELS: Record<StatusGroup, string> = {
  pass: "Pass",
  fail: "Fail",
  "not-applicable": "Not applicable",
  unclear: "Unclear",
  infra: "Infra error",
  "not-evaluated": "Not evaluated",
};

export const STATUS_GROUP_SYMBOLS: Record<StatusGroup, string> = {
  pass: "✓",
  fail: "×",
  "not-applicable": "○",
  unclear: "?",
  infra: "!",
  "not-evaluated": "·",
};

export const STATUS_GROUP_ORDER: StatusGroup[] = [
  "pass",
  "fail",
  "not-applicable",
  "unclear",
  "infra",
  "not-evaluated",
];

export function statusGroup(status: Status): StatusGroup {
  switch (status) {
    case "conforming":
      return "pass";
    case "nonconforming":
      return "fail";
    case "unsupported-capability":
    case "unsupported-revision":
    case "not-applicable":
      return "not-applicable";
    case "inconclusive":
      return "unclear";
    case "harness-error":
      return "infra";
    case "skipped-unavailable":
    case "not-run":
      return "not-evaluated";
  }
}

const STATUS_PRIORITY: Status[] = [
  "harness-error",
  "nonconforming",
  "inconclusive",
  "unsupported-revision",
  "unsupported-capability",
  "skipped-unavailable",
  "not-applicable",
  "conforming",
  "not-run",
];

export interface Filters {
  search: string;
  revision: string;
  part: string;
  clause: string;
  phase: string;
  expectation: string;
  casePresence: string;
  tag: string;
  requirement: string;
  tool: string;
  profile: string;
  statusGroup: string;
  status: string;
  reason: string;
  campaign: string;
  dateFrom: string;
  dateTo: string;
  caseId: string;
  requirementId: string;
  changed: boolean;
  disagreement: boolean;
}

export const EMPTY_FILTERS: Filters = {
  search: "",
  revision: "",
  part: "",
  clause: "",
  phase: "",
  expectation: "",
  casePresence: "",
  tag: "",
  requirement: "",
  tool: "",
  profile: "",
  statusGroup: "",
  status: "",
  reason: "",
  campaign: "",
  dateFrom: "",
  dateTo: "",
  caseId: "",
  requirementId: "",
  changed: false,
  disagreement: false,
};

export type TrendKind = "pass-rate" | "coverage" | "density";

export type TrendRange =
  | "week"
  | "month"
  | "three-months"
  | "six-months"
  | "year"
  | "all";

export interface TrendState {
  kind: TrendKind;
  range: TrendRange;
  point: string;
  parts: string[];
}

export const DEFAULT_TREND_STATE: TrendState = {
  kind: "pass-rate",
  range: "all",
  point: "",
  parts: [],
};

const TREND_KINDS = new Set<TrendKind>(["pass-rate", "coverage", "density"]);
const TREND_PART_KEY = /^(?:chapter:[1-9][0-9]*|annex:[A-Q])$/;
const TREND_PART_PARAMETER = "trendPart";
const TREND_RANGES = new Set<TrendRange>([
  "week",
  "month",
  "three-months",
  "six-months",
  "year",
  "all",
]);
const DAY_MS = 24 * 60 * 60 * 1000;
const PROJECT_START = Date.UTC(2026, 6, 1);

export function trendStateFromSearch(search: string): TrendState {
  const parameters = new URLSearchParams(search);
  const requestedKind = parameters.get("trend") as TrendKind | null;
  const requestedRange = parameters.get("trendRange") as TrendRange | null;
  return {
    kind:
      requestedKind && TREND_KINDS.has(requestedKind)
        ? requestedKind
        : DEFAULT_TREND_STATE.kind,
    range:
      requestedRange && TREND_RANGES.has(requestedRange)
        ? requestedRange
        : DEFAULT_TREND_STATE.range,
    point: parameters.get("trendPoint") ?? "",
    parts: [
      ...new Set(
        parameters
          .getAll(TREND_PART_PARAMETER)
          .filter((part) => TREND_PART_KEY.test(part)),
      ),
    ],
  };
}

export function toolTrendPointKey(point: MetricPoint): string {
  return `tool:${point.campaign_id}:${point.tool_id}:${point.profile_id}`;
}

export function corpusTrendPointKey(
  campaign: Campaign,
  scope: "requirements" | "cases",
): string {
  return `corpus:${campaign.id}:${scope}`;
}

function subtractUtcMonths(timestamp: number, months: number): number {
  const date = new Date(timestamp);
  const monthIndex = date.getUTCFullYear() * 12 + date.getUTCMonth() - months;
  const year = Math.floor(monthIndex / 12);
  const month = ((monthIndex % 12) + 12) % 12;
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  return Date.UTC(year, month, Math.min(date.getUTCDate(), lastDay));
}

export function trendRangeBounds(
  points: Array<{ timestamp: string }>,
  range: TrendRange,
  now: Date,
): {
  domainStart: number;
  domainEnd: number;
  rangeStart: number;
  rangeEnd: number;
} {
  const today = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  );
  const domainEnd = today + DAY_MS;
  const timestamps = points
    .map((point) => Date.parse(point.timestamp))
    .filter((timestamp) => Number.isFinite(timestamp));
  const earliest = timestamps.length ? new Date(Math.min(...timestamps)) : null;
  const earliestDay = earliest
    ? Date.UTC(
        earliest.getUTCFullYear(),
        earliest.getUTCMonth(),
        earliest.getUTCDate(),
      )
    : PROJECT_START;
  const domainStart = Math.min(PROJECT_START, earliestDay);
  let requestedStart: number;
  switch (range) {
    case "week":
      requestedStart = domainEnd - 7 * DAY_MS;
      break;
    case "month":
      requestedStart = subtractUtcMonths(today, 1);
      break;
    case "three-months":
      requestedStart = subtractUtcMonths(today, 3);
      break;
    case "six-months":
      requestedStart = subtractUtcMonths(today, 6);
      break;
    case "year":
      requestedStart = subtractUtcMonths(today, 12);
      break;
    case "all":
      requestedStart = domainStart;
      break;
  }
  return {
    domainStart,
    domainEnd,
    rangeStart: Math.max(domainStart, requestedStart),
    rangeEnd: domainEnd,
  };
}

export function filtersFromSearch(search: string): Filters {
  const parameters = new URLSearchParams(search);
  const result = { ...EMPTY_FILTERS };
  for (const key of Object.keys(EMPTY_FILTERS) as (keyof Filters)[]) {
    if (key === "changed" || key === "disagreement") {
      result[key] = parameters.get(key) === "1";
    } else {
      result[key] = parameters.get(key) ?? "";
    }
  }
  return result;
}

export function filtersToSearch(
  filters: Filters,
  view: string,
  trend: TrendState = DEFAULT_TREND_STATE,
): string {
  const parameters = new URLSearchParams();
  parameters.set("view", view);
  for (const [key, value] of Object.entries(filters)) {
    if (value === false || value === "") continue;
    parameters.set(key, value === true ? "1" : String(value));
  }
  if (view === "trends") {
    if (trend.kind !== DEFAULT_TREND_STATE.kind) {
      parameters.set("trend", trend.kind);
    }
    if (trend.range !== DEFAULT_TREND_STATE.range) {
      parameters.set("trendRange", trend.range);
    }
    if (trend.point) parameters.set("trendPoint", trend.point);
    for (const part of trend.parts) parameters.append(TREND_PART_PARAMETER, part);
  }
  return `?${parameters.toString()}`;
}

export function campaignsInDateRange(
  dataset: Dataset,
  dateFrom: string,
  dateTo: string,
): Campaign[] {
  return [...dataset.campaigns]
    .filter((campaign) => {
      const date = campaign.finished_at.slice(0, 10);
      return (!dateFrom || date >= dateFrom) && (!dateTo || date <= dateTo);
    })
    .sort((left, right) => right.finished_at.localeCompare(left.finished_at));
}

export function selectedCampaign(
  dataset: Dataset,
  campaignId: string,
  dateFrom = "",
  dateTo = "",
): Campaign | undefined {
  const campaigns = campaignsInDateRange(dataset, dateFrom, dateTo);
  return campaigns.find((campaign) => campaign.id === campaignId) ?? campaigns[0];
}

export interface StatusTransition {
  caseId: string;
  toolId: string;
  profileId: string;
  previous: Status;
  current: Status;
}

export interface ToolRevisionChange {
  toolId: string;
  previous: string;
  current: string;
}

export interface CampaignComparison {
  previousCampaignId?: string | undefined;
  regressions: StatusTransition[];
  newPasses: StatusTransition[];
  otherChanges: StatusTransition[];
  toolRevisionChanges: ToolRevisionChange[];
  corpusChanged: boolean;
  denominatorChanged: boolean;
}

function campaignProfileSignature(campaign: Campaign): string {
  return campaign.tools
    .flatMap((tool) =>
      tool.profile_ids.map((profileId) => {
        const profile = tool.definition.profiles.find((item) => item.id === profileId);
        if (!profile) return `${tool.definition.id}/${profileId}/invalid`;
        return [
          tool.definition.id,
          profileId,
          profile.standard_revision,
          profile.phase_ceiling,
          profile.direct_phases.join(","),
        ].join("/");
      }),
    )
    .sort()
    .join("|");
}

export function previousComparableCampaign(
  dataset: Dataset,
  selected: Campaign | undefined,
): Campaign | undefined {
  if (!selected) return undefined;
  const signature = campaignProfileSignature(selected);
  return dataset.campaigns
    .filter(
      (campaign) =>
        campaign.finished_at < selected.finished_at &&
        campaignProfileSignature(campaign) === signature,
    )
    .sort((left, right) => right.finished_at.localeCompare(left.finished_at))[0];
}

export function compareCampaigns(
  dataset: Dataset,
  selected: Campaign | undefined,
): CampaignComparison {
  const previous = previousComparableCampaign(dataset, selected);
  const empty = {
    previousCampaignId: previous?.id,
    regressions: [],
    newPasses: [],
    otherChanges: [],
    toolRevisionChanges: [],
    corpusChanged: false,
    denominatorChanged: false,
  } satisfies CampaignComparison;
  if (!selected || !previous) return empty;

  const priorResults = resultsByKey(previous);
  const regressions: StatusTransition[] = [];
  const newPasses: StatusTransition[] = [];
  const otherChanges: StatusTransition[] = [];
  for (const result of selected.results) {
    const prior = priorResults.get(resultKey(result));
    if (!prior || prior.status === result.status) continue;
    const transition = {
      caseId: result.case_id,
      toolId: result.tool_id,
      profileId: result.profile_id,
      previous: prior.status,
      current: result.status,
    };
    if (statusGroup(prior.status) === "pass" && statusGroup(result.status) !== "pass") {
      regressions.push(transition);
    } else if (
      statusGroup(prior.status) !== "pass" &&
      statusGroup(result.status) === "pass"
    ) {
      newPasses.push(transition);
    } else {
      otherChanges.push(transition);
    }
  }

  const priorTools = new Map(previous.tools.map((tool) => [tool.definition.id, tool]));
  const toolRevisionChanges = selected.tools.flatMap((tool): ToolRevisionChange[] => {
    const prior = priorTools.get(tool.definition.id);
    const priorRevision = prior?.selection?.resolved_sha ?? prior?.reported_version ?? "local";
    const currentRevision =
      tool.selection?.resolved_sha ?? tool.reported_version ?? "local";
    return prior && priorRevision !== currentRevision
      ? [{ toolId: tool.definition.id, previous: priorRevision, current: currentRevision }]
      : [];
  });
  const priorDenominators = new Map(
    dataset.metrics
      .filter((metric) => metric.campaign_id === previous.id)
      .map((metric) => [`${metric.tool_id}/${metric.profile_id}`, metric.denominator]),
  );
  const denominatorChanged = dataset.metrics
    .filter((metric) => metric.campaign_id === selected.id)
    .some(
      (metric) =>
        priorDenominators.get(`${metric.tool_id}/${metric.profile_id}`) !==
        metric.denominator,
    );

  return {
    previousCampaignId: previous.id,
    regressions,
    newPasses,
    otherChanges,
    toolRevisionChanges,
    corpusChanged:
      selected.hashes.cases !== previous.hashes.cases ||
      selected.hashes.requirements !== previous.hashes.requirements,
    denominatorChanged,
  };
}

export function resultKey(result: Result): string {
  return `${result.case_id}:${result.tool_id}:${result.profile_id}`;
}

export function resultsByKey(campaign: Campaign | undefined): Map<string, Result> {
  return new Map((campaign?.results ?? []).map((result) => [resultKey(result), result]));
}

export function aggregateStatus(results: Array<Result | undefined>): Status {
  const statuses = new Set(results.filter(Boolean).map((result) => result?.status as Status));
  if (!statuses.size) return "not-run";
  return STATUS_PRIORITY.find((status) => statuses.has(status)) ?? "not-run";
}

export function profileKeys(campaign: Campaign | undefined): string[] {
  if (!campaign) return [];
  return campaign.tools.flatMap((tool) =>
    tool.profile_ids.map((profile) => `${tool.definition.id}/${profile}`),
  );
}

export function changedCaseKeys(
  dataset: Dataset,
  selected: Campaign | undefined,
): Set<string> {
  const previousCampaign = previousComparableCampaign(dataset, selected);
  if (!selected || !previousCampaign) return new Set();
  const latest = resultsByKey(selected);
  const previous = resultsByKey(previousCampaign);
  const changed = new Set<string>();
  for (const [key, result] of latest) {
    const prior = previous.get(key);
    if (prior && prior.status !== result.status) changed.add(result.case_id);
  }
  return changed;
}

export function disagreementCaseKeys(campaign: Campaign | undefined): Set<string> {
  const statuses = new Map<string, Set<Status>>();
  for (const result of campaign?.results ?? []) {
    const values = statuses.get(result.case_id) ?? new Set<Status>();
    values.add(result.status);
    statuses.set(result.case_id, values);
  }
  return new Set(
    [...statuses.entries()]
      .filter(([, values]) => values.size > 1)
      .map(([caseId]) => caseId),
  );
}

export function filterCorpus(
  dataset: Dataset,
  filters: Filters,
  campaign: Campaign | undefined,
): {
  requirements: Requirement[];
  cases: CaseDefinition[];
  requirementCases: CaseDefinition[];
} {
  const changed = changedCaseKeys(dataset, campaign);
  const disagreement = disagreementCaseKeys(campaign);
  const resultMap = resultsByKey(campaign);
  const requirementMap = new Map(
    dataset.requirements.map((requirement) => [requirement.id, requirement]),
  );
  const allCasesByRequirement = new Map<string, CaseDefinition[]>();
  for (const testCase of dataset.cases) {
    for (const requirementId of new Set([
      testCase.primary_requirement,
      ...testCase.related_requirements,
    ])) {
      const linked = allCasesByRequirement.get(requirementId) ?? [];
      linked.push(testCase);
      allCasesByRequirement.set(requirementId, linked);
    }
  }
  const needle = filters.search.toLocaleLowerCase();
  const candidateResultsByCase = new Map<string, Result[]>();
  for (const result of resultMap.values()) {
    if (
      (!filters.tool || result.tool_id === filters.tool) &&
      (!filters.profile || result.profile_id === filters.profile)
    ) {
      const values = candidateResultsByCase.get(result.case_id) ?? [];
      values.push(result);
      candidateResultsByCase.set(result.case_id, values);
    }
  }
  const matchesCase = (
    testCase: CaseDefinition,
    contextRequirements: Requirement[],
  ) => {
    const candidateResults = candidateResultsByCase.get(testCase.id) ?? [];
    const searchable = [
      testCase.id,
      testCase.title,
      testCase.description,
      ...contextRequirements.flatMap((requirement) => [
        requirement.id,
        requirement.summary,
        requirement.clause,
        ...requirement.anchors,
      ]),
      ...testCase.tags,
      ...candidateResults.flatMap((result) => [
        result.status,
        result.reason,
        result.summary,
        ...result.observations.flatMap((observation) => [
          observation.stdout.excerpt,
          observation.stderr.excerpt,
          ...observation.diagnostics.map((diagnostic) => diagnostic.message),
        ]),
      ]),
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!filters.requirement ||
        testCase.primary_requirement === filters.requirement ||
        testCase.related_requirements.includes(filters.requirement)) &&
      (!needle || searchable.includes(needle)) &&
      (!filters.revision ||
        testCase.revision_applicability[filters.revision] === "applicable" ||
        testCase.revision_applicability[filters.revision] ===
          "same-rule-different-clause") &&
      (!filters.part ||
        contextRequirements.some((requirement) => requirement.part === filters.part)) &&
      (!filters.clause ||
        contextRequirements.some((requirement) =>
          requirement.clause.startsWith(filters.clause),
        )) &&
      (!filters.phase || testCase.target_phase === filters.phase) &&
      (!filters.expectation || testCase.expectation === filters.expectation) &&
      (!filters.tag ||
        testCase.tags.includes(filters.tag) ||
        contextRequirements.some((requirement) =>
          requirement.tags.includes(filters.tag),
        )) &&
      (!filters.statusGroup ||
        candidateResults.some(
          (result) => statusGroup(result.status) === filters.statusGroup,
        )) &&
      (!filters.status ||
        candidateResults.some((result) => result.status === filters.status)) &&
      (!filters.reason ||
        candidateResults.some((result) => result.reason === filters.reason)) &&
      (!filters.changed || changed.has(testCase.id)) &&
      (!filters.disagreement || disagreement.has(testCase.id))
    );
  };
  const cases = dataset.cases.filter((testCase) => {
    const context = filters.requirement
      ? [...new Set([testCase.primary_requirement, ...testCase.related_requirements])]
          .map((id) => requirementMap.get(id))
          .filter((requirement): requirement is Requirement => Boolean(requirement))
      : [requirementMap.get(testCase.primary_requirement)].filter(
          (requirement): requirement is Requirement => Boolean(requirement),
        );
    return matchesCase(testCase, context);
  });
  const requirementCases = dataset.cases.filter((testCase) =>
    matchesCase(
      testCase,
      [...new Set([testCase.primary_requirement, ...testCase.related_requirements])]
        .map((id) => requirementMap.get(id))
        .filter((requirement): requirement is Requirement => Boolean(requirement)),
    ),
  );
  const matchedCaseIds = new Set(
    requirementCases.map((testCase) => testCase.id),
  );
  const caseSpecificFilter = Boolean(
    filters.phase ||
      filters.expectation ||
      filters.statusGroup ||
      filters.status ||
      filters.reason ||
      filters.changed ||
      filters.disagreement,
  );
  const requirements = dataset.requirements.filter((requirement) => {
    const linkedCases = allCasesByRequirement.get(requirement.id) ?? [];
    const matchingCases = linkedCases.filter((testCase) => matchedCaseIds.has(testCase.id));
    const hasCases = linkedCases.length > 0;
    const rule = filters.revision
      ? requirement.revision_applicability[filters.revision]
      : undefined;
    const searchable = [
      requirement.id,
      requirement.summary,
      requirement.clause,
      ...requirement.anchors,
      ...requirement.tags,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!filters.requirement || requirement.id === filters.requirement) &&
      (!needle || searchable.includes(needle) || matchingCases.length > 0) &&
      (!filters.revision ||
        rule?.status === "applicable" ||
        rule?.status === "same-rule-different-clause") &&
      (!filters.part || requirement.part === filters.part) &&
      (!filters.clause || requirement.clause.startsWith(filters.clause)) &&
      (!filters.casePresence ||
        (filters.casePresence === "with-cases" ? hasCases : !hasCases)) &&
      (!filters.tag ||
        requirement.tags.includes(filters.tag) ||
        matchingCases.some((testCase) => testCase.tags.includes(filters.tag))) &&
      (!caseSpecificFilter || matchingCases.length > 0)
    );
  });
  const requirementIds = new Set(requirements.map((requirement) => requirement.id));
  return {
    requirements,
    cases: cases.filter((testCase) =>
      filters.requirement
        ? [testCase.primary_requirement, ...testCase.related_requirements].some(
            (id) => requirementIds.has(id),
          )
        : requirementIds.has(testCase.primary_requirement),
    ),
    requirementCases: requirementCases.filter((testCase) =>
      [testCase.primary_requirement, ...testCase.related_requirements].some((id) =>
        requirementIds.has(id),
      ),
    ),
  };
}
