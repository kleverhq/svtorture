# Dashboard

The dashboard is a static evidence browser for one or more SVTORTURE campaigns.
It shows what each tool did, why the framework classified that observation as it
did, and which IEEE requirements the selected cases cover. It has no application
server or live database.

## Views

The interface provides six URL-backed views. **Overview** is shown by default:

- **Overview** — a compact sortable tool table with requirement-level Pass,
  Fail, and Unclear totals, pass rate, and the reported tool version. Selecting
  a Tool/Profile opens its filtered Cases;
- **Requirements** — a master-detail requirement list with compact grouped
  verdicts, standard anchors, supporting cases, and vertical tool evidence.
  Selecting a Tool evidence row opens Cases filtered by that Tool/Profile and
  the exact linked Requirement;
- **Cases** — a master-detail case list with inline local source viewing,
  exact normalized results, diagnostics, output hashes/excerpts, reproduction
  commands, and a return path to the requirement inspector;
- **Trends** — one selectable historical chart for Pass rate, Coverage, or
  Density. Coverage and Density each compare Requirements and Cases lines, with
  rolling UTC ranges, zoom, reference levels, and point provenance;
- **Campaigns** — compact run records with expandable corpus, tool source,
  image, platform, and trust provenance;
- **About** — an illustrated guide from IEEE anchors and requirements through
  cases, tools, campaign evidence, reproduction, and publication.

Requirements and Cases include a compact corpus summary that expands into all
standard chapters and annexes. Requirements Coverage is unique referenced
anchors divided by eligible standard anchors after waiver-only exclusions; its
breakdown also shows the excluded count, and its Density is unique
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
canonical campaign.json files
        ↓ validate and export
portable campaign bundles
        ↓ assemble
index + trends + selected manifest/catalog/verdicts
        ↓ open one case
one case-centric evidence shard
```

The frontend uses:

- React 19 and TypeScript 7;
- Vite 8 for the static production build;
- ECharts for trend visualization;
- Vitest, Testing Library, and jsdom for unit tests.

`src/svtorture/publish.py` owns the public trust gate, while
`src/svtorture/bundle.py` creates and validates the strict version-6 portable
resources. The browser loads `data/index.json` and `data/trends.json` first,
then the selected campaign's manifest, catalog, and compact verdicts. Full
observations remain unloaded until a case detail requests its evidence shard.
The React model derives filters, comparable-campaign changes, and aggregate
presentation from those immutable resources. View, campaign, date range, trend, trend
range, selected trend point, tool, profile, search, status, advanced filters,
selected evidence entities, and the exact linked-Requirement Case filter are
encoded in the URL so an investigation can be shared or revisited. Grouped requirement statuses are presentation categories only; evidence retains every
exact result status and reason together with the target phase, the phase the
command attempted through, and whether attribution is direct, cumulative, or
not observed. Synthetic unsupported, unavailable, and inapplicable results use
`not-observed` and have no attempted-through observation.

The page header selects the campaign for campaign-scoped views. Optional inclusive
`From` and `To` dates narrow the campaign dropdown; an empty selection resolves to
the latest campaign in that range. Trends keeps all three controls visible but
disabled and ignores their values: its week, month, three-month, six-month, year,
and all-time UTC windows are independent, and all-time is the default. Tool and profile facets are available on Overview,
Requirements, Cases, Trends, and Campaigns. Trends shows Tool/Profile facets for
Pass rate and replaces them with a chapter/annex multiselect for Coverage and
Density without discarding either URL-backed selection. Overview, Trends, and Campaigns intentionally expose only
quick controls; Search and less common controls remain
inside collapsed Advanced filters on Requirements and Cases.

Trends displays exactly one measurement at a time and defaults to Pass rate.
Pass-rate and Coverage charts mark 100% and retain unlabeled headroom above it;
Density marks 1× and 2×. Coverage and Density show Requirements and Cases as two
lines. Each campaign freezes aggregate and per-part integer operands, so any
chapter/annex combination remains tied to its historical corpus. Non-default
state uses `trend`, repeated `chapter`, `trendRange`, and `trendPoint` under
`view=trends`. Case and requirement detail headers provide `Copy link` actions. They copy canonical, path-aware URLs containing the target view, case or
requirement identity, and displayed campaign when available, so the recipient sees
the same evidence context while unrelated investigation filters cannot hide the
shared entity. Opening one of these links reveals the selected requirement or case
list item. On desktop, both views keep a one-third list and two-thirds detail pane
with independent vertical scrolling; narrow and short viewports retain document
flow.

The site header provides `Auto`, `Light`, and `Dark` themes. `Auto` is the default and
follows the browser or operating-system color preference. An explicit selection
is saved in local storage for this dashboard origin; it does not alter datasets
or shared URLs.

A plain `npm run build` creates only the application assets; it does not embed
campaign evidence. `just dashboard-build` builds those assets, exports each
selected canonical campaign through a temporary portable bundle, and assembles
ignored `dashboard/dist/data/` resources. There is no `dataset.json`. Local
exports may include embedded local source links. Public Release exports pass
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

Build the frontend and export that campaign as local version-6 resources:

```bash
just dashboard-build ".svtorture/campaigns/<campaign-id>/campaign.json"
```

Start the static server:

```bash
just dashboard-serve
```

Open <http://localhost:4173>. Stop the server with `Ctrl-C`.

To compare several canonical campaigns, pass each path as a separate argument:

```bash
just dashboard-build ".svtorture/campaigns/<first>/campaign.json" ".svtorture/campaigns/<second>/campaign.json"
just dashboard-serve
```

Portable ZIPs and unpacked bundle directories use the same local path:

```bash
just dashboard-local "/path/to/first.zip" "/path/to/unpacked-second"
```

`dashboard-local` assembles all inputs and starts the server. Re-run
`just dashboard-build` after changing canonical campaign inputs. Generated
application and local data remain in ignored `.svtorture/` and
`dashboard/dist/` directories.

## Development checks

```bash
npm --prefix dashboard run typecheck
npm --prefix dashboard test
npm --prefix dashboard run build
```

The root `just frontend` target runs all three checks. Bundle construction is
implemented in `src/svtorture/bundle.py`, while public trust policy remains in
`src/svtorture/publish.py`; conformance terminology is authoritative in
[docs/methodology.md](../docs/methodology.md).
