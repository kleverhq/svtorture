# Standards catalog guidance

## Source of truth

- Runtime anchor index: `ieee-1800-2023-anchors.json`
- Optional requirement-authoring corpus: `ieee-1800-2023-annotated/`
- Requirement semantics and scoring: `../docs/methodology.md`
- Case integration workflow: `../docs/adding-a-case.md`
- Generated contracts: `../schemas/`

## Local guidance

- Normal validation and execution must not require the annotated submodule.
- When adding or revising a requirement, derive it from the pinned annotated corpus, not another PDF, website, or paraphrase.
- Cite complete anchors present in the vendored index; put the declared clause's main anchor first and add supporting anchors only when the rule spans blocks.
- If the submodule is initialized, pre-commit requires its `anchors.json` to be byte-for-byte identical to the vendored index.
- Inspect the corresponding PDF page when cited text has a visual-review marker.
- This inventory contains only normative requirements that are testable in principle.
- Keep chapter files aligned with `index.toml`, requirements sorted by ID, and tag IDs registered in `tags.toml`.
- Store concise project-owned summaries; do not edit the submodule or copy IEEE text or documents elsewhere in this repository.
