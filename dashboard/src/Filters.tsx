import { useEffect, useRef, type Dispatch, type SetStateAction } from "react";

import {
  STATUS_GROUP_LABELS,
  STATUS_GROUP_ORDER,
  STATUS_LABELS,
  statusGroup,
} from "./model";
import type {
  Filters as FilterValues,
  StatusGroup,
  TrendKind,
} from "./model";
import type { Campaign, CorpusPartMetric, Dataset, Status } from "./types";

export type FilterMode = "overview" | "corpus" | "trends" | "campaigns";

interface FilterProps {
  dataset: Dataset;
  campaign?: Campaign | undefined;
  filters: FilterValues;
  setFilters: Dispatch<SetStateAction<FilterValues>>;
  onReset: () => void;
  mode: FilterMode;
  trendKind?: TrendKind | undefined;
  standardParts?: CorpusPartMetric[] | undefined;
  selectedParts?: string[] | undefined;
  onSelectedPartsChange?: ((parts: string[]) => void) | undefined;
}

function choices(values: Array<string | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort();
}

const PROFILE_ORDER = ["preprocessor", "parser", "elaborator", "simulator"];

function displayFilterValue(value: string): string {
  return value
    .replaceAll(/[-_]+/g, " ")
    .replaceAll(/\b\w/g, (character) => character.toUpperCase());
}

