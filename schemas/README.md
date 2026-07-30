# JSON Schemas

These generated snapshots make the public campaign, case, requirement, suite,
tag, result, and tool contracts inspectable outside Python. In particular,
`tools.schema.json` describes the thin `tools/tools.toml` index and
`tool.schema.json` describes each per-tool `tool.toml`. Regenerate all snapshots
with `just schemas`.
