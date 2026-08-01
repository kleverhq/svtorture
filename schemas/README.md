# JSON Schemas

These generated snapshots make the public campaign, case, requirement, suite,
tag, result, and tool contracts inspectable outside Python. In particular,
`tools.schema.json` describes the thin `tools/tools.toml` index and
`tool.schema.json` describes each per-tool `tool.toml`. The `dashboard-index`,
`campaign-summary`, `campaign-trends`, `campaign-manifest`, `campaign-catalog`,
`campaign-verdicts`, and `campaign-evidence` snapshots define the schema-v6
portable dashboard and Release resources. Regenerate all snapshots with `just
schemas`.
