# Add an illustrated About guide to the dashboard

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with the repository's `exec-plan` skill.

## Purpose / Big Picture

A first-time visitor should be able to open the final dashboard tab, named **About**, and understand what SVTORTURE is without reading maintainer documentation first. The page will be a compact vertical visual guide: a sticky table of contents, short slide-like sections, and editable Draw.io PNG diagrams explain the path from the IEEE standard to traceable requirements, executable cases, tool runs, campaign evidence, and the dashboard itself. The same concise narrative and image assets will live under `docs/about/` as a standalone repository document.

The result is observable by starting the dashboard, selecting the last **About** tab, using the left-hand section links, and scrolling through six illustrated sections. It must remain readable on a narrow screen, require no campaign dataset to render, and add no frontend dependency.

## Non-Goals

This work does not change campaign execution, schemas, scoring, publication policy, tool integration, or requirement/case metadata. It does not add a general Markdown renderer, documentation site generator, carousel, scrollspy framework, animation library, or runtime image service. It does not claim complete standard coverage or superiority over another corpus; it explains the framework's current intent and mechanics neutrally.

## Progress

- [x] (2026-07-30 11:54Z) Read `task.md`, applicable repository guidance, the ExecPlan instructions, and the Draw.io visual-quality workflow.
- [x] (2026-07-30 13:06Z) Grounded the narrative and formulas in `docs/{architecture,methodology,annotation,reproduction}.md`, real requirement/case/tool manifests, and dashboard publication documentation.
- [x] (2026-07-30 13:09Z) Added failing component tests for the final URL-backed About tab, keyboard reachability, hidden campaign controls, six linked sections, and five accessible illustrations; focused Vitest fails only because the tab/component do not exist yet.
- [x] (2026-07-30 13:12Z) Created five editable `*.drawio.png` diagrams, passed XML/layout checks, exported with embedded Draw.io models, and visually inspected every PNG through the image-capable `read` tool; no clipping, collisions, or illegible labels remained.
- [x] (2026-07-30 13:17Z) Added `docs/about/README.md` and integrated its shared PNG assets into a dependency-free `AboutView`; Vite emitted all five hashed assets successfully.
- [x] (2026-07-30 13:20Z) Added the final URL-backed About tab, hidden irrelevant campaign/filter controls, sticky desktop and horizontal narrow table of contents, six vertical sections, and accessible figures.
- [x] (2026-07-30 13:22Z) Passed the initial 70 frontend tests, TypeScript typecheck, production build, and `just smoke`; visually inspected 1440×1100 and 500×900 browser screenshots.
- [x] (2026-07-30 13:39Z) Resolved all focused code, factual-content, and visual/accessibility review findings; every impacted reviewer returned no substantive findings on recheck.
- [x] (2026-07-30 13:40Z) Passed final `just ci`: 163 non-Docker Python, 11 Docker, and 72 dashboard tests; production build emitted all five PNG assets.
- [x] (2026-07-30 13:46Z) Completed a fresh independent control review; its only low finding was this stale plan progress, now corrected.
- [x] (2026-07-30 13:48Z) Completed the prompt-to-artifact audit: all six requested topics map to both docs and UI; five PNGs are valid, editable, shared, and visually reviewed; anchors are complete; no dependency or raw Draw.io source was added; tests cover tab order, URL/hash, no-data rendering, anchors, descriptions, and keyboard-scroll regions.
- [x] (2026-07-30 13:49Z) Committed and verified the completed work as `feat(dashboard): add illustrated About guide`.

## Surprises & Discoveries

- Observation: the dashboard has no Markdown dependency and Vite is configured with `publicDir: false`.
  Evidence: `dashboard/package.json` contains React and ECharts only, and `dashboard/vite.config.ts` disables the public directory. Imported PNG modules are therefore the smallest build-time asset path.

- Observation: Draw.io Desktop is installed locally.
  Evidence: `command -v drawio` resolves to `/snap/bin/drawio`, so exported PNG files can embed their editable Draw.io model and can be visually inspected before use.

- Observation: the Snap-packaged Draw.io cannot see the host `/tmp` namespace.
  Evidence: exports from `/tmp/svtorture-about-diagrams/*.drawio` reported “input file/directory not found”; copying the validated temporary XML into `docs/about/assets/` for export and deleting it immediately afterward succeeded.

- Observation: Vite can bundle imported PNG files from `docs/about/assets/` even though its project root is `dashboard/` and `publicDir` is disabled.
  Evidence: `npm --prefix dashboard run build` emitted five hashed `*.drawio-*.png` assets, allowing one canonical documentation asset set without a copy step.

