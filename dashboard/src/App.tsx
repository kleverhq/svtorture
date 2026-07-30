import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
} from "react";

import { AboutView } from "./AboutView";
import { CampaignView } from "./CampaignView";
import { CorpusCoverage } from "./CorpusCoverage";
import { EvidenceView } from "./EvidenceView";
import { Filters } from "./Filters";
import { HeadlineMetrics } from "./HeadlineMetrics";
import { TrendsView } from "./TrendsView";
import { RequirementsView } from "./RequirementsView";
import {
  EMPTY_FILTERS,
  campaignsInDateRange,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  corpusTrendPointKey,
  selectedCampaign,
  toolTrendPointKey,
  trendStateFromSearch,
  type TrendKind,
  type TrendRange,
} from "./model";
import { ThemeControl } from "./ThemeControl";
import type { Dataset } from "./types";
import { useDataset } from "./useDataset";

type View = "overview" | "matrix" | "evidence" | "trends" | "campaigns" | "about";

const VIEWS: Array<{ id: View; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "matrix", label: "Requirements" },
  { id: "evidence", label: "Cases" },
  { id: "trends", label: "Trends" },
  { id: "campaigns", label: "Campaigns" },
  { id: "about", label: "About" },
];

function initialView(): View {
  const requested = new URLSearchParams(window.location.search).get("view");
  return VIEWS.some((view) => view.id === requested)
    ? (requested as View)
    : "overview";
}

function SiteHeader({ dataset }: { dataset: Dataset | undefined }) {
  return (
    <header className="site-header">
      <a className="brand" href="?" aria-label="SVTORTURE dashboard home">
        <span className="brand__mark">SV</span>
        <span>
          <strong>SVTORTURE</strong>
          <small>SystemVerilog conformance framework for EDA tools</small>
        </span>
      </a>
      <div className="site-header__meta">
        {dataset && (
          <>
            <span className={`visibility visibility--${dataset.visibility}`}>
              {dataset.visibility}
            </span>
            <span>{dataset.campaigns.length} campaigns</span>
          </>
        )}
        <a
          className="github-link"
          href="https://github.com/kleverhq/svtorture"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
        <ThemeControl />
      </div>
    </header>
  );
}

