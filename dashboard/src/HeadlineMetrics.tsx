import { compareCampaigns, statusGroup } from "./model";
import type { Campaign, Dataset } from "./types";

export function HeadlineMetrics({
  dataset,
  campaign,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
}) {
  const comparison = compareCampaigns(dataset, campaign);
  const selectedCaseIds = new Set(campaign?.case_ids ?? []);
  const coveredRequirements = new Set(
    dataset.cases
      .filter((testCase) => selectedCaseIds.has(testCase.id))
      .map((testCase) => testCase.primary_requirement),
  ).size;
  const results = campaign?.results ?? [];
  const counts = {
    pass: results.filter((result) => statusGroup(result.status) === "pass").length,
    fail: results.filter((result) => statusGroup(result.status) === "fail").length,
    unsupported: results.filter(
      (result) => statusGroup(result.status) === "unsupported",
    ).length,
    issue: results.filter((result) => statusGroup(result.status) === "issue").length,
  };
  const knownFailures = results.filter((result) => result.known_issue).length;
  const headlineProfiles = new Set(
    campaign?.tools.flatMap((tool) =>
      tool.definition.profiles
        .filter((profile) => profile.headline)
        .map((profile) => `${tool.definition.id}/${profile.id}`),
    ) ?? [],
  );
  const points = dataset.metrics.filter(
    (metric) =>
      metric.campaign_id === campaign?.id &&
      headlineProfiles.has(`${metric.tool_id}/${metric.profile_id}`),
  );

  const summary = [
    {
      label: "Requirements",
      value: coveredRequirements,
      note: `${campaign?.case_ids.length ?? 0} selected cases`,
    },
    {
      label: "Tools",
      value: campaign?.tools.length ?? 0,
      note: campaign?.missing_tool_ids.length
        ? `${campaign.missing_tool_ids.length} missing`
        : "all expected present",
    },
    { label: "Passing results", value: counts.pass, note: `${results.length} total` },
    {
      label: "Failing results",
      value: counts.fail,
      note: knownFailures ? `${knownFailures} known` : "none marked known",
    },
    {
      label: "Unsupported",
      value: counts.unsupported,
      note: "capability or revision",
    },
    { label: "Infra / unclear", value: counts.issue, note: "requires inspection" },
    {
      label: "Regressions",
      value: comparison.previousCampaignId ? comparison.regressions.length : "—",
      note: comparison.previousCampaignId ? "from comparable prior" : "no comparable prior",
    },
  ];

  return (
    <section className="overview-metrics" aria-label="Campaign summary">
      <div className="summary-strip">
        {summary.map((item) => (
          <div className="summary-stat" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </div>
        ))}
      </div>
      <div className="tool-metrics" aria-label="Verified support by tool">
        {points.map((metric) => {
          const percentage = metric.denominator
            ? (100 * metric.numerator) / metric.denominator
            : 0;
          return (
            <article key={`${metric.tool_id}/${metric.profile_id}`}>
              <div className="tool-metric__identity">
                <strong>{metric.tool_id}</strong>
                <span>{metric.profile_id}</span>
              </div>
              <div className="tool-metric__score">
                <strong>
                  {metric.valid ? `${metric.numerator}/${metric.denominator}` : "Invalid"}
                </strong>
                <span>{metric.valid ? `${percentage.toFixed(0)}% verified` : metric.label}</span>
              </div>
              <div className="meter" aria-label={`${percentage.toFixed(0)} percent verified`}>
                <span style={{ width: `${percentage}%` }} />
              </div>
              <span className="tool-metric__state">
                {metric.revision} · {metric.complete ? "complete" : "incomplete"}
              </span>
            </article>
          );
        })}
      </div>
    </section>
  );
}
