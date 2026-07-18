# Test guidance

## Source of truth

- Quality gates: root `justfile`
- Product behavior: `../docs/methodology.md` and `../docs/architecture.md`

## Local guidance

- Keep default unit tests deterministic and independent of Docker and the network.
- Mark Docker integration tests explicitly and preserve failure ownership between tool results and harness errors.
- Test strict rejection paths whenever metadata or public schemas change.
