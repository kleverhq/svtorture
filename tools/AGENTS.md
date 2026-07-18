# Tool integration guidance

## Source of truth

- Registration, adapters, images, and wrapper policy: `../docs/adding-a-tool.md`
- Runtime boundaries: `../docs/architecture.md`
- Stable commands: root `justfile`

## Local guidance

- Keep public registry and diagnostic policy in this directory beside per-tool recipes.
- Keep each container recipe in its tool directory and update `tools.toml` recipe paths together with moves.
- Never commit `private.toml`, licensed images, credentials, or license endpoints.
