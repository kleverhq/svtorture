# Contributing

Use the root `justfile`; it is the same interface used by hooks and CI.

```text
just setup
just smoke
just ci
```

Do not weaken an oracle to match current tool behavior. A compiler diagnostic,
another simulator, public feature matrix, or existing green result can
corroborate and prioritize a test, but it cannot define the expected standard
behavior.

Corpus changes follow [docs/adding-a-case.md](docs/adding-a-case.md). Adapter and
tool-registry changes follow [docs/adding-a-tool.md](docs/adding-a-tool.md).
Generated schemas and dashboard fixtures are refreshed with `just schemas` and
`just fixture`.

Keep commits free of `.svtorture/`, full logs, binaries, generated simulator
output, licensed images, private wrapper configuration, credentials, and IEEE
documents. Never add an expected-failure shortcut for a known defect.
