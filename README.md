# SVTORTURE

SVTORTURE is a standards-driven SystemVerilog conformance framework for EDA
tools. It connects each small, tool-neutral test case to a specific IEEE 1800
requirement, runs the case, and evaluates the observation with a shared oracle.

The main data flow is:

```text
IEEE 1800 requirements
        ↓
SystemVerilog cases
        ↓
tool adapters and controlled Docker execution
        ↓
raw observations and generic conformance judgments
        ↓
reproducible campaigns
        ↓
static evidence dashboard
```

The public dashboard is available at <https://kleverhq.github.io/svtorture>.

## How does SVTORTURE differ from sv-tests?

SVTORTURE was inspired by
[CHIPS Alliance sv-tests](https://github.com/chipsalliance/sv-tests), which runs
one SystemVerilog test collection across many tools. `sv-tests` reports broad
compatibility data in several test modes. SVTORTURE organizes coverage and
scoring around normative requirements. Each case links a requirement to a
phase-specific oracle, and each result records the observation and reproducible
conformance judgment.

Coverage and scoring use IEEE requirements instead of feature tags. Each oracle
names one target phase, while tool capabilities follow the cumulative
preprocess → parse → elaborate → simulate pipeline. The evaluator distinguishes
direct evidence from evidence collected by a later command. An unrelated
later-phase failure cannot satisfy an earlier negative oracle, and negative
cases need a diagnostic tied to the intended construct. Tool behavior does not
set the expected result.

Campaigns retain tool revisions, container identities, portable commands,
bounded output excerpts, and full-stream hashes. Full logs stay in local or CI
artifacts. A known failure remains a failure; the framework does not turn it into
an expected pass.

SVTORTURE is not a fork or drop-in replacement for `sv-tests`. Its corpus is
narrower and records more evidence for each covered requirement.

## Requirements

Development and campaign runs require:

- a POSIX-style environment with Bash and Git;
- Python 3.12 or newer;
- [uv](https://docs.astral.sh/uv/);
- Node.js 24 with npm, matching CI;
- [Just](https://just.systems/) 1.21 or newer;
- a Docker daemon capable of running `linux/amd64` containers, either natively
  or through emulation;
- network access for dependency installation and upstream source resolution.

Native Windows users need WSL or an equivalent POSIX environment.

Public compiler and simulator binaries do not need to be installed on the host.
SVTORTURE resolves their source revisions and runs project-controlled Docker
images. Building a current upstream tool for the first time can take several
minutes. Commercial tools require a separately installed licensed environment
and an ignored per-tool local runner configuration.

An IEEE 1800-2023 PDF and Poppler are optional. They are needed only when
maintaining requirement annotations; ordinary validation, campaigns,
reproduction, and dashboard use do not require the PDF.

## Quick start

From the repository root, install the locked Python and frontend dependencies:

```bash
just setup
```

Run the fast deterministic checks:

```bash
just smoke
```

Resolve the current upstream Verilator revision, build its Docker image, and run
it against the entire current corpus:

```bash
just latest verilator
```

For a shorter first run, select the smoke suite instead:

```bash
just latest verilator smoke
```

The command prints the generated campaign path, for example:

```text
campaign: .svtorture/campaigns/<campaign-id>/campaign.json
summary: conforming=… nonconforming=…
```

Build a local dashboard dataset from the printed path:

```bash
just dashboard-build ".svtorture/campaigns/<campaign-id>/campaign.json"
```

Serve the static dashboard:

```bash
just dashboard-serve
```

Open <http://localhost:4173>. The dashboard provides requirement and case
evidence browsers, campaign provenance, and trend views. Generated
campaigns and dashboard data remain under ignored local directories.

The recommended baseline runs all current public upstream tools in one campaign:

```bash
just public
```

Licensed tools use ignored per-tool local runner configuration. Create the VCS
configuration once, edit its command, verify readiness, and run commercial tools:

```bash
just runner-config vcs
$EDITOR tools/vcs/runner.toml
uv run svtorture doctor
just commercial
```

To run every public and locally configured commercial tool in one campaign, use:

```bash
just all
```

Campaign execution uses one global pool of all tool/profile/case combinations
and, by default, as many workers as CPUs available to the process. Limit the
pool when memory or commercial license seats are more restrictive than CPUs:

```bash
just all all 8
just commercial all 2
uv run svtorture run --tool icarus@latest --suite all --jobs 4
```

The Just signatures are `just all [suite] [jobs]` and
`just commercial [suite] [jobs]`; the first `all` in each example is the suite
argument. A job executes one case for one tool profile; dependent stages within
that job remain sequential. `--jobs 0`, including the Just recipe default,
selects the automatic CPU count.

## Documentation

- [Architecture and data flow](docs/architecture.md)
- [IEEE 1800-2023 annotation](docs/annotation.md)
- [Conformance methodology and metric](docs/methodology.md)
- [Adding a case](docs/adding-a-case.md)
- [Adding a tool](docs/adding-a-tool.md)
- [Campaign reproduction](docs/reproduction.md)
- [Dashboard design and local workflow](dashboard/README.md)

Maintainer rules and local constraints live in the nearest `AGENTS.md`.

## License

The project is licensed under [Apache-2.0](LICENSE).
