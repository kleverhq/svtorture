# Synopsys VCS

VCS demonstrates the generic commercial-tool path. `tool.toml` owns its
profiles and reviewed diagnostic fallbacks. VCS has no public image recipe;
copy `runner.example.toml` to `runner.toml` and place any local runner scripts
in this directory. The directory's `.gitignore` keeps both the configuration and
scripts local while preserving the README, example, and manifest. Configure a
command implementing the wrapper protocol described in
[`docs/adding-a-tool.md`](../../docs/adding-a-tool.md).
