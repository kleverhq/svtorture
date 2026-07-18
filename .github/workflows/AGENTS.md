# Workflow guidance

## Source of truth

- Stable task interface: `../../justfile`
- Architecture and publication policy: `../../docs/architecture.md`
- Workflow-facing helpers: `../../scripts/`

## Local guidance

- Reuse `just` recipes and tested scripts for substantive logic.
- Keep inline workflow shell limited to short orchestration.
- Preserve explicit missing-artifact and publication-failure reporting.
