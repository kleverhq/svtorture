# Dashboard

The dashboard is a static evidence browser for one or more SVTORTURE campaigns.
It shows what each tool did, why the framework classified that observation as it
did, and which IEEE requirements the selected cases cover. It has no application
server or live database.

## Views

The interface provides four URL-filtered views:

- **Requirements matrix** — requirement-level status across selected tool
  profiles;
- **Case evidence** — case metadata, normalized results, diagnostics, and
  retained output excerpts;
- **History & compare** — metric history and changes between campaigns;
- **Campaign provenance** — corpus, tool source, image, platform, and trust
  information needed to understand a run.

The headline metric is defined in
[the conformance methodology](../docs/methodology.md). Missing, unsupported,
incomplete, and nonconforming evidence remains visible rather than being
collapsed into a pass/fail percentage.

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
- ECharts for history visualization;
- Vitest, Testing Library, and jsdom for unit tests.

`src/svtorture/publish.py` validates campaigns and creates the versioned dataset.
The React model derives filters, comparisons, and aggregate presentation from
that immutable data. Filters are encoded in the URL so a selected view can be
shared or revisited.

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
