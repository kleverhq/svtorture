import type { Campaign, Dataset } from "./types";

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

  return (
    <section className="overview-metrics" aria-label="Verified requirement coverage">
      <div className="overview-table-wrap">
        <table className="overview-table">
          <thead>
            <tr>
              <th>Tool</th>
              <th>Pass</th>
              <th>Fail</th>
              <th>Unclear</th>
              <th>Coverage</th>
              <th>Version</th>
            </tr>
          </thead>
          <tbody>
            {!campaign ? (
              <tr>
                <td className="empty-state" colSpan={6}>
                  No campaign matches the current campaign and date selection.
                </td>
              </tr>
            ) : points.length ? (
              points.map((metric) => {
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
                        ? `${percentage.toFixed(0)}% · IEEE ${metric.revision}`
                        : `Unavailable · ${metric.infrastructure_state || metric.label}`}
                    </td>
                    <td>{metric.reported_version ?? "Unavailable"}</td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td className="empty-state" colSpan={6}>
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
