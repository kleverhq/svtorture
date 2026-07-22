import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
} from "react";

import { CampaignView } from "./CampaignView";
import { EvidenceView } from "./EvidenceView";
import { Filters } from "./Filters";
import { HeadlineMetrics } from "./HeadlineMetrics";
import { HistoryView } from "./HistoryView";
import { MatrixView } from "./MatrixView";
import {
  EMPTY_FILTERS,
  campaignsInDateRange,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  selectedCampaign,
} from "./model";
import { ThemeControl } from "./ThemeControl";
import { useDataset } from "./useDataset";

type View = "overview" | "matrix" | "evidence" | "history" | "campaigns";

const VIEWS: Array<{ id: View; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "matrix", label: "Requirements" },
  { id: "evidence", label: "Cases" },
  { id: "history", label: "Changes" },
  { id: "campaigns", label: "Campaigns" },
];

function initialView(): View {
  const requested = new URLSearchParams(window.location.search).get("view");
  return VIEWS.some((view) => view.id === requested)
    ? (requested as View)
    : "overview";
}

export default function App() {
  const state = useDataset();
  const [view, setView] = useState<View>(initialView);
  const [filters, setFilters] = useState(() => filtersFromSearch(window.location.search));
  const [workspaceHeight, setWorkspaceHeight] = useState(0);
  const workspaceRef = useRef<HTMLElement>(null);
  useEffect(() => {
    window.history.replaceState(null, "", filtersToSearch(filters, view));
  }, [filters, view]);
  useLayoutEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const measure = () => setWorkspaceHeight(workspace.getBoundingClientRect().height);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(workspace);
    return () => observer.disconnect();
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
  const rangedCampaigns = campaignsInDateRange(
    dataset,
    filters.dateFrom,
    filters.dateTo,
  );
  const campaign = selectedCampaign(
    dataset,
    filters.campaign,
    filters.dateFrom,
    filters.dateTo,
  );
  const filtered = filterCorpus(dataset, filters, campaign);
  const campaignSelectValue = rangedCampaigns.some(
    (item) => item.id === filters.campaign,
  )
    ? filters.campaign
    : "";
  const campaignNeedle = filters.search.toLocaleLowerCase();
  const visibleCampaigns = rangedCampaigns.filter(
    (item) =>
      (!campaignSelectValue || item.id === campaign?.id) &&
      (!campaignNeedle ||
        [
          item.id,
          item.selection_name,
          item.repository.commit,
          item.platform,
          ...item.tools.flatMap((tool) => [
            tool.definition.id,
            tool.definition.display_name,
            tool.reported_version ?? "",
          ]),
        ]
          .join(" ")
          .toLocaleLowerCase()
          .includes(campaignNeedle)),
  );
  const resetLocalFilters = () =>
    setFilters((current) => ({
      ...EMPTY_FILTERS,
      campaign: current.campaign,
      dateFrom: current.dateFrom,
      dateTo: current.dateTo,
    }));
  const inspectCase = (caseId: string) => {
    setFilters((current) => ({ ...current, caseId }));
    setView("evidence");
  };
  const inspectRequirement = (requirementId: string) => {
    setFilters((current) => ({ ...current, requirementId }));
    setView("matrix");
  };
  const moveTabFocus = (
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
    <>
      <header className="site-header">
        <a className="brand" href="?" aria-label="SVTORTURE dashboard home">
          <span className="brand__mark">SV</span>
          <span>
            <strong>SVTORTURE</strong>
          </span>
        </a>
        <div className="site-header__meta">
          <span className={`visibility visibility--${dataset.visibility}`}>
            {dataset.visibility}
          </span>
          <span>{dataset.campaigns.length} campaigns</span>
          <a
            className="github-link"
            href="https://github.com/kleverhq/sv-torture"
            target="_blank"
            rel="noreferrer"
          >
            GitHub ↗
          </a>
          <ThemeControl />
        </div>
      </header>

      <main
        className="dashboard"
        style={{ "--workspace-height": `${workspaceHeight}px` } as CSSProperties}
      >
        <section className="campaign-overview" aria-label="Campaign selection">
          <label className="campaign-overview__campaign">
            <span>Campaign</span>
            <select
              value={campaignSelectValue}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  campaign: event.target.value,
                  tool: "",
                  profile: "",
                }))
              }
            >
              <option value="">
                {rangedCampaigns.length ? "Latest campaign" : "No campaigns in range"}
              </option>
              {rangedCampaigns.map((item) => (
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
              max={filters.dateTo || undefined}
              value={filters.dateFrom}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  campaign: "",
                  dateFrom: event.target.value,
                  tool: "",
                  profile: "",
                }))
              }
            />
          </label>
          <label>
            <span>To</span>
            <input
              type="date"
              min={filters.dateFrom || undefined}
              value={filters.dateTo}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  campaign: "",
                  dateTo: event.target.value,
                  tool: "",
                  profile: "",
                }))
              }
            />
          </label>
        </section>

        <section
          className="workspace-bar"
          aria-label="Dashboard controls"
          ref={workspaceRef}
        >
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
                  onClick={() => setView(item.id)}
                  onKeyDown={(event) => moveTabFocus(event, index)}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
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
          />
        </section>

        <div
          className="view-panel"
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
              searchFilter={filters.search}
              onSelectTool={(tool, profile) => {
                setFilters((current) => ({ ...current, tool, profile }));
                setView("matrix");
              }}
            />
          )}
          {view === "matrix" && (
            <MatrixView
              requirements={filtered.requirements}
              cases={filtered.cases}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              selectedRequirementId={filters.requirementId}
              onSelectRequirement={(requirementId) =>
                setFilters((current) => ({ ...current, requirementId }))
              }
              onInspectCase={inspectCase}
            />
          )}
          {view === "evidence" && (
            <EvidenceView
              requirements={filtered.requirements}
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
          {view === "history" && (
            <HistoryView
              dataset={dataset}
              campaign={campaign}
              toolFilter={filters.tool}
              profileFilter={filters.profile}
              searchFilter={filters.search}
            />
          )}
          {view === "campaigns" && <CampaignView campaigns={visibleCampaigns} />}
        </div>
      </main>
      <footer>
        <span>SVTORTURE · Apache-2.0</span>
      </footer>
    </>
  );
}
