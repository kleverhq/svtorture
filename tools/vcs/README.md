# Synopsys VCS

VCS demonstrates the generic commercial-tool path. `tool.toml` owns its
profiles and reviewed diagnostic fallbacks. VCS has no public image recipe;
copy `runner.example.toml` to the ignored `runner.toml` and configure a local
command implementing the wrapper protocol described in
[`docs/adding-a-tool.md`](../../docs/adding-a-tool.md).
