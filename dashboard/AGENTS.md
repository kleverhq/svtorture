# Dashboard guidance

## Source of truth

- Dataset construction and publication policy: `../src/svtorture/publish.py`
- Conformance terminology: `../docs/methodology.md`
- Frontend commands: root `justfile`

## Local guidance

- The default build reads the canonical example dataset from `../fixtures/dashboard/data/dataset.json`.
- Real campaign exports belong only in ignored `dist/data/`.
- Keep filters URL-backed and present absent or incomplete evidence explicitly.
