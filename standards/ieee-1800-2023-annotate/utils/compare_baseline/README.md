# Baseline comparison utility

`compare_baseline.py` is a maintainer-only regression gate. It compares a newly generated corpus with a separately stored reviewed corpus without requiring that baseline to be committed.

Both arguments must be corpus roots containing `txt/` and `anchors.json`:

```bash
python3 utils/compare_baseline/compare_baseline.py \
  /path/to/reviewed-baseline \
  generated
```

The utility requires the same TXT file inventory, the same anchor index apart from input-specific `source_sha256`, the same per-file metadata apart from `source`, `source_sha256`, and `status`, and the same anchor sequence. Each anchored block must then be byte-identical or carry one of the explicit annotation/glyph/vector review markers. An unmarked content difference fails the command.

This utility is not needed to generate or verify a corpus. It exists for maintainers who have access to a reviewed baseline and are changing annotation behavior.

Run its authored tests with:

```bash
python3 -m unittest discover \
  -s utils/compare_baseline \
  -p 'test_*.py' -v
```
