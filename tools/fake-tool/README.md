# Deterministic fake tool

This image implements a stable test protocol used to exercise the real executor
and evaluator without depending on external compiler behavior. The adjacent
`tool.toml` registers `Dockerfile` and `fake_tool.py` as its image recipe.
