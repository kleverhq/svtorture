# Standards catalog guidance

## Source of truth

- Runtime anchor index: `ieee-1800-2023-anchors.json`
- Requirement annotator source: `ieee-1800-2023-annotate/`
- Annotation workflow and policy: `../docs/annotation.md`
- Requirement semantics and scoring: `../docs/methodology.md`
- Case integration workflow: `../docs/adding-a-case.md`
- Generated contracts: `../schemas/`

## Local guidance

- Normal validation and execution must not require the PDF, Poppler, or generated annotated text.
- When adding or revising a requirement, run `just annotate` and derive it from the locally materialized corpus, not another website or paraphrase.
- Cite complete anchors present in the committed runtime index; put the declared clause's main anchor first and add supporting anchors only when the rule spans blocks.
- Inspect the corresponding PDF page when cited text has a visual-review marker.
- Use `just annotate-update-anchors` only for an intentional index change, and commit the updated runtime index.
- This inventory contains only normative requirements that are testable in principle.
- Keep chapter files aligned with `index.toml`, requirements sorted by ID, and tag IDs registered in `tags.toml`.
- Store concise project-owned summaries; never commit the IEEE PDF or generated standard text.
