import { useState } from "react";

import type { Campaign, Dataset, MetricPoint } from "./types";

type SortKey = "tool" | "pass" | "fail" | "unclear" | "coverage";
type SortDirection = "ascending" | "descending";

function sortValue(metric: MetricPoint, key: SortKey): number | string | null {
  if (key === "tool") return `${metric.tool_id}/${metric.profile_id}`;
  if (!metric.valid) return null;
  if (key === "pass") return metric.conforming;
  if (key === "fail") return metric.nonconforming;
  if (key === "unclear") return metric.inconclusive;
  return metric.denominator ? metric.numerator / metric.denominator : 0;
}

export function HeadlineMetrics({
  dataset,
  campaign,
  toolFilter,
  profileFilter,
  onSelectTool,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
  toolFilter: string;
  profileFilter: string;
  onSelectTool: (tool: string, profile: string) => void;
}) {
  const [sort, setSort] = useState<{
    key: SortKey;
    direction: SortDirection;
  } | null>(null);
  const headlineProfiles = new Set(
    campaign?.tools.flatMap((tool) =>
      tool.definition.profiles
        .filter((profile) => profile.headline)
        .map((profile) => `${tool.definition.id}/${profile.id}`),
    ) ?? [],
  );
  const points = campaign
    ? dataset.metrics.filter(
        (metric) =>
          metric.campaign_id === campaign.id &&
          headlineProfiles.has(`${metric.tool_id}/${metric.profile_id}`) &&
          (!toolFilter || metric.tool_id === toolFilter) &&
          (!profileFilter || metric.profile_id === profileFilter),
      )
    : [];
  const sortedPoints = sort
    ? [...points].sort((left, right) => {
        const leftValue = sortValue(left, sort.key);
        const rightValue = sortValue(right, sort.key);
        let comparison: number;
        if (leftValue === null && rightValue === null) comparison = 0;
        else if (leftValue === null) comparison = 1;
        else if (rightValue === null) comparison = -1;
        else {
          comparison =
            typeof leftValue === "string" && typeof rightValue === "string"
              ? leftValue.localeCompare(rightValue, undefined, {
                  numeric: true,
                  sensitivity: "base",
                })
              : Number(leftValue) - Number(rightValue);
        }
        return sort.direction === "ascending" ? comparison : -comparison;
      })
    : points;
  const toggleSort = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction:
        current?.key === key && current.direction === "ascending"
          ? "descending"
          : "ascending",
    }));
  };
  const sortableHeader = (key: SortKey, label: string) => (
    <th
      className="overview-table__sortable"
      aria-sort={sort?.key === key ? sort.direction : "none"}
    >
      <button
        type="button"
        className="overview-table__sort"
        title={`Sort by ${label}`}
        onClick={() => toggleSort(key)}
      >
        <span>{label}</span>
        <span aria-hidden="true">
          {sort?.key === key
            ? sort.direction === "ascending"
              ? "▲"
              : "▼"
            : "↕"}
        </span>
      </button>
    </th>
  );

  return (
    <section className="overview-metrics" aria-label="Verified requirement coverage">
      <div className="overview-table-wrap">
        <table className="overview-table">
          <thead>
            <tr>
              {sortableHeader("tool", "Tool")}
              {sortableHeader("pass", "Pass")}
              {sortableHeader("fail", "Fail")}
              {sortableHeader("unclear", "Unclear")}
              {sortableHeader("coverage", "Coverage")}
              <th>Standard</th>
              <th>Version</th>
            </tr>
          </thead>
          <tbody>
            {!campaign ? (
              <tr>
                <td className="empty-state" colSpan={7}>
                  No campaign matches the current campaign and date selection.
                </td>
              </tr>
            ) : sortedPoints.length ? (
              sortedPoints.map((metric) => {
                const percentage =
                  metric.valid && metric.denominator
                    ? (100 * metric.numerator) / metric.denominator
                    : 0;
                return (
                  <tr
                    className={metric.valid ? "" : "is-unavailable"}
                    key={`${metric.tool_id}/${metric.profile_id}`}
                    onClick={() => onSelectTool(metric.tool_id, metric.profile_id)}
                  >
                    <td>
                      <button
                        type="button"
                        className="overview-table__tool"
                        aria-label={`View requirements for ${metric.tool_id}/${metric.profile_id}`}
                      >
                        <strong>{metric.tool_id}</strong>
                        <span>{metric.profile_id}</span>
                      </button>
                    </td>
                    <td className="overview-table__outcome overview-table__outcome--pass">
                      {metric.valid ? metric.conforming : "—"}
                    </td>
                    <td className="overview-table__outcome overview-table__outcome--fail">
                      {metric.valid ? metric.nonconforming : "—"}
                    </td>
                    <td className="overview-table__outcome overview-table__outcome--unclear">
                      {metric.valid ? metric.inconclusive : "—"}
                    </td>
                    <td>
                      {metric.valid
                        ? `${percentage.toFixed(0)}%`
                        : `Unavailable · ${metric.infrastructure_state || metric.label}`}
                    </td>
                    <td>IEEE {metric.revision}</td>
                    <td>{metric.reported_version ?? "Unavailable"}</td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td className="empty-state" colSpan={7}>
                  {toolFilter || profileFilter
                    ? "No tool profiles match the current Overview filters."
                    : "No headline metrics were recorded."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
