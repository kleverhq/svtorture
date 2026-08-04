import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
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
  filterCorpus,
  filterValueList,
  filtersFromSearch,
  filtersToSearch,
  requirementsQuickFilters,
  toggleFilterValue,
  corpusTrendPointKey,
  toolTrendPointKey,
  trendStateFromSearch,
  type TrendKind,
  type TrendRange,
} from "./model";
import { ThemeControl } from "./ThemeControl";
import type { CampaignSummary, CaseDefinition, DashboardIndex } from "./types";
import { useDashboard } from "./useDashboard";

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

function SiteHeader({
  index,
  historyCount,
}: {
  index: DashboardIndex | undefined;
  historyCount: number;
}) {
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
        {index && (
          <span>
            {index.campaigns.length} available · {historyCount} archived
          </span>
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
  campaigns: CampaignSummary[];
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
  const [view, setView] = useState<View>(initialView);
  const [filters, setFilters] = useState(() => filtersFromSearch(window.location.search));
  const state = useDashboard(
    filters.campaign,
    filters.dateFrom,
    filters.dateTo,
    view === "trends" || view === "about",
    view !== "trends" && view !== "about",
    filters.changed,
  );
  const [trend, setTrend] = useState(() =>
    trendStateFromSearch(window.location.search),
  );
  const [workspaceHeight, setWorkspaceHeight] = useState(0);
  const workspaceRef = useRef<HTMLElement>(null);
  const availableIds = new Set(state.index?.campaigns.map((campaign) => campaign.id) ?? []);
  const rangedCampaigns = (state.trends?.campaigns ?? [])
    .filter((campaign) => {
      const date = campaign.finished_at.slice(0, 10);
      return (
        availableIds.has(campaign.id) &&
        (!filters.dateFrom || date >= filters.dateFrom) &&
        (!filters.dateTo || date <= filters.dateTo)
      );
    })
    .sort(
      (left, right) =>
        right.finished_at.localeCompare(left.finished_at) ||
        right.id.localeCompare(left.id),
    );
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
  }, [state.dataset, state.index, view]);
  useEffect(() => {
    const history = state.trends;
    if (!history) return;
    setTrend((current) => {
      const latest = history.campaigns.at(-1);
      const availableParts = new Set(
        latest?.corpus_metrics.requirements.breakdown.map(
          (part) => `${part.kind}:${part.id}`,
        ) ?? [],
      );
      const parts = current.parts.filter((part) => availableParts.has(part));
      const pointIsValid =
        !current.point ||
        (current.kind === "pass-rate"
          ? history.campaigns.some((campaign) =>
              campaign.tool_metrics.some(
                (point) => toolTrendPointKey(point, campaign.id) === current.point,
              ),
            )
          : history.campaigns.some(
              (campaign) =>
                corpusTrendPointKey(campaign, "requirements") === current.point ||
                corpusTrendPointKey(campaign, "cases") === current.point,
            ));
      if (pointIsValid && parts.length === current.parts.length) return current;
      return { ...current, parts, point: pointIsValid ? current.point : "" };
    });
  }, [state.trends]);
  useEffect(() => {
    const dataset = state.dataset;
    if (!dataset) return;
    setFilters((current) => {
      let tool = current.tool;
      let profile = current.profile;
      if (view === "overview") {
        const selected = dataset.campaigns[0];
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
      if (tool === current.tool && profile === current.profile) return current;
      return { ...current, tool, profile };
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
  const selectedRequirementTags = useMemo(
    () => filterValueList(filters.requirementTags),
    [filters.requirementTags],
  );
  const corpusFilterDependency =
    view === "matrix"
      ? JSON.stringify([
          filters.tool,
          filters.profile,
          filters.statusGroup,
          filters.requirementTags,
          filters.changed,
          filters.disagreement,
        ])
      : filters;
  const corpusFilters = useMemo(() => {
    if (view === "matrix") return requirementsQuickFilters(filters);
    if (view === "evidence") return { ...filters, requirementTags: "" };
    return filters;
  }, [corpusFilterDependency, view]);
  const selectedCampaign = useMemo(
    () =>
      state.dataset?.campaigns.find((item) => item.id === state.selectedId),
    [state.dataset, state.selectedId],
  );
  const filteredCorpus = useMemo(
    () =>
      state.dataset && view !== "about" && view !== "trends"
        ? filterCorpus(state.dataset, corpusFilters, selectedCampaign)
        : undefined,
    [corpusFilters, selectedCampaign, state.dataset, view],
  );
  const requirementEvidenceCases = useMemo(() => {
    const result = new Map<string, CaseDefinition[]>();
    if (!state.dataset || view !== "matrix") return result;
    for (const tool of selectedCampaign?.tools ?? []) {
      for (const profile of tool.profile_ids) {
        result.set(
          `${tool.definition.id}/${profile}`,
          filterCorpus(
            state.dataset,
            {
              ...corpusFilters,
              tool: tool.definition.id,
              profile,
            },
            selectedCampaign,
          ).requirementCases,
        );
      }
    }
    return result;
  }, [corpusFilters, selectedCampaign, state.dataset, view]);
  const inspectRequirementToolCases = useCallback(
    (tool: string, profile: string, requirement: string) => {
      setFilters((current) => ({
        ...current,
        tool,
        profile,
        requirement,
        caseId: "",
        requirementId: "",
      }));
      setView("evidence");
    },
    [],
  );
  const inspectCase = useCallback((caseId: string) => {
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
  }, []);
  const selectRequirement = useCallback((requirementId: string) => {
    setFilters((current) => ({ ...current, requirementId }));
  }, []);
  const changeSelectedSections = useCallback((sections: string[]) => {
    setFilters((current) => ({
      ...current,
      sections: sections.join(","),
      requirementId: "",
    }));
  }, []);
  const toggleRequirementTag = useCallback((tag: string) => {
    setFilters((current) => ({
      ...current,
      requirementTags: toggleFilterValue(current.requirementTags, tag),
      requirementId: "",
    }));
  }, []);
  const selectableCampaigns =
    view === "trends" || view === "about"
      ? (state.trends?.campaigns ?? []).filter((campaign) => availableIds.has(campaign.id))
      : rangedCampaigns;
  const campaignSelectValue = selectableCampaigns.some(
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
        <SiteHeader
          index={state.index}
          historyCount={state.trends?.campaigns.length ?? 0}
        />
        <main
          className="dashboard dashboard--about"
          style={
            { "--workspace-height": `${workspaceHeight}px` } as CSSProperties
          }
        >
          <CampaignSelection
            campaigns={selectableCampaigns}
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
          {state.error && (
            <p className="empty-state" role="status">
              Campaign data unavailable: {state.error}
            </p>
          )}
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

  if (view === "trends" && state.index && state.trends) {
    const latest = state.trends.campaigns.at(-1);
    return (
      <>
        <SiteHeader index={state.index} historyCount={state.trends.campaigns.length} />
        <main
          className="dashboard dashboard--trends"
          style={{ "--workspace-height": `${workspaceHeight}px` } as CSSProperties}
        >
          <CampaignSelection
            campaigns={selectableCampaigns}
            campaignValue={campaignSelectValue}
            dateFrom={filters.dateFrom}
            dateTo={filters.dateTo}
            disabled
            emptyLabel="Campaign detail unavailable"
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
            <Filters
              history={state.trends}
              filters={filters}
              setFilters={setFilters}
              onReset={() => undefined}
              mode="trends"
              trendKind={trend.kind}
              standardParts={latest?.corpus_metrics.requirements.breakdown ?? []}
              selectedParts={trend.parts}
              onSelectedPartsChange={setTrendParts}
            />
          </section>
          <div
            className="view-panel view-panel--trends"
            role="tabpanel"
            id="dashboard-view-panel"
            aria-labelledby="trends-tab"
            tabIndex={0}
          >
            <TrendsView
              history={state.trends}
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
          </div>
        </main>
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
  if (state.unavailable) {
    return (
      <main className="loading">
        <span className="brand__mark">SV</span>
        <h1>Campaign detail is not available on this site</h1>
        <p><code>{state.unavailable.id}</code> remains in immutable history.</p>
        {state.unavailable.archive && (
          <a href={state.unavailable.archive.release_url}>Open campaign Release ↗</a>
        )}
      </main>
    );
  }
  if (!state.dataset) {
    return (
      <main className="loading">
        <span className="brand__mark">SV</span>
        <p>{state.loading ? "Loading campaign evidence…" : "No campaigns match this date range."}</p>
      </main>
    );
  }

  const dataset = state.dataset;
  const campaign = selectedCampaign;
  const filtered = filteredCorpus!;
  const visibleCampaigns = campaign
    ? [campaign].filter(
        (item) =>
          (!filters.tool && !filters.profile) ||
          item.tools.some(
            (tool) =>
              (!filters.tool || tool.definition.id === filters.tool) &&
              (!filters.profile || tool.profile_ids.includes(filters.profile)),
          ),
      )
    : [];
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
      <SiteHeader
        index={state.index}
        historyCount={state.trends?.campaigns.length ?? 0}
      />

      <main
        className={`dashboard${view === "trends" ? " dashboard--trends" : ""}`}
        style={{ "--workspace-height": `${workspaceHeight}px` } as CSSProperties}
      >
        <CampaignSelection
          campaigns={selectableCampaigns}
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
              history={state.trends}
              filters={filters}
              setFilters={setFilters}
              onReset={resetLocalFilters}
              mode={
                view === "matrix"
                  ? "requirements"
                  : view === "evidence"
                    ? "cases"
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
              allRequirements={dataset.requirements}
              standardSections={dataset.standard_sections}
              selectedSections={filters.sections
                .split(",")
                .filter(Boolean)}
              onSelectedSectionsChange={changeSelectedSections}
              selectedTags={selectedRequirementTags}
              onToggleTag={toggleRequirementTag}
              cases={filtered.requirementCases}
              evidenceCasesByProfile={requirementEvidenceCases}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              selectedRequirementId={filters.requirementId}
              onSelectRequirement={selectRequirement}
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
              loadCaseEvidence={state.loadCaseEvidence}
            />
          )}
          {view === "trends" && (
            <TrendsView
              history={state.trends!}
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
