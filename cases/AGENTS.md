# Case guidance

## Source of truth

- Case design and validation workflow: `../docs/adding-a-case.md`
- Conformance and oracle semantics: `../docs/methodology.md`
- Starter metadata and source: `../templates/case/`

## Local guidance

- Keep each directory name equal to its case ID and each case focused on one semantic boundary.
- Map one primary requirement and use only tags registered in `../standards/tags.toml`.
- Never weaken self-checks, diagnostic anchors, or expected behavior for a tool defect.
