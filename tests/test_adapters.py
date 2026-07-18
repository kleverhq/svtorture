from __future__ import annotations

from pathlib import Path

import pytest

from svtorture.adapters.base import ToolAdapter
from svtorture.adapters.commercial import VcsAdapter
from svtorture.adapters.open_source import IcarusAdapter, SlangAdapter, VerilatorAdapter
from svtorture.catalog import Catalog, LoadedCase


@pytest.mark.parametrize(
    ("tool_id", "profile_id", "case_id", "adapter_type", "required"),
    (
        (
            "slang",
            "elaborator",
            "ch27-unselected-undefined-module",
            SlangAdapter,
            ("slang", "--std=1800-2023", "--single-unit", "--top=top"),
        ),
        (
            "icarus",
            "simulator",
            "ch04-nba-rhs-captured",
            IcarusAdapter,
            ("iverilog", "-g2012", "-s", "top"),
        ),
        (
            "verilator",
            "simulator",
            "ch04-nba-rhs-captured",
            VerilatorAdapter,
            ("verilator", "--language", "1800-2023", "--top-module", "top"),
        ),
        (
            "vcs",
            "simulator",
            "ch04-nba-rhs-captured",
            VcsAdapter,
            ("vcs", "-full64", "-sverilog", "-o"),
        ),
    ),
)
def test_real_adapter_command_construction(
    catalog: Catalog,
    tool_id: str,
    profile_id: str,
    case_id: str,
    adapter_type: type[ToolAdapter],
    required: tuple[str, ...],
) -> None:
    case = catalog.cases[case_id]
    tool = catalog.tools.tool(tool_id)
    profile = tool.profile(profile_id)
    adapter = adapter_type()
    plan = adapter.build_plan(
        case,
        tool,
        profile,
        image=("image@sha256:" + "0" * 64 if tool_id != "vcs" else None),
        wrapper=("/private/wrapper" if tool_id == "vcs" else None),
    )
    flattened = plan.stages[0].argv
    for argument in required:
        assert argument in flattened
    assert all(str(catalog.root) not in argument for argument in flattened)
    assert all(str(catalog.root) not in argument for argument in plan.stages[0].portable_argv)
    if tool_id == "icarus":
        assert "-g2012" in flattened
    if tool_id == "vcs":
        assert plan.wrapper == "/private/wrapper"


def test_include_define_and_ordered_sources_are_adapter_inputs(catalog: Catalog) -> None:
    include_case = catalog.cases["ch22-include-trailing-comment"]
    multi_case = catalog.cases["ch26-multifile-package-import"]
    tool = catalog.tools.tool("icarus")
    adapter = IcarusAdapter()
    include_plan = adapter.build_plan(
        include_case,
        tool,
        tool.profile("elaborator"),
        image="image",
        wrapper=None,
    )
    argv = include_plan.stages[0].argv
    assert "-I/case/include" in argv
    assert "-DSVTORTURE_EXTERNAL_BIAS=1" in argv
    multi_plan = adapter.build_plan(
        multi_case,
        tool,
        tool.profile("elaborator"),
        image="image",
        wrapper=None,
    )
    source_arguments = [
        argument for argument in multi_plan.stages[0].argv if argument.startswith("/case/")
    ]
    assert source_arguments[-2:] == ["/case/values_pkg.sv", "/case/top.sv"]


@pytest.mark.parametrize(
    ("adapter", "text"),
    (
        (SlangAdapter(), "{source}:{line}:3: error: invalid token"),
        (IcarusAdapter(), "{source}:{line}: error: invalid token"),
        (VerilatorAdapter(), "%Error: {source}:{line}:3: invalid token"),
        (VcsAdapter(), "{source}, {line}: error: invalid token"),
    ),
)
def test_real_adapter_diagnostic_normalization(
    catalog: Catalog,
    adapter: ToolAdapter,
    text: str,
) -> None:
    case = catalog.cases["ch23-mixed-port-style-rejected"]
    assert case.anchor_line is not None
    rendered = text.format(source="/case/top.sv", line=case.anchor_line)
    diagnostics, internal = adapter.normalize_diagnostics("", rendered, case)
    assert not internal
    assert diagnostics
    assert diagnostics[0].source == "$CASE/top.sv"
    assert diagnostics[0].target_case_id == case.definition.id


def test_same_line_in_a_different_source_is_not_target_evidence(
    catalog: Catalog,
) -> None:
    case = catalog.cases["ch23-mixed-port-style-rejected"]
    assert case.anchor_line is not None
    diagnostics, internal = VerilatorAdapter().normalize_diagnostics(
        "",
        f"%Error: /case/unrelated.sv:{case.anchor_line}:3: unrelated construct",
        case,
    )
    assert not internal
    assert diagnostics
    assert diagnostics[0].target_case_id is None


def test_verilator_user_assertion_report_is_not_a_compiler_internal_error(
    catalog: Catalog,
) -> None:
    case = catalog.cases["ch12-unique-if-no-match-diagnostic"]
    assert case.anchor_line is not None
    diagnostics, internal = VerilatorAdapter().normalize_diagnostics(
        (
            f"[0] %Error: top.sv:{case.anchor_line}: Assertion failed in top: "
            "'unique if' statement violated\n"
            f"%Error: /case/top.sv:{case.anchor_line}: Verilog $stop"
        ),
        "",
        case,
    )
    assert not internal
    assert diagnostics
    assert diagnostics[-1].target_case_id == case.definition.id


def test_locationless_adapter_rule_is_separate_from_case(catalog: Catalog, root: Path) -> None:
    from svtorture.adapters.registry import adapter_for

    case: LoadedCase = catalog.cases["ch05-base-format-whitespace-rejected"]
    adapter = adapter_for(
        "vcs",
        rules_path=root / "toolchains" / "diagnostic-rules.toml",
    )
    diagnostics, _ = adapter.normalize_diagnostics(
        "",
        "Error-[SE] syntax error while reading based number",
        case,
    )
    assert diagnostics
    assert diagnostics[0].source is None
    assert diagnostics[0].target_case_id == case.definition.id


@pytest.mark.parametrize(
    "contents",
    (
        "schema_version = true\nrules = []\n",
        (
            'schema_version = 1\n[[rules]]\ntool = "vcs"\n'
            'case = "ch05-base-format-whitespace-rejected"\ncontains = ""\n'
        ),
    ),
)
def test_diagnostic_fallback_metadata_is_strict(tmp_path: Path, contents: str) -> None:
    from svtorture.adapters.registry import AdapterError, load_fallbacks

    path = tmp_path / "rules.toml"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(AdapterError):
        load_fallbacks(path)
