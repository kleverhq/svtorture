import { useEffect, useState } from "react";

import { CampaignView } from "./CampaignView";
import { EvidenceView } from "./EvidenceView";
import { Filters } from "./Filters";
import { HeadlineMetrics } from "./HeadlineMetrics";
import { HistoryView } from "./HistoryView";
import { MatrixView } from "./MatrixView";
import {
  EMPTY_FILTERS,
  filterCorpus,
  filtersFromSearch,
  filtersToSearch,
  selectedCampaign,
} from "./model";
import { ThemeControl } from "./ThemeControl";
import { useDataset } from "./useDataset";

type View = "matrix" | "evidence" | "history" | "campaigns";

const VIEWS: Array<{ id: View; label: string }> = [
  { id: "matrix", label: "Requirements" },
  { id: "evidence", label: "Case evidence" },
  { id: "history", label: "Changes" },
  { id: "campaigns", label: "Campaigns" },
];

function initialView(): View {
  const requested = new URLSearchParams(window.location.search).get("view");
  return VIEWS.some((view) => view.id === requested) ? (requested as View) : "matrix";
}

export default function App() {
  const state = useDataset();
  const [view, setView] = useState<View>(initialView);
  const [filters, setFilters] = useState(() => filtersFromSearch(window.location.search));
  useEffect(() => {
    window.history.replaceState(null, "", filtersToSearch(filters, view));
  }, [filters, view]);

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
  const datedCampaign = filters.date
    ? [...dataset.campaigns]
        .filter((campaign) => campaign.finished_at.startsWith(filters.date))
        .sort((left, right) => right.finished_at.localeCompare(left.finished_at))[0]
    : undefined;
  const campaign = filters.campaign
    ? selectedCampaign(dataset, filters.campaign)
    : (datedCampaign ?? selectedCampaign(dataset, ""));
  const filtered = filterCorpus(dataset, filters, campaign);
  const visibleCampaigns = dataset.campaigns.filter(
    (item) =>
      (!filters.campaign || item.id === filters.campaign) &&
      (!filters.date || item.finished_at.startsWith(filters.date)),
  );
  const repository = campaign?.trust.repository;
  const inspectCase = (caseId: string) => {
    setFilters((current) => ({ ...current, caseId }));
    setView("evidence");
  };
  const inspectRequirement = (requirementId: string) => {
    setFilters((current) => ({ ...current, requirementId }));
    setView("matrix");
  };

  return (
    <>
      <header className="site-header">
        <a className="brand" href="?" aria-label="SVTORTURE dashboard home">
          <span className="brand__mark">SV</span>
          <span>
            <strong>SVTORTURE</strong>
            <small>Conformance evidence</small>
          </span>
        </a>
        <div className="site-header__meta">
          <span className={`visibility visibility--${dataset.visibility}`}>
            {dataset.visibility}
          </span>
          <span>{dataset.campaigns.length} campaigns</span>
          {repository && <a href={`https://github.com/${repository}`}>Source</a>}
          <ThemeControl />
        </div>
      </header>

      <main className="dashboard">
        <section className="campaign-overview" aria-labelledby="overview-title">
          <div>
            <span className="section-label">
              {filters.campaign ? "Selected campaign" : "Latest campaign"}
            </span>
            <h1 id="overview-title">Conformance overview</h1>
            {campaign ? (
              <p>
                <strong>{new Date(campaign.finished_at).toLocaleString()}</strong>
                <code>{campaign.id}</code>
              </p>
            ) : (
              <p>No campaign matches the current selection.</p>
            )}
          </div>
          {campaign && (
            <dl className="campaign-overview__facts">
              <div>
                <dt>Run</dt>
                <dd>{campaign.selection_name}</dd>
              </div>
              <div>
                <dt>State</dt>
                <dd className={campaign.complete ? "text-pass" : "text-issue"}>
                  {campaign.complete ? "Complete" : "Incomplete"}
                </dd>
              </div>
              <div>
                <dt>Repository</dt>
                <dd>
                  <code>{campaign.repository.commit.slice(0, 12)}</code>
                  {campaign.repository.dirty ? " · dirty" : " · clean"}
                </dd>
              </div>
            </dl>
          )}
        </section>

        <HeadlineMetrics dataset={dataset} campaign={campaign} />

        <section className="workspace-bar" aria-label="Dashboard controls">
          <nav className="view-tabs" aria-label="Dashboard views">
            {VIEWS.map((item) => (
              <button
                type="button"
                key={item.id}
                aria-current={view === item.id ? "page" : undefined}
                onClick={() => setView(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <Filters
            dataset={dataset}
            campaign={campaign}
            filters={filters}
            setFilters={setFilters}
            onReset={() => setFilters({ ...EMPTY_FILTERS })}
          />
        </section>

        {view === "matrix" && (
          <MatrixView
            requirements={filtered.requirements}
            cases={filtered.cases}
            campaign={campaign}
            toolFilter={filters.tool}
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
            dateFilter={filters.date}
          />
        )}
        {view === "campaigns" && <CampaignView campaigns={visibleCampaigns} />}
      </main>
      <footer>
        <span>SVTORTURE · Apache-2.0</span>
        <span>Immutable campaign evidence</span>
      </footer>
    </>
  );
}
