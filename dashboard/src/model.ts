import type {
  Campaign,
  CaseDefinition,
  Dataset,
  Requirement,
  Result,
  Status,
} from "./types";

export const STATUS_LABELS: Record<Status, string> = {
  conforming: "Pass",
  nonconforming: "Fail",
  inconclusive: "Inconclusive",
  "unsupported-capability": "Unsupported",
  "unsupported-revision": "Unsupported revision",
  "not-applicable": "Not applicable",
  "skipped-unavailable": "Not run",
  "harness-error": "Harness error",
  "not-run": "Not run",
};

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
  chapter: string;
  clause: string;
  phase: string;
  expectation: string;
  casePresence: string;
  tag: string;
  tool: string;
  status: string;
  reason: string;
  campaign: string;
  date: string;
  changed: boolean;
  disagreement: boolean;
}

export const EMPTY_FILTERS: Filters = {
  search: "",
  revision: "",
  chapter: "",
  clause: "",
  phase: "",
  expectation: "",
  casePresence: "",
  tag: "",
  tool: "",
  status: "",
  reason: "",
  campaign: "",
  date: "",
  changed: false,
  disagreement: false,
};

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

export function filtersToSearch(filters: Filters, view: string): string {
  const parameters = new URLSearchParams();
  parameters.set("view", view);
  for (const [key, value] of Object.entries(filters)) {
    if (value === false || value === "") continue;
    parameters.set(key, value === true ? "1" : String(value));
  }
  return `?${parameters.toString()}`;
}

export function selectedCampaign(dataset: Dataset, campaignId: string): Campaign | undefined {
  if (campaignId) {
    return dataset.campaigns.find((campaign) => campaign.id === campaignId);
  }
  return [...dataset.campaigns].sort((left, right) =>
    right.finished_at.localeCompare(left.finished_at),
  )[0];
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
  const campaigns = [...dataset.campaigns].sort((left, right) =>
    left.finished_at.localeCompare(right.finished_at),
  );
  const selectedIndex = selected
    ? campaigns.findIndex((campaign) => campaign.id === selected.id)
    : campaigns.length - 1;
  if (selectedIndex <= 0) return new Set();
  const latest = resultsByKey(campaigns[selectedIndex]);
  const previous = resultsByKey(campaigns[selectedIndex - 1]);
  const changed = new Set<string>();
  for (const [key, result] of latest) {
    if (previous.get(key)?.status !== result.status) changed.add(result.case_id);
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
): { requirements: Requirement[]; cases: CaseDefinition[] } {
  const changed = changedCaseKeys(dataset, campaign);
  const disagreement = disagreementCaseKeys(campaign);
  const resultMap = resultsByKey(campaign);
  const requirementMap = new Map(
    dataset.requirements.map((requirement) => [requirement.id, requirement]),
  );
  const allCasesByRequirement = new Map<string, CaseDefinition[]>();
  for (const testCase of dataset.cases) {
    const linked = allCasesByRequirement.get(testCase.primary_requirement) ?? [];
    linked.push(testCase);
    allCasesByRequirement.set(testCase.primary_requirement, linked);
  }
  const needle = filters.search.toLocaleLowerCase();
  const cases = dataset.cases.filter((testCase) => {
    const requirement = requirementMap.get(testCase.primary_requirement);
    const candidateResults = [...resultMap.values()].filter(
      (result) =>
        result.case_id === testCase.id &&
        (!filters.tool || `${result.tool_id}/${result.profile_id}` === filters.tool),
    );
    const searchable = [
      testCase.id,
      testCase.title,
      testCase.description,
      testCase.primary_requirement,
      requirement?.summary ?? "",
      requirement?.id ?? "",
      requirement?.clause ?? "",
      requirement?.paragraph_anchor ?? "",
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
      (!needle || searchable.includes(needle)) &&
      (!filters.revision ||
        testCase.revision_applicability[filters.revision] === "applicable" ||
        testCase.revision_applicability[filters.revision] ===
          "same-rule-different-clause") &&
      (!filters.chapter || String(requirement?.chapter) === filters.chapter) &&
      (!filters.clause || requirement?.clause.startsWith(filters.clause)) &&
      (!filters.phase || testCase.target_phase === filters.phase) &&
      (!filters.expectation || testCase.expectation === filters.expectation) &&
      (!filters.tag ||
        testCase.tags.includes(filters.tag) ||
        requirement?.tags.includes(filters.tag)) &&
      (!filters.status ||
        candidateResults.some((result) => result.status === filters.status)) &&
      (!filters.reason ||
        candidateResults.some((result) => result.reason === filters.reason)) &&
      (!filters.changed || changed.has(testCase.id)) &&
      (!filters.disagreement || disagreement.has(testCase.id))
    );
  });
  const matchedCaseIds = new Set(cases.map((testCase) => testCase.id));
  const caseSpecificFilter = Boolean(
    filters.phase ||
      filters.expectation ||
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
      requirement.paragraph_anchor,
      ...requirement.tags,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!needle || searchable.includes(needle) || matchingCases.length > 0) &&
      (!filters.revision ||
        rule?.status === "applicable" ||
        rule?.status === "same-rule-different-clause") &&
      (!filters.chapter || String(requirement.chapter) === filters.chapter) &&
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
    cases: cases.filter((testCase) => requirementIds.has(testCase.primary_requirement)),
  };
}