- Observation: headless Chrome enforces an effective minimum CSS viewport around 500 pixels even when a 390-pixel screenshot is requested.
  Evidence: the 390×844 bitmap cropped a 500-pixel layout, while the actual 500×900 screenshot showed complete text, contained cards, wrapping, and intentional horizontal TOC scrolling. Desktop 1440×1100 also rendered cleanly.

## Decision Log

- Decision: write user-facing prose in English.
  Rationale: the existing dashboard and repository documentation are English; the user confirmed no blocking language question after this assumption was stated.
  Date/Author: 2026-07-30 / Pi

- Decision: use five PNG diagrams with embedded Draw.io data and names ending in `.drawio.png`.
  Rationale: PNG is directly inspectable by the available vision-capable `read` tool, while Draw.io's embedded model keeps each illustration editable without retaining a separate XML file. Five diagrams are enough to illustrate every section without making the page or repository heavy.
  Date/Author: 2026-07-30 / Pi

- Decision: keep the standalone guide in `docs/about/README.md`, place shared assets in `docs/about/assets/`, and import those assets from the React view.
  Rationale: this makes the guide independently browsable and ensures documentation and dashboard use exactly the same illustrations. The React page remains explicit JSX rather than introducing a Markdown runtime.
  Date/Author: 2026-07-30 / Pi

- Decision: omit campaign selection and evidence filters while About is active, and serialize only `view=about` in the URL.
  Rationale: these controls do not affect explanatory content. Hiding them makes the page read like a guide while preserving filter state in memory for the user's return to an evidence view.
  Date/Author: 2026-07-30 / Pi

- Decision: use semantic anchor links and CSS `position: sticky` rather than JavaScript scroll tracking.
  Rationale: native anchors satisfy navigation and accessibility with less code, no state synchronization, and graceful behavior on all supported browsers. On narrow screens the table of contents becomes a normal horizontal/flowing block.
  Date/Author: 2026-07-30 / Pi

## Outcomes & Retrospective

The illustrated guide, shared editable PNGs, tests, responsive styling, and documentation are implemented and committed. Focused validation, visual inspection, complete CI, three focused reviews, their clean rechecks, an independent control review, and the prompt-to-artifact audit all pass. The final About tab remains useful without campaign data, while the shared documentation and embedded Draw.io PNG models keep the explanation portable and editable.

## Context and Orientation

SVTORTURE is a standards-driven SystemVerilog conformance framework. An **anchor** is a stable identifier attached to a specific standard fragment such as a paragraph, list item, table, or figure. A **requirement** is a falsifiable statement distilled from one or more anchors. A **case** is executable source plus metadata and an oracle: the expected stage and outcome against which a tool is evaluated. A **tool profile** describes the deepest supported execution phase, such as elaboration or simulation. A **campaign** is one immutable evidence bundle containing selected cases, resolved tool identities, normalized results, diagnostics, outputs, and reproduction information. The dashboard is a browser for exported campaign evidence.

`docs/architecture.md` is authoritative for component boundaries and data flow. `docs/methodology.md` is authoritative for conformance terms and metric semantics. `src/svtorture/publish.py` controls dataset construction and visibility. The new `docs/about/README.md` must summarize and link to those sources rather than redefine their rules.

The React application lives in `dashboard/src/`. `dashboard/src/App.tsx` owns top-level navigation and chooses the active view. `dashboard/src/styles.css` owns the visual system and responsive layout. Existing tests under `dashboard/src/*.test.tsx` use Vitest, jsdom, and Testing Library. The new `dashboard/src/AboutView.tsx` must be a data-independent component so it can render even when no dataset is available.

The five planned illustrations are:

1. `standards-to-evidence.drawio.png`: IEEE 1800-2023 source, annotation and anchors, requirements, cases plus tools, runner, campaign, dashboard.
2. `traceable-requirements.drawio.png`: anchored source fragments distilled into linked falsifiable requirements, with concise coverage and density cues.
3. `executable-cases.drawio.png`: requirements materialized as source and an oracle, with accept, simulate, and stage-specific reject outcomes.
4. `tool-applicability.drawio.png`: nested preprocessing, parsing, elaboration, and simulation phases alongside profile, language-version, and case applicability checks.
5. `campaign-to-dashboard.drawio.png`: one bounded run producing immutable evidence, then local/public dashboard views, trends, reproducer links, and bug-report assistance.

## Open Questions

