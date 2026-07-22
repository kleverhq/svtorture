import { useEffect, useMemo, useRef, useState } from "react";

import {
  historyRangeBounds,
  metricPointKey,
  type HistoryRange,
} from "./model";
import type { Campaign, Dataset, MetricPoint } from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;
const RANGE_OPTIONS: Array<{ value: HistoryRange; label: string }> = [
  { value: "week", label: "Last week" },
  { value: "month", label: "Last month" },
  { value: "six-months", label: "Last 6 months" },
  { value: "year", label: "Last year" },
  { value: "all", label: "All time" },
];

interface HistoryDatum {
  value: [number, number | null];
  point: MetricPoint;
  pointKey: string;
  unavailable?: boolean;
  boundary?: boolean;
}

function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function metricPercentage(point: MetricPoint): number {
  return point.denominator ? (100 * point.numerator) / point.denominator : 0;
}

function metricIsAvailable(point: MetricPoint): boolean {
  return point.valid && point.denominator > 0;
}

function isMeasurementBoundary(
  previous: MetricPoint | undefined,
  point: MetricPoint,
): boolean {
  return Boolean(
    previous &&
      (previous.corpus_sha !== point.corpus_sha ||
        previous.denominator !== point.denominator),
  );
}

function hasMeasurementBoundary(points: MetricPoint[]): boolean {
  const groups = new Map<string, MetricPoint[]>();
  for (const point of points) {
    const key = `${point.tool_id}/${point.profile_id}`;
    groups.set(key, [...(groups.get(key) ?? []), point]);
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

function formatPercentage(value: number): string {
  return `${value.toFixed(1).replace(/\.0$/, "")}%`;
}

function formatOptional(value: string | null | undefined): string {
  return value || "Not recorded";
}

function HistoryChart({
  points,
  domainStart,
  domainEnd,
  rangeStart,
  rangeEnd,
  selectedPointKey,
  resetKey,
  onSelectPoint,
}: {
  points: MetricPoint[];
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
      metricPointKey(left).localeCompare(metricPointKey(right)),
  );
  const moveSelection = (direction: -1 | 1) => {
    if (!orderedPoints.length) return;
    const current = orderedPoints.findIndex(
      (point) => metricPointKey(point) === selectedPointKey,
    );
    const next =
      current < 0
        ? direction > 0
          ? 0
          : orderedPoints.length - 1
        : Math.min(Math.max(current + direction, 0), orderedPoints.length - 1);
    const point = orderedPoints[next];
    if (point) onSelectPoint(metricPointKey(point));
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
        useUTC: true,
        backgroundColor: "transparent",
        grid: { left: 54, right: 22, top: 44, bottom: 62 },
        legend: {
          top: 4,
          type: "scroll",
          textStyle: { color: "var(--text-secondary)" },
        },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: (parameter: unknown) => {
            const datum = (parameter as { data?: HistoryDatum }).data;
            if (!datum?.point) return "";
            const point = datum.point;
            return [
              `<strong>${escapeHtml(
                datum.unavailable
                  ? "Unavailable"
                  : formatPercentage(metricPercentage(point)),
              )}</strong>`,
              escapeHtml(`${point.tool_id}/${point.profile_id}`),
              escapeHtml(`${formatUtcMinute(point.timestamp)} UTC`),
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
            formatter: (value: number) =>
              new Date(value).toISOString().slice(0, 10),
          },
          axisLine: { lineStyle: { color: "var(--line-strong)" } },
          splitLine: { show: true, lineStyle: { color: "var(--line)" } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          interval: 20,
          name: "verified %",
          nameTextStyle: { color: "var(--text-muted)" },
          axisLabel: { color: "var(--text-muted)", formatter: "{value}%" },
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
        series: [...groups.entries()].flatMap(([name, values]) => {
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
              const datum: HistoryDatum & Record<string, unknown> = {
                value: [
                  Date.parse(point.timestamp),
                  metricIsAvailable(point) ? metricPercentage(point) : null,
                ],
                point,
                pointKey: metricPointKey(point),
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
            .filter(({ point }) => !metricIsAvailable(point))
            .map(
              ({ point, boundary }): HistoryDatum & Record<string, unknown> => ({
                value: [Date.parse(point.timestamp), 0],
                point,
                pointKey: metricPointKey(point),
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
        }),
      });
      chart.on("click", (event) => {
        const datum = event.data as HistoryDatum | undefined;
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
  }, [
    domainEnd,
    domainStart,
    points,
    rangeEnd,
    rangeStart,
    resetKey,
  ]);
  return (
    <div
      className="history-chart-shell"
      role="group"
      tabIndex={0}
      aria-label="Verified requirement coverage over time. Use Left and Right arrows to inspect metric points; Escape closes details."
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          event.preventDefault();
          moveSelection(-1);
        } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          event.preventDefault();
          moveSelection(1);
        } else if (event.key === "Home" && orderedPoints[0]) {
          event.preventDefault();
          onSelectPoint(metricPointKey(orderedPoints[0]));
        } else if (event.key === "End" && orderedPoints.at(-1)) {
          event.preventDefault();
          onSelectPoint(metricPointKey(orderedPoints.at(-1)!));
        } else if (event.key === "Escape") {
          onSelectPoint("");
        }
      }}
    >
      <div className="history-chart" ref={ref} aria-hidden="true" />
    </div>
  );
}

function HistoryInspector({
  point,
  campaign,
  onClose,
}: {
  point: MetricPoint;
  campaign?: Campaign | undefined;
  onClose: () => void;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, [point.campaign_id, point.profile_id, point.tool_id]);
  const percentage = metricIsAvailable(point)
    ? formatPercentage(metricPercentage(point))
    : "Unavailable";
  const tag = point.exact_tags.length
    ? point.exact_tags.join(", ")
    : point.nearest_tag
      ? `${point.nearest_tag} (nearest)`
      : "Not recorded";
  return (
    <aside
      className="history-inspector"
      aria-label="Metric point details"
      aria-live="polite"
      tabIndex={-1}
      ref={ref}
    >
      <header>
        <div>
          <span>Metric point</span>
          <h2>
            {point.tool_id}/{point.profile_id}
          </h2>
          <code>{formatUtcMinute(point.timestamp)} UTC</code>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label="Close metric details"
          onClick={onClose}
        >
          ×
        </button>
      </header>

      <section>
        <h3>Result</h3>
        <dl className="history-inspector__facts">
          <div>
            <dt>Coverage</dt>
            <dd>
              {percentage} · {point.numerator}/{point.denominator}
            </dd>
          </div>
          <div>
            <dt>Standard</dt>
            <dd>IEEE {point.revision}</dd>
          </div>
          <div>
            <dt>Pass</dt>
            <dd>{point.conforming}</dd>
          </div>
          <div>
            <dt>Fail</dt>
            <dd>{point.nonconforming}</dd>
          </div>
          <div>
            <dt>Unclear</dt>
            <dd>{point.inconclusive}</dd>
          </div>
          <div>
            <dt>Validity</dt>
            <dd>{point.valid ? "Valid" : "Invalid"}</dd>
          </div>
          <div>
            <dt>Completeness</dt>
            <dd>{point.complete ? "Complete" : "Incomplete"}</dd>
          </div>
          <div>
            <dt>Infrastructure</dt>
            <dd>{point.infrastructure_state}</dd>
          </div>
        </dl>
      </section>

      <section>
        <h3>Campaign</h3>
        <dl className="history-inspector__facts history-inspector__facts--stacked">
          <div>
            <dt>Timestamp</dt>
            <dd>{formatUtcMinute(point.timestamp)} UTC</dd>
          </div>
          <div>
            <dt>Campaign ID</dt>
            <dd><code>{point.campaign_id}</code></dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{formatOptional(point.reported_version)}</dd>
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

      <section>
        <h3>Tool provenance</h3>
        <dl className="history-inspector__facts history-inspector__facts--stacked">
          <div>
            <dt>Source SHA</dt>
            <dd><code>{formatOptional(point.tool_sha)}</code></dd>
          </div>
          <div>
            <dt>Tag</dt>
            <dd>{tag}</dd>
          </div>
          <div>
            <dt>Image digest</dt>
            <dd><code>{formatOptional(point.image_digest)}</code></dd>
          </div>
        </dl>
      </section>

      <section>
        <h3>Corpus</h3>
        <dl className="history-inspector__facts history-inspector__facts--stacked">
          <div>
            <dt>Repository commit</dt>
            <dd><code>{point.repository_commit}</code></dd>
          </div>
          <div>
            <dt>Manifest SHA</dt>
            <dd><code>{point.corpus_sha}</code></dd>
          </div>
        </dl>
      </section>
    </aside>
  );
}

export function HistoryView({
  dataset,
  toolFilter,
  profileFilter,
  range,
  selectedPointKey,
  onRangeChange,
  onSelectPoint,
}: {
  dataset: Dataset;
  toolFilter: string;
  profileFilter: string;
  range: HistoryRange;
  selectedPointKey: string;
  onRangeChange: (range: HistoryRange) => void;
  onSelectPoint: (point: string) => void;
}) {
  const now = useRef(new Date()).current;
  const [resetKey, setResetKey] = useState(0);
  const visible = useMemo(
    () =>
      dataset.metrics.filter(
        (point) =>
          (!toolFilter || point.tool_id === toolFilter) &&
          (!profileFilter || point.profile_id === profileFilter),
      ),
    [dataset.metrics, profileFilter, toolFilter],
  );
  const bounds = useMemo(
    () => historyRangeBounds(dataset.metrics, range, now),
    [dataset.metrics, now, range],
  );
  const hasBoundary = useMemo(() => hasMeasurementBoundary(visible), [visible]);
  const selectedPoint = dataset.metrics.find(
    (point) => metricPointKey(point) === selectedPointKey,
  );
  const selectedCampaign = selectedPoint
    ? dataset.campaigns.find((campaign) => campaign.id === selectedPoint.campaign_id)
    : undefined;
  const selectedIsVisible =
    selectedPoint &&
    (!toolFilter || selectedPoint.tool_id === toolFilter) &&
    (!profileFilter || selectedPoint.profile_id === profileFilter);

  useEffect(() => {
    if (selectedPointKey && !selectedIsVisible) onSelectPoint("");
  }, [onSelectPoint, selectedIsVisible, selectedPointKey]);

  const chooseRange = (value: HistoryRange) => {
    onRangeChange(value);
    setResetKey((current) => current + 1);
  };

  return (
    <section className="panel history" aria-label="Metric history">
      <div className="history__controls">
        <div className="history__ranges" role="group" aria-label="History range">
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
        <div className="history__zoom-controls">
          {hasBoundary && (
            <span className="history__boundary-key">
              <strong aria-hidden="true">◆</strong> corpus/denominator boundary
            </span>
          )}
          <span className="history__zoom-hint">Wheel/pinch to zoom · drag to pan</span>
          <button
            type="button"
            className="button button--quiet"
            onClick={() => setResetKey((current) => current + 1)}
          >
            Reset zoom
          </button>
        </div>
      </div>
      <div
        className={`history__workspace${selectedPoint ? " has-inspector" : ""}`}
      >
        <div className="history__main">
          <HistoryChart
            points={visible}
            {...bounds}
            selectedPointKey={selectedPointKey}
            resetKey={resetKey}
            onSelectPoint={onSelectPoint}
          />
        </div>
        {selectedPoint && (
          <HistoryInspector
            point={selectedPoint}
            campaign={selectedCampaign}
            onClose={() => onSelectPoint("")}
          />
        )}
      </div>
    </section>
  );
}
