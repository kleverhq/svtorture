import type { Campaign, Dataset } from "./types";

export function HeadlineMetrics({
  dataset,
  campaign,
  onSelectTool,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
  onSelectTool: (tool: string) => void;
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
          headlineProfiles.has(`${metric.tool_id}/${metric.profile_id}`),
      )
    : [];

  return (
    <section
      className="overview-metrics tool-coverage"
      aria-labelledby="tool-coverage-title"
    >
      <header>
        <h2 id="tool-coverage-title">Verified requirement coverage by tool</h2>
        <p>
          A requirement is verified only when every selected mandatory case for that tool
          profile passes.
        </p>
      </header>
      {!campaign ? (
        <p className="empty-state">
          No campaign matches the current campaign and date selection.
        </p>
      ) : points.length ? (
        <div className="tool-metrics">
          {points.map((metric) => {
            const percentage =
              metric.valid && metric.denominator
                ? (100 * metric.numerator) / metric.denominator
                : 0;
            const profileKey = `${metric.tool_id}/${metric.profile_id}`;
            return (
              <button
                type="button"
                className={`tool-metric ${
                  metric.valid ? "" : "tool-metric--unavailable"
                }`}
                key={profileKey}
                aria-label={`View requirements for ${metric.tool_id}/${metric.profile_id}`}
                onClick={() => onSelectTool(profileKey)}
              >
                <span className="tool-metric__identity">
                  <strong>{metric.tool_id}</strong>
                  <span>{metric.profile_id}</span>
                </span>
                {metric.valid ? (
                  <span
                    className="tool-metric__outcomes"
                    aria-label={`${metric.tool_id} requirement outcomes`}
                  >
                    <span className="tool-outcome tool-outcome--pass">
                      <strong>{metric.conforming}</strong>
                      <span>PASS</span>
                    </span>
                    <span className="tool-outcome tool-outcome--fail">
                      <strong>{metric.nonconforming}</strong>
                      <span>FAIL</span>
                    </span>
                    <span className="tool-outcome tool-outcome--unclear">
                      <strong>{metric.inconclusive}</strong>
                      <span>UNCLEAR</span>
                    </span>
                  </span>
                ) : (
                  <strong className="tool-metric__unavailable">Unavailable</strong>
                )}
                <span className="tool-metric__coverage">
                  {metric.valid
                    ? `${percentage.toFixed(0)}% of IEEE ${metric.revision} applicable requirements`
                    : `Unavailable · ${metric.infrastructure_state || metric.label}`}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="empty-state">No headline metrics were recorded.</p>
      )}
    </section>
  );
}
