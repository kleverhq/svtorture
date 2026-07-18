# Python source guidance

## Source of truth

- Component boundaries and data flow: `../docs/architecture.md`
- Judgment and metric behavior: `../docs/methodology.md`
- Public contracts: `../schemas/`

## Local guidance

- Keep strict public models frozen and rejecting unknown fields.
- Adapters construct execution plans and normalize diagnostics; only the evaluator decides conformance.
- Update schemas, fixtures, tests, and relevant docs with public model changes.
