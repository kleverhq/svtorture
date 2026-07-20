# sv-torture

SVTORTURE maps concise IEEE 1800 requirements to tool-neutral SystemVerilog
cases, executes compiler snapshots through controlled tool integrations, and
turns raw observations into reproducible conformance evidence.

The main path through the repository is:

```text
standards → cases → suites → tools → campaigns → dashboard
```

Clone with `--recurse-submodules`, or initialize an existing checkout with
`git submodule update --init --recursive`. Access to the annotated repository is
required. GitHub Actions uses `ANNOTATED_STANDARD_TOKEN` when configured; for a
private submodule, set it to a fine-grained token with read access to both
repositories. Then run `just setup` and use `just smoke` for the fast local gate
or `just ci` for the complete integration gate. The root `justfile` lists
campaign, reproduction, schema, and dashboard entrypoints.

Documentation:

- [Architecture and data flow](docs/architecture.md)
- [Conformance methodology and metric](docs/methodology.md)
- [Adding a case](docs/adding-a-case.md)
- [Adding a tool](docs/adding-a-tool.md)
- [Campaign reproduction](docs/reproduction.md)

Each top-level directory has a short README explaining why it exists. Maintainer
rules and local constraints live in the nearest `AGENTS.md`. The project is
licensed under [Apache-2.0](LICENSE).
