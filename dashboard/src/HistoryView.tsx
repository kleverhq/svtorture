import { useEffect, useMemo, useRef } from "react";

import { compareCampaigns } from "./model";
import type { Campaign, Dataset, MetricPoint } from "./types";

function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function HistoryChart({ points }: { points: MetricPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let active = true;
    let chart: import("echarts/core").ECharts | undefined;
    const resize = () => chart?.resize();
    const render = async () => {
      const [
        echarts,
        { LineChart },
        { GridComponent, LegendComponent, TooltipComponent },
        { SVGRenderer },
      ] = await Promise.all([
        import("echarts/core"),
        import("echarts/charts"),
        import("echarts/components"),
        import("echarts/renderers"),
      ]);
      if (!active || !ref.current) return;
      echarts.use([
        LineChart,
        GridComponent,
        LegendComponent,
        TooltipComponent,
        SVGRenderer,
      ]);
      chart = echarts.init(ref.current, undefined, { renderer: "svg" });
      const groups = new Map<string, MetricPoint[]>();
      for (const point of points) {
        const key = `${point.tool_id}/${point.profile_id}`;
        const values = groups.get(key) ?? [];
        values.push(point);
        groups.set(key, values);
      }
      chart.setOption({
        animation: false,
        backgroundColor: "transparent",
        grid: { left: 50, right: 24, top: 46, bottom: 60 },
        legend: {
          top: 4,
          textStyle: { color: "var(--text-secondary)" },
        },
        tooltip: {
          trigger: "axis",
          formatter: (parameters: unknown) => {
            if (!Array.isArray(parameters)) return "";
            return parameters
              .map(
                (parameter: {
                  seriesName?: string;
                  data?: { point?: MetricPoint };
                }) => {
                  const point = parameter.data?.point;
                  const score =
                    point?.valid && point.denominator
                      ? `${((100 * point.numerator) / point.denominator).toFixed(1)}%`
                      : "invalid";
                  return point
                    ? `${escapeHtml(parameter.seriesName ?? "")}<br/>${escapeHtml(
                        point.timestamp,
                      )}<br/>${escapeHtml(score)} · ${point.numerator}/${
                        point.denominator
                      }` +
                        `<br/>campaign ${escapeHtml(point.campaign_id)}` +
                        `<br/>tool ${escapeHtml(point.tool_sha ?? "no source SHA")}` +
                        `<br/>corpus ${escapeHtml(point.corpus_sha)}`
                    : "";
                },
              )
              .join("<br/>");
          },
        },
        xAxis: {
          type: "time",
          axisLabel: { color: "var(--text-muted)" },
          axisLine: { lineStyle: { color: "var(--line-strong)" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          name: "verified %",
          nameTextStyle: { color: "var(--text-muted)" },
          axisLabel: { color: "var(--text-muted)", formatter: "{value}%" },
          splitLine: { lineStyle: { color: "var(--line)" } },
        },
        series: [...groups.entries()].map(([name, values]) => {
          const sorted = [...values].sort((left, right) =>
            left.timestamp.localeCompare(right.timestamp),
          );
          return {
            name,
            type: "line",
            connectNulls: false,
            symbol: "circle",
            symbolSize: 9,
            lineStyle: { width: 3 },
            data: sorted.map((point, index) => {
              const prior = sorted[index - 1];
              const corpusChanged =
                prior &&
                (prior.corpus_sha !== point.corpus_sha ||
                  prior.denominator !== point.denominator);
              return {
                value: [
                  point.timestamp,
                  point.valid && point.denominator
                    ? (100 * point.numerator) / point.denominator
                    : Number.NaN,
                ],
                point,
                symbol: corpusChanged ? "diamond" : "circle",
                symbolSize: corpusChanged ? 15 : 9,
                itemStyle: corpusChanged
                  ? { borderWidth: 3, borderColor: "var(--issue)" }
                  : {},
              };
            }),
          };
        }),
      });
      window.addEventListener("resize", resize);
    };
    void render();
    return () => {
      active = false;
      window.removeEventListener("resize", resize);
      chart?.dispose();
    };
  }, [points]);
  return <div className="history-chart" ref={ref} role="img" aria-label="Metric history chart" />;
}

export function HistoryView({
  dataset,
  campaign,
  toolFilter,
  dateFilter,
}: {
  dataset: Dataset;
  campaign?: Campaign | undefined;
  toolFilter: string;
  dateFilter: string;
}) {
  const comparison = compareCampaigns(dataset, campaign);
  const visible = useMemo(
    () =>
      dataset.metrics
        .filter(
          (point) =>
            (!toolFilter || `${point.tool_id}/${point.profile_id}` === toolFilter) &&
            (!dateFilter || point.timestamp.startsWith(dateFilter)),
        )
        .sort((left, right) => right.timestamp.localeCompare(left.timestamp)),
    [dataset.metrics, dateFilter, toolFilter],
  );
  const historyGroups = new Map<string, MetricPoint[]>();
  for (const point of visible) {
    const key = `${point.tool_id}/${point.profile_id}`;
    const values = historyGroups.get(key) ?? [];
    values.push(point);
    historyGroups.set(key, values);
  }
  const corpusChanges = [...historyGroups.values()].reduce((total, values) => {
    const ordered = [...values].sort((left, right) =>
      left.timestamp.localeCompare(right.timestamp),
    );
    return (
      total +
      ordered.filter((point, index) => {
        const previous = ordered[index - 1];
        return (
          previous !== undefined &&
          (previous.corpus_sha !== point.corpus_sha ||
            previous.denominator !== point.denominator)
        );
      }).length
    );
  }, 0);
  return (
    <section className="panel history" aria-labelledby="history-title">
      <div className="panel__heading panel__heading--compact">
        <div>
          <h2 id="history-title">History and changes</h2>
          <span>{visible.length} metric points · {corpusChanges} corpus boundaries</span>
        </div>
      </div>
      {comparison.previousCampaignId ? (
        <section className="change-summary" aria-label="Changes from previous campaign">
          <div>
            <span>Regressions</span>
            <strong>{comparison.regressions.length}</strong>
          </div>
          <div>
            <span>New passes</span>
            <strong>{comparison.newPasses.length}</strong>
          </div>
          <div>
            <span>Other judgment changes</span>
            <strong>{comparison.otherChanges.length}</strong>
          </div>
          <div>
            <span>Tool revisions changed</span>
            <strong>{comparison.toolRevisionChanges.length}</strong>
          </div>
          <div>
            <span>Measurement boundary</span>
            <strong>
              {comparison.corpusChanged || comparison.denominatorChanged ? "Yes" : "No"}
            </strong>
          </div>
          <p>
            Compared with <code>{comparison.previousCampaignId}</code>
          </p>
        </section>
      ) : (
        <div className="comparison-empty">
          <strong>No comparable previous campaign</strong>
          <span>Change counts become available after another run with the same tool profiles.</span>
        </div>
      )}
      {(comparison.regressions.length > 0 ||
        comparison.newPasses.length > 0 ||
        comparison.otherChanges.length > 0 ||
        comparison.toolRevisionChanges.length > 0 ||
        comparison.corpusChanged ||
        comparison.denominatorChanged) && (
        <div className="change-details">
          {comparison.regressions.map((change) => (
            <span
              className="change change--regression"
              key={`regression:${change.caseId}:${change.toolId}:${change.profileId}`}
            >
              Regression · {change.caseId} · {change.toolId}/{change.profileId} ·{" "}
              {change.previous} → {change.current}
            </span>
          ))}
          {comparison.newPasses.map((change) => (
            <span
              className="change change--pass"
              key={`pass:${change.caseId}:${change.toolId}:${change.profileId}`}
            >
              New pass · {change.caseId} · {change.toolId}/{change.profileId} ·{" "}
              {change.previous} → {change.current}
            </span>
          ))}
          {comparison.otherChanges.map((change) => (
            <span
              className="change change--other"
              key={`other:${change.caseId}:${change.toolId}:${change.profileId}`}
            >
              Judgment · {change.caseId} · {change.toolId}/{change.profileId} ·{" "}
              {change.previous} → {change.current}
            </span>
          ))}
          {comparison.toolRevisionChanges.map((change) => (
            <span
              className="change change--tool"
              key={`tool:${change.toolId}`}
              title={`${change.previous} → ${change.current}`}
            >
              Tool source · {change.toolId} · {change.previous.slice(0, 12)} →{" "}
              {change.current.slice(0, 12)}
            </span>
          ))}
          {comparison.corpusChanged && (
            <span className="change change--boundary">Requirement or case corpus changed</span>
          )}
          {comparison.denominatorChanged && (
            <span className="change change--boundary">Metric denominator changed</span>
          )}
        </div>
      )}
      <HistoryChart points={visible} />
      <div className="history__table-wrap">
        <table className="history__table">
          <thead>
            <tr>
              <th>Timestamp / campaign</th>
              <th>Tool snapshot</th>
              <th>Corpus</th>
              <th>Verified</th>
              <th>Completeness</th>
              <th>Image</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((point) => (
              <tr key={`${point.campaign_id}:${point.tool_id}:${point.profile_id}`}>
                <td>
                  <strong>{new Date(point.timestamp).toLocaleString()}</strong>
                  <code>{point.campaign_id}</code>
                </td>
                <td>
                  <strong>
                    {point.tool_id}/{point.profile_id}
                  </strong>
                  <code title={point.tool_sha ?? undefined}>
                    {point.tool_sha?.slice(0, 12) ?? "no source SHA"}
                  </code>
                  <span>
                    {point.exact_tags.join(", ") || point.nearest_tag || "no nearby tag"}
                  </span>
                  <span>{point.reported_version}</span>
                </td>
                <td>
                  <code title={point.repository_commit}>
                    {point.repository_commit.slice(0, 12)}
                  </code>
                  <code title={point.corpus_sha}>
                    manifest {point.corpus_sha.slice(0, 12)}
                  </code>
                </td>
                <td>
                  <strong>
                    {point.valid
                      ? `${point.numerator}/${point.denominator}`
                      : "invalid"}
                  </strong>
                  <span>{point.revision}</span>
                </td>
                <td>
                  <span>{point.complete ? "Complete" : "Incomplete"}</span>
                  <span>{point.infrastructure_state}</span>
                </td>
                <td>
                  <code title={point.image_digest ?? undefined}>
                    {point.image_digest?.slice(0, 24) ?? "not recorded"}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