There are no blocking questions. Exact copy and diagram labels will be adjusted to match repository sources discovered during implementation. If a claim cannot be tied to current code or documentation, omit it rather than speculate.

## Plan of Work

First, read the authoritative architecture, methodology, metadata models, tool documentation, and publishing code. Convert the requested narrative into six short sections: overview; requirements; cases; tools; campaigns; dashboard. Keep each section to a title, one lead sentence, a few short facts, and one illustration or compact visual support. Link to the authoritative maintainer documents for details.

Second, add tests before production UI changes. `dashboard/src/AboutView.test.tsx` will require the table of contents to link to all six section IDs, require each section heading and all five meaningful image alternative texts, and prove that the component needs no dataset props. Extend `dashboard/src/App.test.tsx` to require **About** as the last tab and verify that selecting it reveals the guide. These tests should fail because the component and tab do not exist yet.

Third, create each diagram as a native Draw.io model, run the Draw.io layout checker, export to PNG with embedded XML, and delete the intermediate `.drawio` source as required by the Draw.io workflow. Open every `*.drawio.png` with the `read` tool. Check text legibility at dashboard width, clipping, spacing, arrow routing, color contrast, and conceptual accuracy. Revise and re-export until every image passes visual review. Never accept XML validation alone as evidence of diagram quality.

Fourth, create `docs/about/README.md` and `dashboard/src/AboutView.tsx`. The document and component will use the same headings and PNG files, but the component will use semantic HTML (`article`, `nav`, `section`, headings, lists, `figure`, `img`, and `figcaption`) for accessible navigation. Integrate the component as the final tab in `dashboard/src/App.tsx`. Add narrowly scoped styles to `dashboard/src/styles.css`, reusing existing color variables, type scale, cards, radii, and breakpoints. Desktop layout uses a narrow sticky table of contents beside one content column; narrow layout stacks the table above the sections. Images must use intrinsic dimensions, `max-width: 100%`, descriptive alt text, and lazy decoding/loading where appropriate.

Finally, run focused tests, all dashboard checks, the repository smoke/CI interface, and a real browser build. Start the local dashboard and capture a desktop and narrow screenshot if an installed browser permits it; inspect those screenshots through `read` just as the diagrams were inspected. Request focused correctness/content and visual/accessibility reviews, resolve all substantive findings, audit that only intended documentation/UI/PNG files are tracked, update this plan, and create a Conventional Commit.

### Concrete Steps

Run all commands from `/home/esynr3z/projects/sv-torture`.

Create the tests and prove they initially fail:

    npm --prefix dashboard test -- AboutView.test.tsx App.test.tsx

Generate each diagram through a temporary `.drawio` file under the repository so the Snap-confined Draw.io process can read it, then validate, export, and remove the intermediate source:

    mkdir -p .svtorture/drawio
    python3 /home/esynr3z/.pi/agent/npm/node_modules/pi-drawio/skills/drawio/scripts/check-drawio-layout.py .svtorture/drawio/<name>.drawio
    /home/esynr3z/.pi/agent/npm/node_modules/pi-drawio/skills/drawio/scripts/drawio-export.sh .svtorture/drawio/<name>.drawio png docs/about/assets/<name>.drawio.png
    rm .svtorture/drawio/<name>.drawio

After each export, call the `read` tool on the PNG and revise if any visual-quality check fails.

Run focused and complete frontend checks:

    npm --prefix dashboard test -- AboutView.test.tsx App.test.tsx
    npm --prefix dashboard run typecheck
    npm --prefix dashboard test
    npm --prefix dashboard run build

Run the repository interfaces before handoff:

    just smoke
    just ci

A successful frontend build should emit five hashed PNG assets under `dashboard/dist/assets/`. A local dashboard should show **About** as the final tab, section links should navigate to visible headings, desktop layout should retain the left rail while scrolling, and narrow layout should stack without horizontal overflow.

### Validation and Acceptance

Acceptance requires all of the following observable behavior, not merely passing compilation:

