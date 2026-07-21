# Copied-text scanning utility

`scan_copied_text.py` is a maintainer-only source hygiene gate. Given a separately stored reviewed corpus, it detects long normalized token sequences from that corpus in repository source files.

```bash
python3 utils/scan_copied_text/scan_copied_text.py \
  /path/to/reviewed-baseline
```

The baseline root must contain `txt/`. By default the utility scans text files returned by `git ls-files`, normalizes case and punctuation, and reports matching sequences of eight tokens. Use `--words N` to change the threshold or provide explicit candidate paths after the baseline argument.

The scan is deliberately conservative and heuristic: it does not inspect binary files or Git history, cannot detect paraphrases, and may miss copied fragments shorter than the threshold. It is not needed to generate or verify a corpus.

Run its authored tests with:

```bash
python3 -m unittest discover \
  -s utils/scan_copied_text \
  -p 'test_*.py' -v
```
