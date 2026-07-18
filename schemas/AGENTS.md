# Schema guidance

## Source of truth

- Schema generation: `../src/svtorture/catalog.py`
- Strict models: `../src/svtorture/models.py`
- Commands: `just schemas` and `just metadata`

## Local guidance

- These JSON files are generated snapshots; do not edit them manually.
- Regenerate and validate schemas in the same change as a public metadata contract.
