import { useEffect, useMemo, useRef, useState } from "react";

import {
  corpusTrendPointKey,
  toolTrendPointKey,
  trendRangeBounds,
  type TrendKind,
  type TrendRange,
} from "./model";
import type {
  Campaign,
  CorpusMetricSummary,
  CorpusRatio,
  Dataset,
  MetricPoint,
} from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;
const RANGE_OPTIONS: Array<{ value: TrendRange; label: string }> = [
  { value: "all", label: "All time" },
  { value: "year", label: "Last year" },
  { value: "six-months", label: "Last 6 months" },
  { value: "three-months", label: "Last 3 months" },
  { value: "month", label: "Last month" },
  { value: "week", label: "Last week" },
];

interface TrendDefinition {
  kind: TrendKind;
  label: string;
  unit: "percent" | "density";
  description: string;
  referenceDescription: string;
}

export const TREND_OPTIONS: TrendDefinition[] = [
  {
    kind: "pass-rate",
    label: "Pass rate",
    unit: "percent",
    description:
      "Applicable requirements passed by each selected tool and profile, including Unclear in the denominator.",
    referenceDescription: "The horizontal reference marks 100%.",
  },
  {
    kind: "coverage",
    label: "Coverage",
    unit: "percent",
    description:
      "Requirements shows referenced anchors; Cases shows requirements linked from cases. Both are divided by the selected corpus total.",
    referenceDescription: "The horizontal reference marks 100%.",
  },
  {
    kind: "density",
    label: "Density",
    unit: "density",
    description:
      "Requirements shows links per covered anchor; Cases shows case links per covered requirement for the selected parts.",
    referenceDescription: "Horizontal references mark 1× and 2× density.",
  },
];

export interface TrendPoint {
  pointKey: string;
  campaignId: string;
  timestamp: string;
  seriesName: string;
  numerator: number;
  denominator: number;
  value: number | null;
  boundaryKey: string;
  campaign?: Campaign;
  metric?: MetricPoint;
}

interface ChartDatum {
  value: [number, number | null];
  point: TrendPoint;
  pointKey: string;
  unavailable?: boolean;
  boundary?: boolean;
}

function definitionFor(kind: TrendKind): TrendDefinition {
  const definition = TREND_OPTIONS.find((item) => item.kind === kind);
  if (!definition) throw new Error(`unknown trend ${kind}`);
  return definition;
}

function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function ratioValue(
  ratio: CorpusRatio,
  unit: TrendDefinition["unit"],
): number | null {
  if (!ratio.denominator) return null;
  const value = ratio.numerator / ratio.denominator;
  return unit === "percent" ? value * 100 : value;
}

export function toolPassRate(point: MetricPoint): number | null {
  if (!point.valid || !point.denominator) return null;
  return (100 * point.numerator) / point.denominator;
}

function corpusRatio(
  summary: CorpusMetricSummary,
  kind: "coverage" | "density",
  selectedParts: string[],
): CorpusRatio {
  if (!selectedParts.length) return summary[kind];
  const selected = new Set(selectedParts);
  return summary.breakdown
    .filter((part) => selected.has(`${part.kind}:${part.id}`))
    .reduce(
      (ratio, part) => ({
        numerator: ratio.numerator + part[kind].numerator,
        denominator: ratio.denominator + part[kind].denominator,
      }),
      { numerator: 0, denominator: 0 },
    );
}

