import { useEffect, useMemo, useRef } from "react";

import type { MetricPoint } from "./types";

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
          textStyle: { color: "#c8d5d1" },
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
          axisLabel: { color: "#91a49f" },
          axisLine: { lineStyle: { color: "#3d514d" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          name: "verified %",
          nameTextStyle: { color: "#91a49f" },
          axisLabel: { color: "#91a49f", formatter: "{value}%" },
          splitLine: { lineStyle: { color: "#263a36" } },
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
                  ? { borderWidth: 3, borderColor: "#ffd166" }
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
  points,
  toolFilter,
  dateFilter,
}: {
  points: MetricPoint[];
  toolFilter: string;
  dateFilter: string;
}) {
  const visible = useMemo(
    () =>
      points
        .filter(
          (point) =>
            (!toolFilter || `${point.tool_id}/${point.profile_id}` === toolFilter) &&
            (!dateFilter || point.timestamp.startsWith(dateFilter)),
        )
        .sort((left, right) => right.timestamp.localeCompare(left.timestamp)),
    [dateFilter, points, toolFilter],
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
      <div className="panel__heading">
        <div>
          <span className="eyebrow">History and comparison</span>
          <h2 id="history-title">Verified support over time</h2>
        </div>
        <p>
          Diamond points mark corpus/denominator boundaries. {corpusChanges} visible
          corpus changes.
        </p>
      </div>
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
