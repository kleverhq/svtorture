# Repository Guidance

## Core workflow

- SVTORTURE is a standards-driven SystemVerilog conformance framework.
- Use the root `justfile` as the stable development and CI interface.
- Run `just smoke` for deterministic local checks and `just ci` before handoff when Docker and network access are available.
- Regenerate schemas with `just schemas`; do not edit generated JSON by hand.
- When adding or revising an 1800-2023 requirement, run the integrated annotator and ground the change in its locally materialized corpus and complete anchors.
- Do not weaken an oracle or add an expected-failure shortcut to match current tool behavior.
- Keep commits free of `.svtorture/`, full logs, binaries, simulator output, licensed images, local runner configuration, credentials, IEEE PDFs, and generated standard text.
- Use Conventional Commits for repository commits.
- Read the nearest applicable `AGENTS.md` before editing; local files add directory-specific guidance.

## Sources of truth

- Architecture and ownership boundaries: `docs/architecture.md`
- Conformance and scoring semantics: `docs/methodology.md`
- Case workflow: `docs/adding-a-case.md`
- Tool integration workflow: `docs/adding-a-tool.md`
- Replay behavior: `docs/reproduction.md`

## Map

- `standards/` — chapter-oriented requirement inventory and controlled tags.
- `cases/` — strict case metadata and minimal SystemVerilog sources.
- `suites/` — named glob selections over case IDs.
- `tools/` — tool manifest index, per-tool policies, container recipes, and runner examples.
- `src/` — Python implementation of catalog, execution, evaluation, and publication.
- `dashboard/` — React evidence browser.
- `schemas/` — generated public JSON Schema snapshots.
- `scripts/` — workflow-facing Python entrypoints.
- `tests/` — framework tests.
- `templates/` — starting points for new corpus material.
- `.github/` — CI, nightly, and Pages automation.
- `docs/` — durable architecture, methodology, and maintainer documentation.

## Writing

- Keep repository Markdown concise, neutral, and focused on current behavior.
- Use README files for navigation and purpose. Put behavioral rules in `AGENTS.md` and durable explanations in `docs/`.
- Avoid duplicating an authoritative document; link to it from local breadcrumbs.