- **About** is the final dashboard tab and opens a data-independent guide.
- A visible table of contents links to Overview, Requirements, Cases, Tools, Campaigns, and Dashboard sections.
- The page reads as vertically stacked visual slides: concise copy, generous separation, and five meaningful illustrations rather than walls of text.
- The overview accurately shows standard -> annotation -> anchors/requirements -> cases plus tools -> runner -> campaign -> dashboard.
- Requirements explain falsifiability, anchor traceability, relationship links, coverage, density, and 2023-to-2012/2017 applicability without inventing formulas.
- Cases explain one-or-more requirement provenance, source/oracle materialization, accepted/simulated/elaborated and expected-rejection behavior, applicability, and their role in dashboard pass-rate evidence.
- Tools explain nested phases, deepest-phase profiles, phase/version applicability, open-source container integration, commercial local runners, and local versus public visibility accurately.
- Campaigns explain resolved identities, versions/hashes, stage outputs, diagnostics, normalized results, and reproduction evidence.
- Dashboard explains pass-rate/evidence browsing, requirements/case/source inspection, periodic mainline evidence, trends, compact reproducers, and bug-report assistance without promising a fixed schedule.
- Every diagram exists as an editable PNG with embedded Draw.io data, passes layout/XML checks, and has been visually inspected through `read`.
- Desktop and narrow layouts are usable and accessible, with no clipping or horizontal overflow.
- No new npm or Python dependency is introduced.
- Frontend tests, typecheck, build, `just smoke`, and `just ci` pass. Final evidence is 72 dashboard, 163 non-Docker Python, and 11 Docker tests.

### Idempotence and Recovery

Tests, builds, exports, and Draw.io validation are repeatable. Diagram XML is generated only in `/tmp`; failed exports leave tracked PNG files untouched until a successful replacement. `dashboard/dist/` remains ignored build output. If a diagram export is visually poor, regenerate the same filename so imports and links remain stable. If an imported documentation asset is not accepted by Vite, keep the canonical PNG in `docs/about/assets/` and use the smallest build-time copy mechanism already available in Vite rather than adding a dependency.

### Artifacts and Notes

Expected final tracked additions are:

    docs/about/README.md
    docs/about/assets/standards-to-evidence.drawio.png
    docs/about/assets/traceable-requirements.drawio.png
    docs/about/assets/executable-cases.drawio.png
    docs/about/assets/tool-applicability.drawio.png
    docs/about/assets/campaign-to-dashboard.drawio.png
    dashboard/src/AboutView.tsx
    dashboard/src/AboutView.test.tsx
    docs/exec-plans/about-dashboard.md

Expected modified files are `dashboard/src/App.tsx`, `dashboard/src/App.test.tsx`, and `dashboard/src/styles.css`. Additional small documentation navigation edits are permitted only if repository discovery shows an existing index that should link the standalone guide.

Completion-audit evidence:

    artifact-audit: 5 editable PNGs, no blind XML source, diff clean
    content-audit: six sections, shared assets, final URL tab, complete anchors
    Test Files  12 passed (12)
    Tests       72 passed (72)
    163 passed, 11 deselected
    11 passed, 163 deselected

The audit maps the brief's overview, requirements, cases, tools, campaigns, and dashboard topics to matching `h2` sections in both `docs/about/README.md` and `dashboard/src/AboutView.tsx`. It checks that About follows Campaigns in the tab list, direct fragment links survive, the two example anchor IDs exist in the committed anchor index, every documentation image is imported by the UI, all five PNGs contain an embedded `mxGraphModel`, and no intermediate `.drawio` file remains.

### Interfaces and Dependencies

Define `AboutView` in `dashboard/src/AboutView.tsx` with no props:

    export function AboutView() { ... }

The component must remain pure and data-independent. It may import static PNG modules and use React only. Do not add a Markdown package, router, icon package, scroll observer, or design-system abstraction. In `dashboard/src/App.tsx`, extend the existing view discriminator with `"about"` and render `<AboutView />` for that selection. Preserve all existing dataset-backed behavior for other views.

Revision note (2026-07-30): Created the initial self-contained plan after reading the user task, repository guidance, dashboard dependency boundary, and Draw.io workflow. The plan chooses a compact no-dependency React view backed by standalone documentation and visually inspected editable PNG exports.

Revision note (2026-07-30): Recorded implementation, TDD, all five vision-reviewed diagram exports, responsive browser evidence, complete CI, and review-driven fixes for data independence, anchor/oracle accuracy, replay qualification, diagram legibility, descriptions, contrast, and keyboard panning.

Revision note (2026-07-30): Corrected the final validation counts and review status after the independent control pass, and updated the Draw.io export procedure for Snap confinement before the completion audit.

Revision note (2026-07-30): Marked the plan complete after the prompt-to-artifact audit, Conventional Commit, and commit verification.

Revision note (2026-07-30): During the final post-commit requirement map, strengthened the open-source flow wording to state that moving upstream references are resolved to immutable revisions before Docker builds; re-ran all 72 frontend tests, typecheck, and production build before amending the commit.
