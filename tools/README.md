# Tools

This directory is the complete integration surface for compilers and simulators.
`tools.toml` is a thin index of child `tool.toml` manifests. Each tool directory
owns its metadata, reviewed diagnostic fallbacks, recipes, and documentation.
Commercial integrations also provide `runner.example.toml`; the sibling
`runner.toml` is machine-local and ignored by Git.