export function Filters({
  dataset,
  campaign,
  filters,
  setFilters,
  onReset,
  mode,
  trendKind,
  standardParts = [],
  selectedParts = [],
  onSelectedPartsChange,
}: FilterProps) {
  const update = (name: keyof FilterValues, value: string | boolean) => {
    setFilters((current) => {
      if (name === "statusGroup") {
        return { ...current, status: "", statusGroup: String(value) };
      }
      if (name === "status") {
        return { ...current, status: String(value), statusGroup: "" };
      }
      return { ...current, [name]: value };
    });
  };
  const statuses = choices(
    dataset.campaigns.flatMap((item) =>
      item.results.map((result) => result.status),
    ),
  ) as Status[];
  const reasons = choices(
    dataset.campaigns.flatMap((item) =>
      item.results.map((result) => result.reason),
    ),
  );
  const tags = choices([
    ...dataset.requirements.flatMap((requirement) => requirement.tags),
    ...dataset.cases.flatMap((testCase) => testCase.tags),
  ]);
  const scopedResults =
    campaign?.results.filter(
      (result) =>
        (!filters.tool || result.tool_id === filters.tool) &&
        (!filters.profile || result.profile_id === filters.profile),
    ) ?? [];
  const groupCounts = Object.fromEntries(
    STATUS_GROUP_ORDER.map((group) => [
      group,
      scopedResults.filter((result) => statusGroup(result.status) === group).length,
    ]),
  ) as Record<StatusGroup, number>;
  const trendPairs = [
    ...new Map(
      dataset.metrics.map((point) => [
        `${point.tool_id}\u0000${point.profile_id}`,
        { toolId: point.tool_id, profileId: point.profile_id },
      ]),
    ).values(),
  ];
  const campaignPairs = [
    ...new Map(
      dataset.campaigns.flatMap((item) =>
        item.tools.flatMap((tool) =>
          tool.profile_ids.map((profileId) => [
            `${tool.definition.id}\u0000${profileId}`,
            { toolId: tool.definition.id, profileId },
          ]),
        ),
      ),
    ).values(),
  ];
  const profilePairs =
    mode === "trends"
      ? trendPairs
      : mode === "campaigns"
        ? campaignPairs
        : (campaign?.tools.flatMap((tool) =>
          tool.profile_ids.flatMap((profileId) => {
            const profile = tool.definition.profiles.find(
              (item) => item.id === profileId,
            );
            return profile && (mode !== "overview" || profile.headline)
              ? [{ toolId: tool.definition.id, profileId }]
              : [];
          }),
        ) ?? []);
  const tools = [...new Set(profilePairs.map((pair) => pair.toolId))];
  const profiles = [...new Set(profilePairs.map((pair) => pair.profileId))].sort(
    (left, right) => {
      const leftOrder = PROFILE_ORDER.indexOf(left);
      const rightOrder = PROFILE_ORDER.indexOf(right);
      if (leftOrder === -1 && rightOrder === -1) return left.localeCompare(right);
      if (leftOrder === -1) return 1;
      if (rightOrder === -1) return -1;
      return leftOrder - rightOrder;
    },
  );
  const profileCount = (toolId: string, profileId: string) =>
    profilePairs.filter(
      (pair) =>
        (!toolId || pair.toolId === toolId) &&
        (!profileId || pair.profileId === profileId),
    ).length;
  const showFacets =
    mode === "overview" ||
    mode === "corpus" ||
    mode === "trends" ||
    mode === "campaigns";
  const showToolFacets =
    showFacets && (mode !== "trends" || trendKind === "pass-rate");
  const showPartFacet =
    mode === "trends" && trendKind !== undefined && trendKind !== "pass-rate";
  const partMultiselectRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const closeOnOutsidePointer = (event: PointerEvent) => {
      const multiselect = partMultiselectRef.current;
      if (
        multiselect?.open &&
        event.target instanceof Node &&
        !multiselect.contains(event.target)
      ) {
        multiselect.open = false;
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      const multiselect = partMultiselectRef.current;
      if (event.key === "Escape" && multiselect?.open) {
        multiselect.open = false;
        multiselect.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const partSelectionLabel = selectedParts.length
    ? `${selectedParts.length} selected`
    : `All ${standardParts.length}`;
  const partKey = (part: CorpusPartMetric) => `${part.kind}:${part.id}`;
  const togglePart = (key: string) => {
    if (!onSelectedPartsChange) return;
    if (selectedParts.includes(key)) {
      onSelectedPartsChange(selectedParts.filter((part) => part !== key));
    } else {
      onSelectedPartsChange([...selectedParts, key]);
    }
  };

  return (
    <div className="filters">
      {showToolFacets && (
        <div className="filters__pair-grid">
          <div className="filters__quick" role="group" aria-label="Tools">
            <span className="filters__quick-label">Tools</span>
            <button
              type="button"
              className="filter-chip"
              aria-pressed={!filters.tool}
              onClick={() => update("tool", "")}
            >
              All <b>{profileCount("", filters.profile)}</b>
            </button>
            {tools.map((toolId) => (
              <button
                type="button"
                className="filter-chip"
                aria-pressed={filters.tool === toolId}
                key={toolId}
                onClick={() => update("tool", toolId)}
              >
                {displayFilterValue(toolId)}{" "}
                <b>{profileCount(toolId, filters.profile)}</b>
              </button>
            ))}
          </div>
          <div className="filters__quick" role="group" aria-label="Profiles">
            <span className="filters__quick-label">Profile</span>
            <button
              type="button"
              className="filter-chip"
              aria-pressed={!filters.profile}
              onClick={() => update("profile", "")}
            >
              All <b>{profileCount(filters.tool, "")}</b>
            </button>
            {profiles.map((profileId) => (
              <button
                type="button"
                className="filter-chip"
                aria-pressed={filters.profile === profileId}
                key={profileId}
                onClick={() => update("profile", profileId)}
              >
                {displayFilterValue(profileId)}{" "}
                <b>{profileCount(filters.tool, profileId)}</b>
              </button>
            ))}
          </div>
        </div>
      )}

      {showPartFacet && (
        <div className="filters__part-row">
          <span className="filters__quick-label">Chapter</span>
          <details className="part-multiselect" ref={partMultiselectRef}>
            <summary
              className="filter-chip"
              aria-label={`Chapter and annex filter: ${partSelectionLabel}`}
            >
              {partSelectionLabel}
            </summary>
            <div className="part-multiselect__menu" role="group" aria-label="Chapters">
              <label>
                <input
                  type="checkbox"
                  checked={selectedParts.length === 0}
                  onChange={() => onSelectedPartsChange?.([])}
                />
                <span>All</span>
              </label>
              {standardParts.map((part) => {
                const key = partKey(part);
                return (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={selectedParts.includes(key)}
                      onChange={() => togglePart(key)}
                    />
                    <span>
                      {part.kind === "chapter" ? "Chapter" : "Annex"} {part.id}
                      <small>{part.title}</small>
                    </span>
                  </label>
                );
              })}
            </div>
          </details>
        </div>
      )}

      {mode === "corpus" && (
        <div className="filters__pair-grid">
          <div className="filters__quick" role="group" aria-label="Results">
            <span className="filters__quick-label">Result</span>
            <button
              type="button"
              className="filter-chip"
              aria-pressed={!filters.statusGroup}
              onClick={() => update("statusGroup", "")}
            >
              All <b>{scopedResults.length}</b>
            </button>
            {STATUS_GROUP_ORDER.map((group) => (
              <button
                type="button"
                className={`filter-chip filter-chip--${group}`}
                aria-pressed={filters.statusGroup === group}
                key={group}
                onClick={() => update("statusGroup", group)}
              >
                {STATUS_GROUP_LABELS[group]} <b>{groupCounts[group]}</b>
              </button>
            ))}
          </div>
          <div className="filters__quick" role="group" aria-label="Comparison">
            <span className="filters__quick-label">Compare</span>
            <button
              type="button"
              className="filter-chip"
              aria-pressed={filters.changed}
              onClick={() => update("changed", !filters.changed)}
            >
              Changed since previous
            </button>
            <button
              type="button"
              className="filter-chip"
              aria-pressed={filters.disagreement}
              onClick={() => update("disagreement", !filters.disagreement)}
            >
              Cross-tool disagreement
            </button>
          </div>
        </div>
      )}

      {mode === "corpus" && (
        <details className="filters__advanced">
          <summary>Advanced filters</summary>
        <div className="filters__grid">
          <label className="search">
            <span>Search</span>
            <input
              type="search"
              value={filters.search}
              placeholder="Requirement, case, clause, diagnostic…"
              onChange={(event) => update("search", event.target.value)}
            />
          </label>
          {mode === "corpus" && (
            <>
              <label>
                <span>Revision</span>
                <select
                  value={filters.revision}
                  onChange={(event) => update("revision", event.target.value)}
                >
                  <option value="">Any</option>
                  <option>1800-2012</option>
                  <option>1800-2017</option>
                  <option>1800-2023</option>
                </select>
              </label>
              <label>
                <span>Chapter</span>
                <select
                  value={filters.chapter}
                  onChange={(event) => update("chapter", event.target.value)}
                >
                  <option value="">Any</option>
                  {choices(dataset.requirements.map((item) => String(item.chapter))).map(
                    (chapter) => (
                      <option key={chapter}>{chapter}</option>
                    ),
                  )}
                </select>
              </label>
              <label>
                <span>Clause prefix</span>
                <input
                  value={filters.clause}
                  placeholder="12.4"
                  onChange={(event) => update("clause", event.target.value)}
                />
              </label>
              <label>
                <span>Phase</span>
                <select
                  value={filters.phase}
                  onChange={(event) => update("phase", event.target.value)}
                >
                  <option value="">Any</option>
                  {choices(dataset.cases.map((item) => item.target_phase)).map((phase) => (
                    <option key={phase}>{phase}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Expectation</span>
                <select
                  value={filters.expectation}
                  onChange={(event) => update("expectation", event.target.value)}
                >
                  <option value="">Any</option>
                  {choices(dataset.cases.map((item) => item.expectation)).map(
                    (expectation) => (
                      <option key={expectation}>{expectation}</option>
                    ),
                  )}
                </select>
              </label>
              <label>
                <span>Case presence</span>
                <select
                  value={filters.casePresence}
                  onChange={(event) => update("casePresence", event.target.value)}
                >
                  <option value="">Any</option>
                  <option value="with-cases">With cases</option>
                  <option value="without-cases">Without cases</option>
                </select>
              </label>
              <label>
                <span>Tag</span>
                <select
                  value={filters.tag}
                  onChange={(event) => update("tag", event.target.value)}
                >
                  <option value="">Any</option>
                  {tags.map((tag) => (
                    <option key={tag}>{tag}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Exact result</span>
                <select
                  value={filters.status}
                  onChange={(event) => update("status", event.target.value)}
                >
                  <option value="">Any</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_LABELS[status]}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Reason</span>
                <select
                  value={filters.reason}
                  onChange={(event) => update("reason", event.target.value)}
                >
                  <option value="">Any</option>
                  {reasons.map((reason) => (
                    <option key={reason}>{reason}</option>
                  ))}
                </select>
              </label>
            </>
          )}
          <button type="button" className="button button--quiet" onClick={onReset}>
            Clear local filters
          </button>
          </div>
        </details>
      )}
    </div>
  );
}