function CampaignSelection({
  campaigns,
  campaignValue,
  dateFrom,
  dateTo,
  disabled,
  emptyLabel,
  onCampaignChange,
  onDateFromChange,
  onDateToChange,
}: {
  campaigns: Dataset["campaigns"];
  campaignValue: string;
  dateFrom: string;
  dateTo: string;
  disabled: boolean;
  emptyLabel: string;
  onCampaignChange: (value: string) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
}) {
  return (
    <section
      className={`campaign-overview${
        disabled ? " campaign-overview--disabled" : ""
      }`}
      aria-label="Campaign selection"
      aria-disabled={disabled}
    >
      <label className="campaign-overview__campaign">
        <span>Campaign</span>
        <select
          value={campaignValue}
          disabled={disabled}
          onChange={(event) => onCampaignChange(event.target.value)}
        >
          <option value="">
            {campaigns.length ? "Latest campaign" : emptyLabel}
          </option>
          {campaigns.map((item) => (
            <option key={item.id} value={item.id}>
              {item.finished_at.slice(0, 10)} · {item.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>From</span>
        <input
          type="date"
          disabled={disabled}
          max={dateTo || undefined}
          value={dateFrom}
          onChange={(event) => onDateFromChange(event.target.value)}
        />
      </label>
      <label>
        <span>To</span>
        <input
          type="date"
          disabled={disabled}
          min={dateFrom || undefined}
          value={dateTo}
          onChange={(event) => onDateToChange(event.target.value)}
        />
      </label>
    </section>
  );
}

function ViewTabs({
  view,
  onSelect,
}: {
  view: View;
  onSelect: (view: View) => void;
}) {
  const moveFocus = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % VIEWS.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + VIEWS.length) % VIEWS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = VIEWS.length - 1;
    if (nextIndex === undefined) return;
    event.preventDefault();
    event.currentTarget.parentElement
      ?.querySelectorAll<HTMLButtonElement>("[role=tab]")
      [nextIndex]?.focus();
  };

  return (
    <div className="view-tabs" role="tablist" aria-label="Dashboard views">
      {VIEWS.map((item, index) => {
        const selected = view === item.id;
        return (
          <button
            type="button"
            role="tab"
            id={`${item.id}-tab`}
            key={item.id}
            aria-selected={selected}
            aria-controls="dashboard-view-panel"
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(item.id)}
            onKeyDown={(event) => moveFocus(event, index)}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export default function App() {
  const state = useDataset();
  const [view, setView] = useState<View>(initialView);
  const [filters, setFilters] = useState(() => filtersFromSearch(window.location.search));
  const [trend, setTrend] = useState(() =>
    trendStateFromSearch(window.location.search),
  );
  const [workspaceHeight, setWorkspaceHeight] = useState(0);
  const workspaceRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const search = filtersToSearch(
      view === "about" ? EMPTY_FILTERS : filters,
      view,
      trend,
    );
    const hash = view === "about" ? window.location.hash : "";
    window.history.replaceState(null, "", `${search}${hash}`);
  }, [filters, trend, view]);
  useLayoutEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const measure = () => setWorkspaceHeight(workspace.getBoundingClientRect().height);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(workspace);
    return () => observer.disconnect();
  }, [state.dataset, view]);
  useEffect(() => {
    const dataset = state.dataset;
    if (!dataset) return;
    setTrend((current) => {
      const availableParts = new Set(
        dataset.corpus_coverage.requirements.breakdown.map(
          (part) => `${part.kind}:${part.id}`,
        ),
      );
      const parts = current.parts.filter((part) => availableParts.has(part));
      const pointIsValid =
        !current.point ||
        (current.kind === "pass-rate"
          ? dataset.metrics.some(
              (point) => toolTrendPointKey(point) === current.point,
            )
          : dataset.campaigns.some(
              (campaign) =>
                corpusTrendPointKey(campaign, "requirements") === current.point ||
                corpusTrendPointKey(campaign, "cases") === current.point,
            ));
      if (pointIsValid && parts.length === current.parts.length) return current;
      return { ...current, parts, point: pointIsValid ? current.point : "" };
    });
  }, [state.dataset]);
  useEffect(() => {
    const dataset = state.dataset;
    if (!dataset) return;
    setFilters((current) => {
      const ranged = campaignsInDateRange(dataset, current.dateFrom, current.dateTo);
      const campaignIsValid =
        !current.campaign || ranged.some((item) => item.id === current.campaign);
      const campaignId = campaignIsValid ? current.campaign : "";
      let tool = current.tool;
      let profile = current.profile;
      if (view === "overview") {
        const selected = selectedCampaign(
          dataset,
          campaignId,
          current.dateFrom,
          current.dateTo,
        );
        const headlineProfiles =
          selected?.tools.flatMap((item) =>
            item.definition.profiles
              .filter(
                (candidate) =>
                  candidate.headline && item.profile_ids.includes(candidate.id),
              )
              .map((candidate) => ({
                toolId: item.definition.id,
                profileId: candidate.id,
              })),
          ) ?? [];
        if (tool && !headlineProfiles.some((item) => item.toolId === tool)) tool = "";
        if (profile && !headlineProfiles.some((item) => item.profileId === profile)) {
          profile = "";
        }
        if (
          tool &&
          profile &&
          !headlineProfiles.some(
            (item) => item.toolId === tool && item.profileId === profile,
          )
        ) {
          profile = "";
        }
      }
      if (campaignId === current.campaign && tool === current.tool && profile === current.profile) {
        return current;
      }
      return { ...current, campaign: campaignId, tool, profile };
    });
  }, [
    filters.campaign,
    filters.dateFrom,
    filters.dateTo,
    filters.profile,
    filters.tool,
    state.dataset,
    view,
  ]);
  const setTrendKind = useCallback(
    (kind: TrendKind) => setTrend((current) => ({ ...current, kind, point: "" })),
    [],
  );
  const setTrendRange = useCallback(
    (range: TrendRange) => setTrend((current) => ({ ...current, range })),
    [],
  );
  const selectTrendPoint = useCallback(
    (point: string) => setTrend((current) => ({ ...current, point })),
    [],
  );
  const setTrendParts = useCallback(
    (parts: string[]) =>
      setTrend((current) => ({ ...current, parts, point: "" })),
    [],
  );
  const rangedCampaigns = state.dataset
    ? campaignsInDateRange(state.dataset, filters.dateFrom, filters.dateTo)
    : [];
  const campaignSelectValue = rangedCampaigns.some(
    (item) => item.id === filters.campaign,
  )
    ? filters.campaign
    : "";
  const changeCampaign = (campaign: string) =>
    setFilters((current) => ({
      ...current,
      campaign,
      tool: "",
      profile: "",
    }));
  const changeDateFrom = (dateFrom: string) =>
    setFilters((current) => ({
      ...current,
      campaign: "",
      dateFrom,
      tool: "",
      profile: "",
    }));
  const changeDateTo = (dateTo: string) =>
    setFilters((current) => ({
      ...current,
      campaign: "",
      dateTo,
      tool: "",
      profile: "",
    }));

  if (view === "about") {
    return (
      <>
        <SiteHeader dataset={state.dataset} />
        <main
          className="dashboard dashboard--about"
          style={
            { "--workspace-height": `${workspaceHeight}px` } as CSSProperties
          }
        >
          <CampaignSelection
            campaigns={rangedCampaigns}
            campaignValue={campaignSelectValue}
            dateFrom={filters.dateFrom}
            dateTo={filters.dateTo}
            disabled
            emptyLabel={
              state.dataset
                ? "No campaigns in range"
                : "Campaign evidence unavailable"
            }
            onCampaignChange={changeCampaign}
            onDateFromChange={changeDateFrom}
            onDateToChange={changeDateTo}
          />
          <section
            className="workspace-bar"
            aria-label="Dashboard controls"
            ref={workspaceRef}
          >
            <ViewTabs view={view} onSelect={setView} />
          </section>
          <div
            className="view-panel"
            role="tabpanel"
            id="dashboard-view-panel"
            aria-labelledby="about-tab"
            tabIndex={0}
          >
            <AboutView />
          </div>
        </main>
        <footer>
          <span>SVTORTURE · Apache-2.0</span>
        </footer>
      </>
    );
  }

  if (state.error) {
    return (
      <main className="loading">
        <span className="brand__mark">SV</span>
        <h1>Evidence dataset unavailable</h1>
        <p>{state.error}</p>
      </main>
    );
  }
  if (!state.dataset) {
    return (
      <main className="loading">
        <span className="brand__mark">SV</span>
        <p>Loading campaign evidence…</p>
      </main>
    );
  }

  const dataset = state.dataset;
  const campaign = selectedCampaign(
    dataset,
    filters.campaign,
    filters.dateFrom,
    filters.dateTo,
  );
  const filtered = filterCorpus(dataset, filters, campaign);
  const requirementEvidenceCases = new Map<string, typeof dataset.cases>();
  for (const tool of campaign?.tools ?? []) {
    for (const profile of tool.profile_ids) {
      const key = `${tool.definition.id}/${profile}`;
      requirementEvidenceCases.set(
        key,
        filterCorpus(
          dataset,
          {
            ...filters,
            tool: tool.definition.id,
            profile,
          },
          campaign,
        ).requirementCases,
      );
    }
  }
  const visibleCampaigns = rangedCampaigns.filter(
    (item) =>
      (!campaignSelectValue || item.id === campaign?.id) &&
      ((!filters.tool && !filters.profile) ||
        item.tools.some(
          (tool) =>
            (!filters.tool || tool.definition.id === filters.tool) &&
            (!filters.profile || tool.profile_ids.includes(filters.profile)),
        )),
  );
  const resetLocalFilters = () =>
    setFilters((current) => ({
      ...EMPTY_FILTERS,
      campaign: current.campaign,
      dateFrom: current.dateFrom,
      dateTo: current.dateTo,
    }));
  const inspectToolCases = (
    tool: string,
    profile: string,
    requirement = "",
  ) => {
    setFilters((current) => ({
      ...EMPTY_FILTERS,
      campaign: current.campaign,
      dateFrom: current.dateFrom,
      dateTo: current.dateTo,
      tool,
      profile,
      requirement,
    }));
    setView("evidence");
  };
  const inspectRequirementToolCases = (
    tool: string,
    profile: string,
    requirement: string,
  ) => {
    setFilters((current) => ({
      ...current,
      tool,
      profile,
      requirement,
      caseId: "",
      requirementId: "",
    }));
    setView("evidence");
  };
  const inspectCase = (caseId: string) => {
    setFilters((current) => ({
      ...EMPTY_FILTERS,
      campaign: current.campaign,
      dateFrom: current.dateFrom,
      dateTo: current.dateTo,
      tool: current.tool,
      profile: current.profile,
      caseId,
    }));
    setView("evidence");
  };
  const inspectRequirement = (requirementId: string) => {
    setFilters((current) => ({
      ...EMPTY_FILTERS,
      campaign: current.campaign,
      dateFrom: current.dateFrom,
      dateTo: current.dateTo,
      tool: current.tool,
      profile: current.profile,
      requirementId,
    }));
    setView("matrix");
  };
  return (
    <>
      <SiteHeader dataset={dataset} />

      <main
        className={`dashboard${view === "trends" ? " dashboard--trends" : ""}`}
        style={{ "--workspace-height": `${workspaceHeight}px` } as CSSProperties}
      >
        <CampaignSelection
          campaigns={rangedCampaigns}
          campaignValue={campaignSelectValue}
          dateFrom={filters.dateFrom}
          dateTo={filters.dateTo}
          disabled={view === "trends"}
          emptyLabel="No campaigns in range"
          onCampaignChange={changeCampaign}
          onDateFromChange={changeDateFrom}
          onDateToChange={changeDateTo}
        />

        {view === "matrix" && (
          <CorpusCoverage
            kind="requirements"
            metric={dataset.corpus_coverage.requirements}
          />
        )}
        {view === "evidence" && (
          <CorpusCoverage kind="cases" metric={dataset.corpus_coverage.cases} />
        )}

        <section
          className="workspace-bar"
          aria-label="Dashboard controls"
          ref={workspaceRef}
        >
          <ViewTabs view={view} onSelect={setView} />
          <Filters
              dataset={dataset}
              campaign={campaign}
              filters={filters}
              setFilters={setFilters}
              onReset={resetLocalFilters}
              mode={
                view === "matrix" || view === "evidence"
                  ? "corpus"
                  : view
              }
              trendKind={view === "trends" ? trend.kind : undefined}
              standardParts={dataset.corpus_coverage.requirements.breakdown}
              selectedParts={trend.parts}
            onSelectedPartsChange={setTrendParts}
          />
        </section>

        <div
          className={`view-panel${view === "trends" ? " view-panel--trends" : ""}`}
          role="tabpanel"
          id="dashboard-view-panel"
          aria-labelledby={`${view}-tab`}
          tabIndex={0}
        >
          {view === "overview" && (
            <HeadlineMetrics
              dataset={dataset}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              onSelectTool={(tool, profile) =>
                inspectToolCases(tool, profile)
              }
            />
          )}
          {view === "matrix" && (
            <RequirementsView
              requirements={filtered.requirements}
              cases={filtered.requirementCases}
              evidenceCasesByProfile={requirementEvidenceCases}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              selectedRequirementId={filters.requirementId}
              onSelectRequirement={(requirementId) =>
                setFilters((current) => ({ ...current, requirementId }))
              }
              onInspectCase={inspectCase}
              onInspectEvidence={inspectRequirementToolCases}
            />
          )}
          {view === "evidence" && (
            <EvidenceView
              requirements={dataset.requirements}
              cases={filtered.cases}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              selectedCaseId={filters.caseId}
              onSelectCase={(caseId) =>
                setFilters((current) => ({ ...current, caseId }))
              }
              onInspectRequirement={inspectRequirement}
            />
          )}
          {view === "trends" && (
            <TrendsView
              dataset={dataset}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              trend={trend.kind}
              range={trend.range}
              selectedPointKey={trend.point}
              selectedParts={trend.parts}
              onTrendChange={setTrendKind}
              onRangeChange={setTrendRange}
              onSelectPoint={selectTrendPoint}
            />
          )}
          {view === "campaigns" && <CampaignView campaigns={visibleCampaigns} />}
        </div>
      </main>
      {view !== "trends" && (
        <footer>
          <span>SVTORTURE · Apache-2.0</span>
        </footer>
      )}
    </>
  );
}