export function trendPoints(
  dataset: Dataset,
  kind: TrendKind,
  toolFilter: string,
  profileFilter: string,
  selectedParts: string[] = [],
): TrendPoint[] {
  if (kind === "pass-rate") {
    const campaigns = new Map(dataset.campaigns.map((campaign) => [campaign.id, campaign]));
    return dataset.metrics
      .filter(
        (point) =>
          (!toolFilter || point.tool_id === toolFilter) &&
          (!profileFilter || point.profile_id === profileFilter),
      )
      .map((point) => {
        const campaign = campaigns.get(point.campaign_id);
        return {
          pointKey: toolTrendPointKey(point),
          campaignId: point.campaign_id,
          timestamp: point.timestamp,
          seriesName: `${point.tool_id}/${point.profile_id}`,
          numerator: point.numerator,
          denominator: point.denominator,
          value: toolPassRate(point),
          boundaryKey: `${point.corpus_sha}:${point.denominator}`,
          ...(campaign ? { campaign } : {}),
          metric: point,
        };
      });
  }

  const definition = definitionFor(kind);
  return dataset.campaigns.flatMap((campaign) =>
    (["requirements", "cases"] as const).map((scope) => {
      const ratio = corpusRatio(
        campaign.corpus_metrics[scope],
        kind,
        selectedParts,
      );
      return {
        pointKey: corpusTrendPointKey(campaign, scope),
        campaignId: campaign.id,
        timestamp: campaign.finished_at,
        seriesName: scope === "requirements" ? "Requirements" : "Cases",
        numerator: ratio.numerator,
        denominator: ratio.denominator,
        value: ratioValue(ratio, definition.unit),
        boundaryKey: `${ratio.numerator}:${ratio.denominator}`,
        campaign,
      };
    }),
  );
}

function isMeasurementBoundary(
  previous: TrendPoint | undefined,
  point: TrendPoint,
): boolean {
  return Boolean(previous && previous.boundaryKey !== point.boundaryKey);
}

function hasMeasurementBoundary(points: TrendPoint[]): boolean {
  const groups = new Map<string, TrendPoint[]>();
  for (const point of points) {
    groups.set(point.seriesName, [...(groups.get(point.seriesName) ?? []), point]);
  }
  return [...groups.values()].some((values) =>
    [...values]
      .sort((left, right) => left.timestamp.localeCompare(right.timestamp))
      .some((point, index, sorted) =>
        isMeasurementBoundary(sorted[index - 1], point),
      ),
  );
}

export function formatUtcMinute(timestamp: string | number): string {
  return new Date(timestamp).toISOString().slice(0, 16).replace("T", " ");
}

function formatTrendValue(value: number | null, unit: TrendDefinition["unit"]): string {
  if (value === null) return "Unavailable";
  const formatted = value.toFixed(unit === "percent" ? 1 : 2).replace(/\.0+$/, "");
  return unit === "percent" ? `${formatted}%` : `${formatted}×`;
}

function formatOptional(value: string | null | undefined): string {
  return value || "Not recorded";
}

function densityMaximum(points: TrendPoint[]): number {
  const observed = points.reduce(
    (maximum, point) => Math.max(maximum, point.value ?? 0),
    2,
  );
  return Math.max(2.25, Math.ceil(observed * 1.1 * 4) / 4);
}

