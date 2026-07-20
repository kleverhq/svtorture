# Standards catalog guidance

## Source of truth

- Pinned 1800-2023 text and anchor index: `ieee-1800-2023-annotated/`
- Requirement semantics and scoring: `../docs/methodology.md`
- Case integration workflow: `../docs/adding-a-case.md`
- Generated contracts: `../schemas/`

## Local guidance

- Derive every 1800-2023 requirement and oracle from the pinned annotated corpus, not another PDF, website, or paraphrase.
- Cite complete anchors present in `ieee-1800-2023-annotated/anchors.json`; put the declared clause's main anchor first and add supporting anchors only when the rule spans blocks.
- Inspect the corresponding PDF page when cited text has a visual-review marker.
- This inventory contains only normative requirements that are testable in principle.
- Keep chapter files aligned with `index.toml`, requirements sorted by ID, and tag IDs registered in `tags.toml`.
- Store concise project-owned summaries; do not edit the submodule or copy IEEE text or documents elsewhere in this repository.
