# sv-torture

SVTORTURE is a standards-driven SystemVerilog conformance framework. It maps a
concise IEEE 1800 requirement inventory to tool-neutral cases, executes exact
compiler snapshots in controlled containers, and preserves raw observations
separately from generic conformance judgments.

Its headline number is deliberately named **Verified support in the covered
corpus**. It is requirement-weighted evidence for a stated revision and
tool/profile scope—not a claim of unconditional SystemVerilog support and not a
vote among tools.

## What is included

- strict Pydantic/TOML models and committed JSON Schemas;
- 12 deterministic IEEE 1800-2023 cases across 11 chapters;
- parse, elaboration, simulation, positive, targeted-negative, and diagnostic
  oracle paths;
- Docker-only Slang, Icarus, and Verilator adapters;
- a generic private-wrapper route, with VCS as the initial optional example;
- immutable, hash-checked campaign records and exact replay;
- a React/TypeScript requirements matrix, evidence browser, history comparison,
  and campaign provenance view;
- fast pre-commit checks, PR CI, nightly upstream collection, GHCR images, and
  append-only `gh-pages` publication.

The conceptual pipeline is:

```text
Requirement → Case → Tool/profile adapter → Execution plan
            → Raw observations → Generic evaluation
            → Immutable campaign → Dashboard dataset
```

## Start here

Requirements are Python 3.12, `uv`, Node/npm, `just`, Git, and a working Docker
daemon on Linux x86-64.

```text
just setup
just smoke
just ci
```

`just smoke` is deterministic and avoids Docker/network work. `just ci` is the
full local PR-CI equivalent: locked installs, full-tree pre-commit, lint/type
checks, unit tests, strict metadata/schema checks, frontend tests/build, fake
Docker E2E, and a real Icarus upstream smoke campaign.

Common campaign commands:

```text
just latest slang
just latest icarus smoke
just latest-all
just pinned verilator v5.040 smoke
just commercial smoke
```

Every moving or named public ref resolves to one full upstream commit before an
image is built. `latest` follows the default branch declared in tool metadata,
not an ambient host checkout. Ordinary conformance differences do not make the default
campaign command fail; harness and infrastructure failures do.

Build and inspect a recorded campaign:

```text
just dashboard-build ".svtorture/campaigns/<campaign>/campaign.json"
just dashboard-serve
just reproduce ".svtorture/campaigns/<campaign>/campaign.json" icarus simulator ch04-nba-rhs-captured
```

Local campaigns and work products remain under the gitignored `.svtorture/`.

## Corpus and authority

IEEE Std 1800-2023 is the active authority. Every requirement and case declares
its applicability to 1800-2012, 1800-2017, and 1800-2023. Icarus runs explicitly
in `-g2012`; it receives a normal judgment only where the case says its source
and oracle apply unchanged to that revision.

The seed corpus covers chapters 4, 5, 6, 7, 11, 12, 13, 22, 23, 26, and 27.
Seven cases are independently rewritten adaptations or inspirations from the
reviewed reference corpus; five are original boundary cases. The exact reference
checkouts and what was reused are recorded in
[docs/reference-sources.md](docs/reference-sources.md).

No IEEE PDF or substantial standards text is included. Requirement records carry
precise clauses, project anchors, and concise original summaries.

## Documentation

- [Architecture and data flow](docs/architecture.md)
- [Conformance methodology and metric](docs/methodology.md)
- [Add a standards-grounded case](docs/adding-a-case.md)
- [Add an open-source or commercial tool](docs/adding-a-tool.md)
- [Campaign reproduction](docs/reproduction.md)
- [Reference checkout audit](docs/reference-sources.md)
- [Contributing](CONTRIBUTING.md)

## License

Framework code and original project material are licensed under
[Apache-2.0](LICENSE). Individual case provenance and upstream tool licenses are
recorded separately.
