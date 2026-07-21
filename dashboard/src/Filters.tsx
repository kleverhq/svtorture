import type { Dispatch, SetStateAction } from "react";

import {
  STATUS_GROUP_LABELS,
  STATUS_GROUP_ORDER,
  statusGroup,
} from "./model";
import type { Filters as FilterValues, StatusGroup } from "./model";
import type { Campaign, Dataset } from "./types";

interface FilterProps {
  dataset: Dataset;
  campaign?: Campaign | undefined;
  filters: FilterValues;
  setFilters: Dispatch<SetStateAction<FilterValues>>;
  onReset: () => void;
}

function choices(values: Array<string | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort();
}

export function Filters({
  dataset,
  campaign,
  filters,
  setFilters,
  onReset,
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
  const profiles = choices(
    dataset.campaigns.flatMap((item) =>
      item.tools.flatMap((tool) =>
        tool.profile_ids.map((profile) => `${tool.definition.id}/${profile}`),
      ),
    ),
  );
  const statuses = choices(
    dataset.campaigns.flatMap((item) =>
      item.results.map((result) => result.status),
    ),
  );
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
        !filters.tool || `${result.tool_id}/${result.profile_id}` === filters.tool,
    ) ?? [];
  const groupCounts = Object.fromEntries(
    STATUS_GROUP_ORDER.map((group) => [
      group,
      scopedResults.filter((result) => statusGroup(result.status) === group).length,
    ]),
  ) as Record<StatusGroup, number>;

  return (
    <div className="filters">
      <div className="filters__quick" aria-label="Result groups">
        <span className="filters__quick-label">Show</span>
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
        <button
          type="button"
          className="filter-chip"
          aria-pressed={filters.changed}
          onClick={() => update("changed", !filters.changed)}
        >
          Changed
        </button>
        <button
          type="button"
          className="filter-chip"
          aria-pressed={filters.disagreement}
          onClick={() => update("disagreement", !filters.disagreement)}
        >
          Disagreement
        </button>
      </div>

      <div className="filters__primary">
        <label className="search">
          <span>Search</span>
          <input
            type="search"
            value={filters.search}
            placeholder="Requirement, case, clause, diagnostic…"
            onChange={(event) => update("search", event.target.value)}
          />
        </label>
        <label>
          <span>Campaign</span>
          <select
            value={filters.campaign}
            onChange={(event) => update("campaign", event.target.value)}
          >
            <option value="">Latest campaign</option>
            {[...dataset.campaigns]
              .sort((left, right) => right.finished_at.localeCompare(left.finished_at))
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.finished_at.slice(0, 10)} · {item.id}
                </option>
              ))}
          </select>
        </label>
        <label>
          <span>Tool / profile</span>
          <select
            value={filters.tool}
            onChange={(event) => update("tool", event.target.value)}
          >
            <option value="">All profiles</option>
            {profiles.map((profile) => (
              <option key={profile}>{profile}</option>
            ))}
          </select>
        </label>
        <button type="button" className="button button--quiet" onClick={onReset}>
          Clear
        </button>
      </div>

      <details className="filters__advanced">
        <summary>Advanced filters</summary>
        <div className="filters__grid">
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
                <option key={status}>{status}</option>
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
          <label>
            <span>Date</span>
            <input
              type="date"
              value={filters.date}
              onChange={(event) => update("date", event.target.value)}
            />
          </label>
        </div>
      </details>
    </div>
  );
}
