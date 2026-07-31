# Workflow scripts

These Python entrypoints bridge `just` recipes and GitHub workflows to the typed
library in `src/`. Their module headers identify the caller, purpose, and output.

- `aggregate_artifacts.py` combines available matrix campaign artifacts and
  records expected tools that did not produce evidence.
- `publish_dashboard.py` creates or verifies immutable campaign Releases,
  rebuilds trends from Release summaries, and writes the latest-only Pages tree.

Neither script owns product policy: the root `justfile` is the stable invocation
surface, while typed validation and publication invariants live under
`src/svtorture/`.
