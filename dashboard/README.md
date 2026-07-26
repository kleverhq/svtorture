# Dashboard

The dashboard is a static evidence browser for one or more SVTORTURE campaigns.
It shows what each tool did, why the framework classified that observation as it
did, and which IEEE requirements the selected cases cover. It has no application
server or live database.

## Views

The interface provides five URL-filtered views. **Overview** is shown by default:

- **Overview** — a compact sortable tool table with requirement-level Pass,
  Fail, and Unclear totals, pass rate, and the reported tool version;
- **Requirements** — a compact requirement/tool matrix with grouped verdicts,
  sticky identity columns, and a separate requirement inspector;
- **Cases** — a master-detail case list with inline local source viewing,
  exact normalized results, diagnostics, output hashes/excerpts, reproduction
  commands, and a return path to the requirement inspector;
- **Trends** — one selectable historical chart for Tool pass rate, Requirements
  Coverage, Cases Coverage, Requirements Density, or Cases Density, with rolling
  UTC ranges, wheel/pinch and slider zoom, reference levels, and point provenance;
- **Campaigns** — compact run records with expandable corpus, tool source,
  image, platform, and trust provenance.

Requirements and Cases include a compact corpus summary that expands into all
standard chapters and annexes. Requirements Coverage is unique referenced
anchors divided by all standard anchors; its Density is unique
requirement–anchor links divided by covered anchors. Cases Coverage is unique
requirements linked from cases divided by all catalog requirements; its Density
is unique case–requirement links divided by covered requirements. Primary and
related case requirements both count.

Overview outcome totals use the requirement-weighted metric: every mandatory
variant must conform for a requirement to pass, while unclear requirements remain
in the denominator. The headline metric is defined in [the conformance
methodology](../docs/methodology.md). Missing, inapplicable, incomplete, and
nonconforming evidence remains visible rather than being collapsed into a
pass/fail percentage.

## Architecture and stack

```text
campaign.json files
        ↓
Python validation and dataset export
        ↓
dashboard/dist/data/dataset.json
        ↓
static React application
```

The frontend uses:

- React 19 and TypeScript 7;
- Vite 8 for the static production build;
- TanStack Table and TanStack Virtual for large evidence matrices;
- ECharts for trend visualization;
- Vitest, Testing Library, and jsdom for unit tests.

`src/svtorture/publish.py` validates campaigns and creates the versioned dataset.
The React model derives filters, comparable-campaign changes, and aggregate
presentation from that immutable data. View, campaign, date range, trend, trend
range, selected trend point, tool, profile, search, status, advanced filters, selected
evidence case, and requirement are encoded in the URL so an investigation can be
shared or revisited. Broad matrix statuses are presentation categories only; evidence retains every
exact result status and reason together with the target phase, the phase the
command attempted through, and whether attribution is direct, cumulative, or
not observed. Synthetic unsupported, unavailable, and inapplicable results use
`not-observed` and have no attempted-through observation.

The page header selects the campaign for campaign-scoped views. Optional inclusive
`From` and `To` dates narrow the campaign dropdown; an empty selection resolves to
the latest campaign in that range. Trends keeps all three controls visible but
disabled and ignores their values: its week, month, six-month, year, and all-time
UTC windows are independent. Tool and profile facets are available on Overview,
Requirements, Cases, Trends, and Campaigns. On Trends they apply only to Tool
pass rate and are disabled for corpus-wide measurements without discarding their
URL-backed selections. Overview, Trends, and Campaigns intentionally expose only
quick controls; Search and less common controls remain
inside collapsed Advanced filters on Requirements and Cases.

Trends displays exactly one measurement at a time and defaults to Tool pass rate.
Pass-rate and Coverage charts mark 100% saturation with headroom above it.
Density charts mark 1× and 2×. Each campaign freezes the exact integer operands
for all four corpus measurements, so historical points remain tied to the corpus
that produced them. Non-default state uses the strict URL parameters `trend`,
`trendRange`, and `trendPoint` under `view=trends`.

The site header provides `Auto`, `Light`, and `Dark` themes. `Auto` is the default and
follows the browser or operating-system color preference. An explicit selection
is saved in local storage for this dashboard origin; it does not alter datasets
or shared URLs.

A plain `npm run build` creates only the application assets; it does not embed
campaign evidence. `just dashboard-build` first builds those assets and then
exports selected campaigns to the ignored `dashboard/dist/data/dataset.json`.
Local exports may include local campaign evidence. Public Pages exports pass
additional provenance, image, repository-state, and private-material checks.
See [the architecture overview](../docs/architecture.md) for the complete data
flow.

## Local quick start

Run these commands from the repository root. First install dependencies:

```bash
just setup
```

If no campaign exists yet, run current Verilator against the complete corpus:

```bash
just latest verilator
```

The run prints a campaign path such as:

```text
.svtorture/campaigns/<campaign-id>/campaign.json
```

Build the frontend and export that campaign as a local dataset:

```bash
just dashboard-build ".svtorture/campaigns/<campaign-id>/campaign.json"
```

Start the static server:

```bash
just dashboard-serve
```

Open <http://localhost:4173>. Stop the server with `Ctrl-C`.

To compare several campaigns, pass their paths as one quoted argument:

```bash
just dashboard-build ".svtorture/campaigns/<first>/campaign.json .svtorture/campaigns/<second>/campaign.json"
just dashboard-serve
```

Re-run `just dashboard-build` after changing the campaign selection. The
campaigns, generated application, and local dataset remain in ignored
`.svtorture/` and `dashboard/dist/` directories.

## Development checks

```bash
npm --prefix dashboard run typecheck
npm --prefix dashboard test
npm --prefix dashboard run build
```

The root `just frontend` target runs all three checks. Dataset construction and
public export policy are implemented in `src/svtorture/publish.py`; conformance
terminology is authoritative in
[docs/methodology.md](../docs/methodology.md).
