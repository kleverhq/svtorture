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
  STATUS_LABELS,
  STATUS_SYMBOLS,
} from "./model";
import { useDataset } from "./useDataset";

type View = "matrix" | "evidence" | "history" | "campaigns";

const VIEWS: Array<{ id: View; label: string }> = [
  { id: "matrix", label: "Requirements matrix" },
  { id: "evidence", label: "Case evidence" },
  { id: "history", label: "History & compare" },
  { id: "campaigns", label: "Campaign provenance" },
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
        <p>Loading immutable campaign evidence…</p>
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

  return (
    <>
      <header className="site-header">
        <a className="brand" href="?" aria-label="SVTORTURE home">
          <span className="brand__mark">SV</span>
          <span>
            <strong>SVTORTURE</strong>
            <small>Standards evidence, not consensus</small>
          </span>
        </a>
        <div className="site-header__meta">
          <span className={`visibility visibility--${dataset.visibility}`}>
            {dataset.visibility} dataset
          </span>
          <span>{dataset.campaigns.length} immutable campaigns</span>
          {repository && (
            <a href={`https://github.com/${repository}`} aria-label="Repository">
              Source
            </a>
          )}
        </div>
      </header>
      <main>
        <section className="hero">
          <div>
            <span className="eyebrow">IEEE 1800 conformance framework</span>
            <h1>
              Verified support
              <em>in the covered corpus.</em>
            </h1>
          </div>
          <p>
            Requirements are scored once. Cases preserve phase, oracle, raw
            observation, exact tool source, image identity, and a reproducible judgment.
          </p>
        </section>

        <HeadlineMetrics dataset={dataset} campaign={campaign} />
        <Filters
          dataset={dataset}
          filters={filters}
          setFilters={setFilters}
          onReset={() => setFilters({ ...EMPTY_FILTERS })}
        />

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

        <aside className="status-legend" aria-label="Result status legend">
          {Object.entries(STATUS_LABELS).map(([status, label]) => (
            <span className={`legend legend--${status}`} key={status}>
              <b aria-hidden="true">{STATUS_SYMBOLS[status as keyof typeof STATUS_SYMBOLS]}</b>
              {label}
            </span>
          ))}
          <span className="legend legend--known-fail">
            <b aria-hidden="true">×</b>Known fail
          </span>
        </aside>

        {view === "matrix" && (
          <MatrixView
            requirements={filtered.requirements}
            cases={filtered.cases}
            campaign={campaign}
            toolFilter={filters.tool}
          />
        )}
        {view === "evidence" && (
          <EvidenceView
            requirements={filtered.requirements}
            cases={filtered.cases}
            campaign={campaign}
            toolFilter={filters.tool}
          />
        )}
        {view === "history" && (
          <HistoryView
            points={dataset.metrics}
            toolFilter={filters.tool}
            dateFilter={filters.date}
          />
        )}
        {view === "campaigns" && <CampaignView campaigns={visibleCampaigns} />}
      </main>
      <footer>
        <span>SVTORTURE · Apache-2.0</span>
        <span>
          Corpus consensus never defines the oracle. IEEE requirement metadata does.
        </span>
      </footer>
    </>
  );
}
