import { compareCampaigns, statusGroup } from "./model";
import type { Campaign, Dataset } from "./types";

function countLabel(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function HeadlineMetrics({
  dataset,
  campaign,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
}) {
  if (!campaign) {
    return (
      <section className="overview-metrics" aria-labelledby="campaign-summary-title">
        <header className="overview-metrics__heading">
          <h2 id="campaign-summary-title">Selected campaign summary</h2>
          <p>No campaign matches the current campaign and date selection.</p>
        </header>
      </section>
    );
  }

  const comparison = compareCampaigns(dataset, campaign);
  const selectedCaseIds = new Set(campaign.case_ids);
  const coveredRequirements = new Set(
    dataset.cases
      .filter((testCase) => selectedCaseIds.has(testCase.id))
      .map((testCase) => testCase.primary_requirement),
  ).size;
  const results = campaign.results;
  const counts = {
    pass: results.filter((result) => statusGroup(result.status) === "pass").length,
    fail: results.filter((result) => statusGroup(result.status) === "fail").length,
    unsupported: results.filter(
      (result) => statusGroup(result.status) === "unsupported",
    ).length,
    issue: results.filter((result) => statusGroup(result.status) === "issue").length,
    unscored: results.filter((result) => statusGroup(result.status) === "unscored").length,
  };
  const knownFailures = results.filter(
    (result) => statusGroup(result.status) === "fail" && result.known_issue,
  ).length;
  const campaignCaseCount = campaign.case_ids.length;
  const expectedTools = campaign.expected_tool_ids.length;
  const missingTools = campaign.missing_tool_ids.length;
  const headlineProfiles = new Set(
    campaign.tools.flatMap((tool) =>
      tool.definition.profiles
        .filter((profile) => profile.headline)
        .map((profile) => `${tool.definition.id}/${profile.id}`),
    ),
  );
  const points = dataset.metrics.filter(
    (metric) =>
      metric.campaign_id === campaign.id &&
      headlineProfiles.has(`${metric.tool_id}/${metric.profile_id}`),
  );
  const recordedEvaluations = countLabel(results.length, "recorded evaluation");

  const summary = [
    {
      label: "Covered requirements",
      value: coveredRequirements,
      note: `${countLabel(campaignCaseCount, "campaign case")} ${campaignCaseCount === 1 ? "maps" : "map"} to these requirements.`,
    },
    {
      label: "Included tools",
      value: campaign.tools.length,
      note: missingTools
        ? `Expected tools missing: ${missingTools} of ${expectedTools}.`
        : expectedTools
          ? `Expected tools present: ${expectedTools} of ${expectedTools}.`
          : "No expected tool list was recorded.",
    },
    {
      label: "Passed evaluations",
      value: counts.pass,
      note: `${recordedEvaluations}.`,
    },
    {
      label: "Failed evaluations",
      value: counts.fail,
      note: `${recordedEvaluations}; ${countLabel(knownFailures, "failure")} linked to a known issue.`,
    },
    {
      label: "Unsupported evaluations",
      value: counts.unsupported,
      note: "The tool capability or selected standard revision is unavailable.",
    },
    {
      label: "Needs inspection",
      value: counts.issue,
      note: "Inconclusive observations or harness errors.",
    },
    {
      label: "Unscored evaluations",
      value: counts.unscored,
      note: "Cases that were not run or do not apply to the selected tool profile.",
    },
    {
      label: "Regressions",
      value: comparison.previousCampaignId ? comparison.regressions.length : "—",
      note: comparison.previousCampaignId
        ? "Previously passing evaluations that are now non-passing, versus the prior campaign with the same tool profiles."
        : "No earlier campaign has the same tool profiles.",
    },
  ];

  return (
    <section className="overview-metrics" aria-labelledby="campaign-summary-title">
      <header className="overview-metrics__heading">
        <h2 id="campaign-summary-title">Selected campaign summary</h2>
        <p>
          Each evaluation is one tool/profile running one case. Counts describe the
          selected campaign and do not hide unsupported or incomplete evidence.
        </p>
      </header>
      <dl className="summary-strip">
        {summary.map((item) => (
          <div className="summary-stat" key={item.label}>
            <dt>{item.label}</dt>
            <dd>
              <strong>{item.value}</strong>
              <span>{item.note}</span>
            </dd>
          </div>
        ))}
      </dl>
      <section className="tool-coverage" aria-labelledby="tool-coverage-title">
        <header>
          <h3 id="tool-coverage-title">Verified requirement coverage by tool</h3>
          <p>
            A requirement is verified only when every selected mandatory case for that
            tool profile passes.
          </p>
        </header>
        {points.length ? (
          <div className="tool-metrics">
            {points.map((metric) => {
              const percentage =
                metric.valid && metric.denominator
                  ? (100 * metric.numerator) / metric.denominator
                  : 0;
              return (
                <article key={`${metric.tool_id}/${metric.profile_id}`}>
                  <div className="tool-metric__identity">
                    <strong>{metric.tool_id}</strong>
                    <span>{metric.profile_id}</span>
                  </div>
                  <div
                    className={`tool-metric__score${metric.valid ? "" : " tool-metric__score--unavailable"}`}
                  >
                    <strong>
                      {metric.valid
                        ? `${metric.numerator} / ${metric.denominator}`
                        : "Unavailable"}
                    </strong>
                    <span>
                      {metric.valid
                        ? `${percentage.toFixed(0)}% of IEEE ${metric.revision}`
                        : `Not scored · ${metric.infrastructure_state || metric.label}`}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <p className="empty-state">No headline metrics were recorded.</p>
        )}
      </section>
    </section>
  );
}