function TrendsChart({
  points,
  definition,
  domainStart,
  domainEnd,
  rangeStart,
  rangeEnd,
  selectedPointKey,
  resetKey,
  onSelectPoint,
}: {
  points: TrendPoint[];
  definition: TrendDefinition;
  domainStart: number;
  domainEnd: number;
  rangeStart: number;
  rangeEnd: number;
  selectedPointKey: string;
  resetKey: number;
  onSelectPoint: (point: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const onSelectRef = useRef(onSelectPoint);
  onSelectRef.current = onSelectPoint;
  const orderedPoints = [...points].sort(
    (left, right) =>
      left.timestamp.localeCompare(right.timestamp) ||
      left.pointKey.localeCompare(right.pointKey),
  );
  const moveSelection = (direction: -1 | 1) => {
    if (!orderedPoints.length) return;
    const current = orderedPoints.findIndex(
      (point) => point.pointKey === selectedPointKey,
    );
    const next =
      current < 0
        ? direction > 0
          ? 0
          : orderedPoints.length - 1
        : Math.min(Math.max(current + direction, 0), orderedPoints.length - 1);
    const point = orderedPoints[next];
    if (point) onSelectPoint(point.pointKey);
  };
  useEffect(() => {
    let active = true;
    let chart: import("echarts/core").ECharts | undefined;
    let observer: ResizeObserver | undefined;
    const resize = () => chart?.resize();
    const render = async () => {
      const [
        echarts,
        { LineChart, ScatterChart },
        {
          DataZoomComponent,
          GridComponent,
          LegendComponent,
          MarkLineComponent,
          TooltipComponent,
        },
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
        ScatterChart,
        DataZoomComponent,
        GridComponent,
        LegendComponent,
        MarkLineComponent,
        TooltipComponent,
        SVGRenderer,
      ]);
      chart = echarts.init(ref.current, undefined, { renderer: "svg" });
      const groups = new Map<string, TrendPoint[]>();
      for (const point of points) {
        const values = groups.get(point.seriesName) ?? [];
        values.push(point);
        groups.set(point.seriesName, values);
      }
      const yAxisMaximum =
        definition.unit === "percent" ? 110 : densityMaximum(points);
      const references =
        definition.unit === "percent"
          ? [{ yAxis: 100, label: { formatter: "100%" } }]
          : [
              { yAxis: 1, label: { formatter: "1×" } },
              { yAxis: 2, label: { formatter: "2×" } },
            ];
      const dataSeries = [...groups.entries()].flatMap(([name, values]) => {
        const sorted = [...values].sort((left, right) =>
          left.timestamp.localeCompare(right.timestamp),
        );
        const annotated = sorted.map((point, index) => ({
          point,
          boundary: isMeasurementBoundary(sorted[index - 1], point),
        }));
        const line = {
          name,
          type: "line",
          symbol: "circle",
          symbolSize: 9,
          connectNulls: false,
          lineStyle: { width: 3 },
          emphasis: { focus: "series" },
          data: annotated.flatMap(({ point, boundary }) => {
            const datum: ChartDatum & Record<string, unknown> = {
              value: [Date.parse(point.timestamp), point.value],
              point,
              pointKey: point.pointKey,
              boundary,
              symbol: boundary ? "diamond" : "circle",
              symbolSize: boundary ? 13 : 9,
            };
            return boundary
              ? [
                  {
                    value: [Date.parse(point.timestamp) - 1, null],
                    symbol: "none",
                    tooltip: { show: false },
                  },
                  datum,
                ]
              : [datum];
          }),
        };
        const unavailable = annotated
          .filter(({ point }) => point.value === null)
          .map(
            ({ point, boundary }): ChartDatum & Record<string, unknown> => ({
              value: [Date.parse(point.timestamp), 0],
              point,
              pointKey: point.pointKey,
              unavailable: true,
              boundary,
              symbol: boundary ? "emptyDiamond" : "emptyCircle",
              symbolSize: boundary ? 14 : 11,
              itemStyle: {
                borderWidth: 2,
                borderColor: "var(--issue)",
                color: "var(--surface)",
              },
            }),
          );
        return unavailable.length
          ? [
              line,
              {
                name,
                type: "scatter",
                data: unavailable,
                emphasis: { focus: "series" },
              },
            ]
          : [line];
      });
      chart.setOption({
        animation: false,
        useUTC: true,
        backgroundColor: "transparent",
        grid: { left: 58, right: 34, top: 44, bottom: 62 },
        legend: {
          top: 4,
          type: "scroll",
          data: [...groups.keys()],
          textStyle: { color: "var(--text-secondary)" },
        },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: (parameter: unknown) => {
            const datum = (parameter as { data?: ChartDatum }).data;
            if (!datum?.point) return "";
            return [
              `<strong>${escapeHtml(
                formatTrendValue(datum.unavailable ? null : datum.point.value, definition.unit),
              )}</strong>`,
              escapeHtml(datum.point.seriesName),
              escapeHtml(`${datum.point.numerator}/${datum.point.denominator}`),
              escapeHtml(`${formatUtcMinute(datum.point.timestamp)} UTC`),
            ].join("<br/>");
          },
        },
        xAxis: {
          type: "time",
          min: domainStart,
          max: domainEnd,
          minInterval: DAY_MS,
          axisLabel: {
            color: "var(--text-muted)",
            hideOverlap: true,
            formatter: (value: number) => new Date(value).toISOString().slice(0, 10),
          },
          axisLine: { lineStyle: { color: "var(--line-strong)" } },
          splitLine: { show: true, lineStyle: { color: "var(--line)" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: yAxisMaximum,
          interval: definition.unit === "percent" ? 20 : 0.5,
          name: definition.unit === "percent" ? "percent" : "density",
          nameTextStyle: { color: "var(--text-muted)" },
          axisLabel: {
            color: "var(--text-muted)",
            formatter:
              definition.unit === "percent"
                ? (value: number) => (value > 100 ? "" : `${value}%`)
                : (value: number) =>
                    value >= yAxisMaximum ? "" : `${value}×`,
          },
          splitLine: { lineStyle: { color: "var(--line)" } },
        },
        dataZoom: [
          {
            type: "inside",
            xAxisIndex: 0,
            startValue: rangeStart,
            endValue: rangeEnd,
            filterMode: "none",
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
            moveOnMouseWheel: false,
            preventDefaultMouseMove: true,
          },
          {
            type: "slider",
            xAxisIndex: 0,
            startValue: rangeStart,
            endValue: rangeEnd,
            filterMode: "none",
            height: 18,
            bottom: 8,
            showDetail: false,
            showDataShadow: false,
            brushSelect: false,
            borderColor: "var(--line)",
            fillerColor: "var(--accent-soft)",
            handleStyle: { color: "var(--accent)" },
          },
        ],
        series: [
          ...dataSeries,
          {
            name: "Reference",
            type: "line",
            silent: true,
            symbol: "none",
            data: [],
            tooltip: { show: false },
            markLine: {
              silent: true,
              symbol: ["none", "none"],
              lineStyle: {
                color: "var(--accent)",
                type: "dashed",
                width: 2,
              },
              label: {
                position: "insideEndTop",
                color: "var(--accent-strong)",
                backgroundColor: "var(--surface)",
                padding: [2, 5],
              },
              data: references,
            },
          },
        ],
      });
      chart.on("click", (event) => {
        const datum = event.data as ChartDatum | undefined;
        if (event.componentType === "series" && datum?.pointKey) {
          onSelectRef.current(datum.pointKey);
        }
      });
      chart.getZr().on("click", (event) => {
        if (!event.target) onSelectRef.current("");
      });
      if (typeof ResizeObserver === "undefined") {
        window.addEventListener("resize", resize);
      } else {
        observer = new ResizeObserver(resize);
        observer.observe(ref.current);
      }
    };
    void render();
    return () => {
      active = false;
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      chart?.dispose();
    };
  }, [definition, domainEnd, domainStart, points, rangeEnd, rangeStart, resetKey]);
  return (
    <div
      className="trends-chart-shell"
      role="group"
      tabIndex={0}
      aria-label={`${definition.label} over time. ${definition.referenceDescription} Use Left and Right arrows to inspect metric points; Escape closes details.`}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          event.preventDefault();
          moveSelection(-1);
        } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          event.preventDefault();
          moveSelection(1);
        } else if (event.key === "Home" && orderedPoints[0]) {
          event.preventDefault();
          onSelectPoint(orderedPoints[0].pointKey);
        } else if (event.key === "End" && orderedPoints.at(-1)) {
          event.preventDefault();
          onSelectPoint(orderedPoints.at(-1)!.pointKey);
        } else if (event.key === "Escape") {
          onSelectPoint("");
        }
      }}
    >
      <div className="trends-chart" ref={ref} aria-hidden="true" />
    </div>
  );
}

