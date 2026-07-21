# IEEE 1800-2023 annotator

This directory contains the repository-owned annotator that materializes a
citation-friendly IEEE 1800-2023 text corpus and anchor index from a
user-supplied PDF. It intentionally contains neither the PDF nor generated
standard text.

Use the root `justfile` rather than invoking these files directly:

```text
just annotator-tests
just annotate
just annotate-check
just annotate-update-anchors
just annotate-verify
```

`annotate.py` and `verify.py` implement the pipeline, `data/` contains structural
recipes and object inventories, and `utils/` contains optional maintainer tools.
See `../../docs/annotation.md` for prerequisites, configuration, generated
artifacts, verification policy, CI behavior, and maintenance guidance.
