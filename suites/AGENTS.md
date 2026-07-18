# Suite guidance

## Source of truth

- Selection loading and validation: `../src/svtorture/catalog.py`
- Campaign usage: root `justfile`

## Local guidance

- `cases` entries are glob patterns over stable case IDs.
- Keep patterns intentional: an unmatched pattern is invalid and overlapping matches are deduplicated in declaration order.
- Keep `all` as `["*"]`; reserve `smoke` for fast coverage of distinct execution and oracle paths.