function TrendsInspector({
  point,
  definition,
  onClose,
}: {
  point: TrendPoint;
  definition: TrendDefinition;
  onClose: () => void;
}) {
  const metric = point.metric;
  const campaign = point.campaign;
  const tag = metric?.exact_tags.length
    ? metric.exact_tags.join(", ")
    : metric?.nearest_tag
      ? `${metric.nearest_tag} (nearest)`
      : "Not recorded";
  return (
    <aside
      className="trends-inspector"
      aria-label="Trend point details"
      aria-live="polite"
    >
      <header>
        <div>
          <span>Trend point</span>
          <h2>{point.seriesName}</h2>
          <code>{formatUtcMinute(point.timestamp)} UTC</code>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label="Close trend details"
          onClick={onClose}
        >
          ×
        </button>
      </header>

      <section>
        <h3>Measurement</h3>
        <dl className="trends-inspector__facts">
          <div>
            <dt>Trend</dt>
            <dd>{definition.label}</dd>
          </div>
          <div>
            <dt>Value</dt>
            <dd>{formatTrendValue(point.value, definition.unit)}</dd>
          </div>
          <div>
            <dt>Operands</dt>
            <dd>{point.numerator}/{point.denominator}</dd>
          </div>
          {metric && (
            <>
              <div>
                <dt>Standard</dt>
                <dd>IEEE {metric.revision}</dd>
              </div>
              <div>
                <dt>Pass</dt>
                <dd>{metric.conforming}</dd>
              </div>
              <div>
                <dt>Fail</dt>
                <dd>{metric.nonconforming}</dd>
              </div>
              <div>
                <dt>Unclear</dt>
                <dd>{metric.inconclusive}</dd>
              </div>
              <div>
                <dt>Validity</dt>
                <dd>{metric.valid ? "Valid" : "Invalid"}</dd>
              </div>
              <div>
                <dt>Completeness</dt>
                <dd>{metric.complete ? "Complete" : "Incomplete"}</dd>
              </div>
            </>
          )}
        </dl>
      </section>

      <section>
        <h3>Campaign</h3>
        <dl className="trends-inspector__facts trends-inspector__facts--stacked">
          <div>
            <dt>Timestamp</dt>
            <dd>{formatUtcMinute(point.timestamp)} UTC</dd>
          </div>
          <div>
            <dt>Campaign ID</dt>
            <dd><code>{point.campaignId}</code></dd>
          </div>
          <div>
            <dt>Campaign source</dt>
            <dd>{formatOptional(campaign?.trust.source)}</dd>
          </div>
          <div>
            <dt>Trusted repository</dt>
            <dd>{formatOptional(campaign?.trust.repository)}</dd>
          </div>
        </dl>
      </section>

      {metric && (
        <section>
          <h3>Tool provenance</h3>
          <dl className="trends-inspector__facts trends-inspector__facts--stacked">
            <div>
              <dt>Version</dt>
              <dd>{formatOptional(metric.reported_version)}</dd>
            </div>
            <div>
              <dt>Source SHA</dt>
              <dd><code>{formatOptional(metric.tool_sha)}</code></dd>
            </div>
            <div>
              <dt>Tag</dt>
              <dd>{tag}</dd>
            </div>
            <div>
              <dt>Image digest</dt>
              <dd><code>{formatOptional(metric.image_digest)}</code></dd>
            </div>
          </dl>
        </section>
      )}

      <section>
        <h3>Corpus provenance</h3>
        <dl className="trends-inspector__facts trends-inspector__facts--stacked">
          <div>
            <dt>Repository commit</dt>
            <dd><code>{formatOptional(metric?.repository_commit ?? campaign?.repository.commit)}</code></dd>
          </div>
          <div>
            <dt>Requirements manifest</dt>
            <dd><code>{formatOptional(campaign?.hashes.requirements)}</code></dd>
          </div>
          <div>
            <dt>Cases manifest</dt>
            <dd><code>{formatOptional(campaign?.hashes.cases ?? metric?.corpus_sha)}</code></dd>
          </div>
          <div>
            <dt>Selection manifest</dt>
            <dd><code>{formatOptional(campaign?.hashes.selection)}</code></dd>
          </div>
        </dl>
      </section>
    </aside>
  );
}

