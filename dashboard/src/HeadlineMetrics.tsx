import type { Campaign, Dataset } from "./types";

export function HeadlineMetrics({
  dataset,
  campaign,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
}) {
  const headlineProfiles = new Set(
    campaign?.tools.flatMap((tool) =>
      tool.definition.profiles
        .filter((profile) => profile.headline)
        .map((profile) => `${tool.definition.id}/${profile.id}`),
    ) ?? [],
  );
  const metrics = dataset.metrics.filter(
    (metric) =>
      (!campaign || metric.campaign_id === campaign.id) &&
      (!campaign || headlineProfiles.has(`${metric.tool_id}/${metric.profile_id}`)),
  );
  const latestTimestamp = [...metrics]
    .map((metric) => metric.timestamp)
    .sort()
    .at(-1);
  const points = metrics.filter((metric) => metric.timestamp === latestTimestamp);
  return (
    <section className="metric-strip" aria-label="Headline metrics">
      {points.map((metric) => (
        <article className="metric-card" key={`${metric.tool_id}/${metric.profile_id}`}>
          <div className="metric-card__topline">
            <strong>{metric.tool_id}</strong>
            <span>{metric.profile_id}</span>
          </div>
          <div className="metric-card__score">
            {metric.valid ? `${metric.numerator}/${metric.denominator}` : "Invalid"}
          </div>
          <p>{metric.label}</p>
          <span className="metric-card__scope">
            {metric.profile_id === "simulator"
              ? "Scope includes simulation"
              : metric.profile_id === "elaborator"
                ? "Scope ends at elaboration"
                : "Scope ends at parsing"}
          </span>
          <div className="meter" aria-hidden="true">
            <span
              style={{
                width: `${
                  metric.denominator ? (100 * metric.numerator) / metric.denominator : 0
                }%`,
              }}
            />
          </div>
          <details>
            <summary>
              {metric.revision} · {metric.complete ? "complete" : "incomplete"}
            </summary>
            <dl className="compact-dl">
              <div>
                <dt>Corpus scope</dt>
                <dd>{metric.corpus_coverage}</dd>
              </div>
              <div>
                <dt>Executed</dt>
                <dd>{metric.execution_coverage}</dd>
              </div>
              <div>
                <dt>Conforming</dt>
                <dd>{metric.conforming}</dd>
              </div>
              <div>
                <dt>Nonconforming</dt>
                <dd>{metric.nonconforming}</dd>
              </div>
              <div>
                <dt>Inconclusive</dt>
                <dd>{metric.inconclusive}</dd>
              </div>
              <div>
                <dt>Unsupported</dt>
                <dd>{metric.unsupported}</dd>
              </div>
              <div>
                <dt>Infrastructure</dt>
                <dd>{metric.infrastructure_state}</dd>
              </div>
              <div>
                <dt>Corpus SHA</dt>
                <dd>
                  <code title={metric.corpus_sha}>{metric.corpus_sha.slice(0, 12)}</code>
                </dd>
              </div>
              <div>
                <dt>Campaign</dt>
                <dd>
                  <code>{metric.campaign_id}</code>
                </dd>
              </div>
            </dl>
          </details>
        </article>
      ))}
    </section>
  );
}
