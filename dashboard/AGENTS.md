# Dashboard guidance

## Source of truth

- Dataset construction and publication policy: `../src/svtorture/publish.py`
- Conformance terminology: `../docs/methodology.md`
- Frontend commands: root `justfile`

## Local guidance

- A plain frontend build contains no dataset; local and Pages workflows export campaign data after the build.
- Local campaign exports belong only in ignored `dist/data/`.
- Keep filters URL-backed and present absent or incomplete evidence explicitly.
