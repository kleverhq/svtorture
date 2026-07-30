# IEEE 1800-2023 annotation

The deterministic annotator is in
`standards/ieee-1800-2023-annotate/`. It converts a user-supplied IEEE 1800-2023
PDF into an ignored, searchable text corpus with stable citation anchors. The
licensed PDF and generated standard text are not committed.

The committed `standards/ieee-1800-2023-anchors.json` is the only annotation
artifact used by normal catalog validation, execution, replay, and publication.
Those workflows do not need the PDF, Poppler, or generated TXT files.

## Prerequisites

Annotation requires:

- Python 3.10 or newer;
- Poppler `pdftohtml`, provided by the `poppler-utils` system package;
- a locally available IEEE 1800-2023 PDF.

For Debian and Ubuntu:

```text
sudo apt-get install poppler-utils
```

For macOS with Homebrew:

```text
brew install poppler
```

The development reference is Poppler 24.02.0 and a PDF with SHA-256:

```text
203fbcccbbae90cef401a3acd31835c8cd1507e8f12b2e069046d4f316e317c9
```

The annotator warns when the PDF hash or Poppler version differs from the
reference. Run the complete verification before accepting output produced by a
different input or tool version.

## Local configuration

Copy `.env.local.example` to ignored `.env.local` and set a stable absolute PDF
path:

```text
IEEE_1800_2023_PDF=/absolute/path/to/IEEE-1800-2023.pdf
```

The root `justfile` loads `.env.local` automatically. Every annotation target
also accepts an explicit PDF argument, which takes precedence:

```text
just annotate /path/to/IEEE-1800-2023.pdf
```

Do not place the PDF anywhere in Git. The annotator directory ignores PDFs and
all generated output.

## Repository commands

Run source-only annotator and utility tests without a PDF:

```text
just annotator-tests
```

Materialize the complete ignored corpus without changing committed metadata:

```text
just annotate
```

Generate, structurally verify, and compare the generated anchor index with the
committed runtime index:

```text
just annotate-check
```

When an intentional annotator change modifies the index, update it explicitly:

```text
just annotate-update-anchors
git add standards/ieee-1800-2023-anchors.json
git commit
```

For deterministic regeneration, generate the corpus and then regenerate every
part a second time, requiring byte-for-byte stability:

```text
just annotate-verify
```

For complete local verification, run `just annotate-check` to compare the
committed index and `just annotate-verify` to regenerate the corpus twice.

Generated files live under
`standards/ieee-1800-2023-annotate/generated/` and can be deleted at any time.

## Generated corpus

Complete annotation produces:

- `generated/txt/01.txt` through `generated/txt/41.txt` for numbered clauses;
- `generated/txt/A.txt` through `generated/txt/Q.txt` for annexes;
- `generated/anchors.json` for the complete ordered anchor inventory.

Every TXT file records the input path, source SHA-256, physical and printed page
ranges, status, and anchor schema. The anchor index records the source SHA-256,
titles, stable relative TXT paths, per-part counts, and anchors in corpus order.
The index omits the machine-local PDF path, so identical PDFs produce
byte-identical indexes when read from different paths.

## Annotation model

`annotate.py` invokes `pdftohtml -xml -hidden -i` for each configured clause or
annex. It validates printed-page footers, preserves source coordinates and font
information, removes headers and footers, repairs overlapping fragments, and
classifies headings, prose, lists, notes, code, grammar, captions, tables, and
figure labels. Classified lines become anchored blocks keyed to printed pages.

`data/recipes.json` then restores expected anchor structure around layouts that
cannot be reconstructed safely and adds explicit visual-review markers. Recipe
validation permits only anchor values, structural boundaries, and marker names;
it rejects copied standard prose, code, grammar, formulas, and captions.

`data/objects.csv` inventories numbered tables, figures, and Syntax captions,
including their clause and page facts. It contains no copied captions.

## Anchors and visual review

Every generated block starts with a stable anchor:

```text
[2023:3.14.2.1:P001:p059]
```

The general form is:

```text
[2023:<clause-or-annex>:<fragment>:p<printed-page-or-range>]
```

Common fragment prefixes are `H` for headings, `P` for paragraphs, `L` for list
items, `C` for code, `G` for grammar, `T` for tables, `F` for figures, and `S`
for Syntax captions.

Linear PDF conversion cannot preserve every table, diagram, waveform, formula,
custom glyph, or significant layout. Affected blocks carry one of these markers:

```text
[TABLE_REQUIRES_VISUAL_REVIEW]
[FIGURE_REQUIRES_VISUAL_REVIEW]
[DIAGRAM_REQUIRES_VISUAL_REVIEW]
[WAVEFORM_REQUIRES_VISUAL_REVIEW]
[FORMALISM_REQUIRES_VISUAL_REVIEW]
[LAYOUT_REQUIRES_VISUAL_REVIEW]
[CODE_LAYOUT_REQUIRES_VISUAL_REVIEW]
[TEXT_ANNOTATION_REQUIRES_VISUAL_REVIEW]
```

Inspect the corresponding printed PDF page whenever a requirement or oracle
depends on a marked block.

## Verification policy

`verify.py` checks:

- the exact 58-file inventory;
- source metadata and configured page ranges;
- anchor grammar, order, page coverage, and global uniqueness;
- deterministic `anchors.json` generation;
- expected visual-review marker counts;
- table, figure, and Syntax inventories from `data/objects.csv`;
- grammar adjacency for Syntax captions;
- deterministic regeneration when `--check-generated` is requested.

The reference corpus contains 16,963 globally unique anchors, 146 tables, 103
figures, 212 Syntax captions, and 686 visual-review markers. Structural
verification checks consistency and reproducibility for the selected PDF. It
does not verify the semantics of layouts marked for visual review.

## CI verification

The `annotation-index` CI job runs only for trusted pushes to `main` in the
branch-restricted `ieee-1800-2023-annotation` GitHub environment. Pull requests
do not receive the licensed URL. Configure `IEEE_1800_2023_PDF_URL` as an
environment secret. If the secret is absent, the trusted job prints a warning
and exits successfully without installing Poppler or downloading the PDF.

With the secret available, CI uses commit-pinned setup actions and Just 1.21.0.
It installs `poppler-utils` and downloads the PDF into ignored `.svtorture/`.
Only the download step receives the URL. The separate `just annotate-check` step
receives the local PDF path and byte-compares the generated index with
`standards/ieee-1800-2023-anchors.json`. A mismatch fails the job and instructs
the maintainer to run `just annotate-update-anchors` and commit the result. CI
must not log the URL or PDF or upload either one as an artifact.

## Maintenance utilities

`utils/compare_baseline/compare_baseline.py` compares a newly generated corpus
with a separately stored reviewed corpus. It ignores only input-specific source
metadata; anchors and unmarked blocks must otherwise match. See its colocated
README for usage.

`utils/scan_copied_text/scan_copied_text.py` checks tracked files with supported
text suffixes for long, normalized token sequences that also appear in a
separately stored reviewed corpus. The scanner is a source-hygiene check, not
part of generation or runtime. See its colocated README for limitations.

When changing annotation behavior:

1. make the smallest general parser or classification correction;
2. materialize the affected corpus with the reference PDF;
3. inspect marked or layout-sensitive pages in the PDF;
4. update structural recipes only when automatic classification cannot safely
   preserve the anchor skeleton;
5. run `just annotator-tests`, `just annotate-check`, and `just annotate-verify`;
6. use `just annotate-update-anchors` only if the intended anchor inventory
   changed;
7. run the repository's normal `just smoke` and `just precommit` gates.
