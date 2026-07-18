import type { Dispatch, SetStateAction } from "react";

import type { Filters as FilterValues } from "./model";
import type { Dataset } from "./types";

interface FilterProps {
  dataset: Dataset;
  filters: FilterValues;
  setFilters: Dispatch<SetStateAction<FilterValues>>;
  onReset: () => void;
}

function choices(values: Array<string | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort();
}

export function Filters({ dataset, filters, setFilters, onReset }: FilterProps) {
  const update = (name: keyof FilterValues, value: string | boolean) => {
    setFilters((current) => ({ ...current, [name]: value }));
  };
  const profiles = choices(
    dataset.campaigns.flatMap((campaign) =>
      campaign.tools.flatMap((tool) =>
        tool.profile_ids.map((profile) => `${tool.definition.id}/${profile}`),
      ),
    ),
  );
  const statuses = choices(
    dataset.campaigns.flatMap((campaign) =>
      campaign.results.map((result) => result.status),
    ),
  );
  const reasons = choices(
    dataset.campaigns.flatMap((campaign) =>
      campaign.results.map((result) => result.reason),
    ),
  );
  const tags = choices([
    ...dataset.requirements.flatMap((requirement) => requirement.tags),
    ...dataset.cases.flatMap((testCase) => testCase.tags),
  ]);

  return (
    <section className="filters" aria-label="Evidence filters">
      <div className="filters__primary">
        <label className="search">
          <span>Search evidence</span>
          <input
            type="search"
            value={filters.search}
            placeholder="requirement, case, clause, semantic…"
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
              .map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.finished_at.slice(0, 10)} · {campaign.id}
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
          Clear filters
        </button>
      </div>
      <details>
        <summary>Precise filters</summary>
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
            <span>Requirement state</span>
            <select
              value={filters.state}
              onChange={(event) => update("state", event.target.value)}
            >
              <option value="">Any</option>
              {choices(dataset.requirements.map((item) => item.coverage_state)).map(
                (state) => (
                  <option key={state}>{state}</option>
                ),
              )}
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
            <span>Result</span>
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
          <label className="check">
            <input
              type="checkbox"
              checked={filters.changed}
              onChange={(event) => update("changed", event.target.checked)}
            />
            <span>Changed from previous campaign</span>
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={filters.disagreement}
              onChange={(event) => update("disagreement", event.target.checked)}
            />
            <span>Tool disagreement</span>
          </label>
        </div>
      </details>
    </section>
  );
}
