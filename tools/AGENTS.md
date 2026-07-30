# Tool integration guidance

## Source of truth

- Registration, adapters, images, and runner policy: `../docs/adding-a-tool.md`
- Runtime boundaries: `../docs/architecture.md`
- Stable commands: root `justfile`

## Local guidance

- Keep `tools.toml` as an explicit index; portable metadata and diagnostic policy belong in each tool's `tool.toml`.
- Resolve recipe and runner paths relative to the owning `tool.toml`.
- Never commit `runner.toml`, licensed images, credentials, or license endpoints.