export function TrendsView({
  dataset,
  toolFilter,
  profileFilter,
  trend,
  range,
  selectedPointKey,
  selectedParts,
  onTrendChange,
  onRangeChange,
  onSelectPoint,
}: {
  dataset: Dataset;
  toolFilter: string;
  profileFilter: string;
  trend: TrendKind;
  range: TrendRange;
  selectedPointKey: string;
  selectedParts: string[];
  onTrendChange: (trend: TrendKind) => void;
  onRangeChange: (range: TrendRange) => void;
  onSelectPoint: (point: string) => void;
}) {
  const now = useRef(new Date()).current;
  const [resetKey, setResetKey] = useState(0);
  const definition = definitionFor(trend);
  const visible = useMemo(
    () => trendPoints(dataset, trend, toolFilter, profileFilter, selectedParts),
    [dataset, profileFilter, selectedParts, toolFilter, trend],
  );
  const timeline = useMemo(
    () =>
      trend === "pass-rate"
        ? dataset.metrics.map((point) => ({ timestamp: point.timestamp }))
        : dataset.campaigns.map((campaign) => ({ timestamp: campaign.finished_at })),
    [dataset.campaigns, dataset.metrics, trend],
  );
  const bounds = useMemo(
    () => trendRangeBounds(timeline, range, now),
    [now, range, timeline],
  );
  const hasBoundary = useMemo(() => hasMeasurementBoundary(visible), [visible]);
  const selectedPoint = visible.find((point) => point.pointKey === selectedPointKey);

  useEffect(() => {
    if (selectedPointKey && !selectedPoint) onSelectPoint("");
  }, [onSelectPoint, selectedPoint, selectedPointKey]);

  const chooseRange = (value: TrendRange) => {
    onRangeChange(value);
    setResetKey((current) => current + 1);
  };

  return (
    <section className="panel trends" aria-label="Trends">
      <div className="trends__controls">
        <div className="trends__ranges" role="group" aria-label="Trend range">
          {RANGE_OPTIONS.map((option) => (
            <button
              type="button"
              className="filter-chip"
              aria-pressed={range === option.value}
              key={option.value}
              onClick={() => chooseRange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="trends__zoom-controls">
          {hasBoundary && (
            <span className="trends__boundary-key">
              <strong aria-hidden="true">◆</strong> corpus/denominator boundary
            </span>
          )}
          <span className="trends__zoom-hint">Wheel/pinch to zoom · drag to pan</span>
          <button
            type="button"
            className="button button--quiet"
            onClick={() => setResetKey((current) => current + 1)}
          >
            Reset zoom
          </button>
        </div>
      </div>
      <div className={`trends__workspace${selectedPoint ? " has-inspector" : ""}`}>
        <div
          className="trends__selector"
          role="radiogroup"
          aria-labelledby="trend-selector-label"
        >
          <span id="trend-selector-label" className="trends__selector-title">
            Trend
          </span>
          <div className="trends__options">
            {TREND_OPTIONS.map((option) => {
              const descriptionId = `trend-description-${option.kind}`;
              return (
                <label key={option.kind} title={option.description}>
                  <input
                    type="radio"
                    name="trend"
                    value={option.kind}
                    checked={trend === option.kind}
                    aria-label={option.label}
                    aria-describedby={descriptionId}
                    onChange={() => onTrendChange(option.kind)}
                  />
                  <span>{option.label}</span>
                  <span id={descriptionId} className="visually-hidden">
                    {option.description}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
        <div className="trends__main">
          <TrendsChart
            points={visible}
            definition={definition}
            {...bounds}
            selectedPointKey={selectedPointKey}
            resetKey={resetKey}
            onSelectPoint={onSelectPoint}
          />
        </div>
        {selectedPoint && (
          <TrendsInspector
            point={selectedPoint}
            definition={definition}
            onClose={() => onSelectPoint("")}
          />
        )}
      </div>
    </section>
  );
}
