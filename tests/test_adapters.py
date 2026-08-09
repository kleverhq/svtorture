from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from svtorture.adapters.base import ToolAdapter, UnsupportedCapability
from svtorture.adapters.commercial import VcsAdapter
from svtorture.adapters.open_source import IcarusAdapter, SlangAdapter, VerilatorAdapter
from svtorture.campaign import validate_plan_for_profile
from svtorture.catalog import Catalog, LoadedCase
from svtorture.models import (
    ExecutionPlan,
    ExecutionStage,
    ForeignInterface,
    Phase,
    StageKind,
    WorkFile,
)


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


@pytest.mark.parametrize(
    ("tool_id", "profile_id", "adapter_type"),
    (
        ("icarus", "simulator", IcarusAdapter),
        ("verilator", "simulator", VerilatorAdapter),
        ("vcs", "simulator", VcsAdapter),
    ),
)
def test_integrated_compile_attempts_parse_case_through_elaboration(
    catalog: Catalog,
    tool_id: str,
    profile_id: str,
    adapter_type: type[ToolAdapter],
) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = catalog.tools.tool(tool_id)
    plan = adapter_type().build_plan(
        case,
        tool,
        tool.profile(profile_id),
        image=("image" if tool_id != "vcs" else None),
        wrapper=("/private/wrapper" if tool_id == "vcs" else None),
    )
    assert plan.target_phase is Phase.PARSE
    assert plan.stages[0].attempted_through_phase is Phase.ELABORATE


@pytest.mark.parametrize(
    ("tool_id", "adapter_type", "preprocessor_flag"),
    (
        ("icarus", IcarusAdapter, "-E"),
        ("verilator", VerilatorAdapter, "-E"),
    ),
)
def test_open_source_preprocessing_is_direct(
    catalog: Catalog,
    tool_id: str,
    adapter_type: type[ToolAdapter],
    preprocessor_flag: str,
) -> None:
    original = catalog.cases["ch22-include-trailing-comment"]
    case = replace(
        original,
        definition=original.definition.model_copy(update={"target_phase": Phase.PREPROCESS}),
    )
    tool = catalog.tools.tool(tool_id)
    plan = adapter_type().build_plan(
        case,
        tool,
        tool.profile("elaborator"),
        image="image",
        wrapper=None,
    )
    assert plan.target_phase is Phase.PREPROCESS
    assert plan.stages[0].attempted_through_phase is Phase.PREPROCESS
    assert preprocessor_flag in plan.stages[0].argv


def test_plan_identity_must_match_requested_case_and_profile(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = catalog.tools.tool("icarus")
    profile = tool.profile("simulator")
    plan = (
        IcarusAdapter()
        .build_plan(
            case,
            tool,
            profile,
            image="image",
            wrapper=None,
        )
        .model_copy(update={"case_id": "different-case"})
    )
    with pytest.raises(ValueError, match="identity"):
        validate_plan_for_profile(
            plan,
            case,
            tool,
            profile,
            image="image",
            wrapper=None,
        )


def test_plan_backend_identity_must_match_prepared_tool(catalog: Catalog) -> None:
    case = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = catalog.tools.tool("icarus")
    profile = tool.profile("simulator")
    plan = IcarusAdapter().build_plan(
        case,
        tool,
        profile,
        image="unexpected-image",
        wrapper=None,
    )
    with pytest.raises(ValueError, match="backend identity"):
        validate_plan_for_profile(
            plan,
            case,
            tool,
            profile,
            image="recorded-image",
            wrapper=None,
        )


def test_stage_kind_cannot_claim_an_incoherent_phase(catalog: Catalog) -> None:
    case = catalog.cases["ch04-nba-rhs-captured"]
    with pytest.raises(ValueError, match="build stages cannot claim simulation"):
        ExecutionStage(
            id="compile",
            kind=StageKind.COMPILE,
            attempted_through_phase=Phase.SIMULATE,
            argv=("tool",),
            portable_argv=("tool",),
            timeout_seconds=case.definition.limits.timeout_seconds,
            output_bytes=case.definition.limits.output_bytes,
        )


def test_include_define_inputs_reach_adapter(catalog: Catalog) -> None:
    case = catalog.cases["ch22-include-trailing-comment"]
    tool = catalog.tools.tool("icarus")
    plan = IcarusAdapter().build_plan(
        case,
        tool,
        tool.profile("elaborator"),
        image="image",
        wrapper=None,
    )
    argv = plan.stages[0].argv
    assert "-I/case/include" in argv
    assert "-DSVTORTURE_EXTERNAL_BIAS=1" in argv


@pytest.mark.parametrize(
    ("tool_id", "adapter_type", "case_id"),
    (
        ("slang", SlangAdapter, "ch26-multifile-package-import"),
        ("icarus", IcarusAdapter, "ch03-unit-prior-type-across-files"),
        ("verilator", VerilatorAdapter, "ch03-unit-prior-type-across-files"),
        ("vcs", VcsAdapter, "ch03-unit-prior-type-across-files"),
    ),
)
def test_ordered_sources_reach_every_adapter(
    catalog: Catalog,
    tool_id: str,
    adapter_type: type[ToolAdapter],
    case_id: str,
) -> None:
    case = catalog.cases[case_id]
    tool = catalog.tools.tool(tool_id)
    plan = adapter_type().build_plan(
        case,
        tool,
        tool.profile("simulator" if tool_id != "slang" else "elaborator"),
        image=("image" if tool_id != "vcs" else None),
        wrapper=("/private/wrapper" if tool_id == "vcs" else None),
    )
    expected = [f"/case/{source}" for source in case.definition.sources]
    portable = [f"$CASE/{source}" for source in case.definition.sources]
    assert [argument for argument in plan.stages[0].argv if argument.endswith(".sv")] == expected
    assert [
        argument for argument in plan.stages[0].portable_argv if argument.endswith(".sv")
    ] == portable


def test_adapters_own_advanced_case_mechanics(catalog: Catalog) -> None:
    sdf = catalog.cases["ch32-iopath-rise-annotates-path"]
    icarus = catalog.tools.tool("icarus")
    sdf_plan = IcarusAdapter().build_plan(
        sdf,
        icarus,
        icarus.profile("simulator"),
        image="image",
        wrapper=None,
    )
    assert "-gspecify" in sdf_plan.stages[0].argv
    with pytest.raises(UnsupportedCapability, match="SDF"):
        VerilatorAdapter().check_case(sdf)

    covergroup = catalog.cases["ch19-clocking-event-automatic-sample"]
    verilator = catalog.tools.tool("verilator")
    coverage_plan = VerilatorAdapter().build_plan(
        covergroup,
        verilator,
        verilator.profile("simulator"),
        image="image",
        wrapper=None,
    )
    assert "--coverage-user" in coverage_plan.stages[0].argv
    with pytest.raises(UnsupportedCapability, match="covergroups"):
        IcarusAdapter().check_case(covergroup)


def test_library_map_plans_are_adapter_owned(catalog: Catalog) -> None:
    case = catalog.cases["ch33-basic-config-selects-design"]
    verilator = catalog.tools.tool("verilator")
    verilator_plan = VerilatorAdapter().build_plan(
        case,
        verilator,
        verilator.profile("simulator"),
        image="image",
        wrapper=None,
    )
    assert "--libmap" in verilator_plan.stages[0].argv
    assert "/case/lib.map" in verilator_plan.stages[0].argv

    vcs = catalog.tools.tool("vcs")
    vcs_plan = VcsAdapter().build_plan(
        case,
        vcs,
        vcs.profile("simulator"),
        image=None,
        wrapper="/private/wrapper",
    )
    assert [stage.id for stage in vcs_plan.stages] == [
        "compile-work",
        "compile-libb",
        "compile-liba",
        "elaborate",
        "run",
    ]
    assert {item.path for item in vcs_plan.work_files} == {
        "libraries/work/.keep",
        "libraries/liba/.keep",
        "libraries/libb/.keep",
        "synopsys_sim.setup",
    }
    validate_plan_for_profile(
        vcs_plan,
        case,
        vcs,
        vcs.profile("simulator"),
        image=None,
        wrapper="/private/wrapper",
    )


@pytest.mark.parametrize(
    ("tool_id", "adapter", "image", "wrapper", "expected"),
    (
        (
            "verilator",
            VerilatorAdapter(),
            "image",
            None,
            (StageKind.COMPILE, StageKind.FOREIGN_BUILD, StageKind.RUN),
        ),
        (
            "vcs",
            VcsAdapter(),
            None,
            "/private/wrapper",
            (StageKind.COMPILE, StageKind.FOREIGN_BUILD, StageKind.RUN),
        ),
    ),
)
@pytest.mark.parametrize(
    "case_id",
    ("ch35-c-source-import", "ch35-open-unpacked-array-runtime"),
)
def test_dpi_plans_separate_foreign_builds(
    catalog: Catalog,
    tool_id: str,
    adapter: ToolAdapter,
    image: str | None,
    wrapper: str | None,
    expected: tuple[StageKind, ...],
    case_id: str,
) -> None:
    case = catalog.cases[case_id]
    tool = catalog.tools.tool(tool_id)
    profile = tool.profile("simulator")
    plan = adapter.build_plan(
        case,
        tool,
        profile,
        image=image,
        wrapper=wrapper,
    )
    assert tuple(stage.kind for stage in plan.stages) == expected
    validate_plan_for_profile(
        plan,
        case,
        tool,
        profile,
        image=image,
        wrapper=wrapper,
    )
    if tool_id == "verilator":
        assert "--exe" in plan.stages[0].argv
    else:
        assert "\tvcs " in plan.work_files[0].content
        assert plan.stages[1].expected_artifact == "simv"

    with pytest.raises(UnsupportedCapability, match="DPI"):
        IcarusAdapter().check_case(case)


def test_vcs_compiles_mixed_foreign_sources_with_their_languages(catalog: Catalog) -> None:
    original = catalog.cases["ch35-c-source-import"]
    case = replace(
        original,
        definition=original.definition.model_copy(update={"resources": ("native.c", "native.cpp")}),
    )
    tool = catalog.tools.tool("vcs")
    plan = VcsAdapter().build_plan(
        case,
        tool,
        tool.profile("simulator"),
        image=None,
        wrapper="/private/wrapper",
    )
    makefile = plan.work_files[0].content
    assert "\t$(CXX) -shared -fPIC" in makefile
    assert "-x c native.c" in makefile
    assert "-x c++ native.cpp" in makefile
    assert ".o" not in makefile


def test_plan_validation_requires_foreign_stage_to_match_case(catalog: Catalog) -> None:
    tool = catalog.tools.tool("verilator")
    profile = tool.profile("simulator")
    foreign_case = catalog.cases["ch35-c-source-import"]
    foreign_plan = VerilatorAdapter().build_plan(
        foreign_case,
        tool,
        profile,
        image="image",
        wrapper=None,
    )
    legacy_value = foreign_plan.model_dump(mode="json")
    legacy_value["schema_version"] = 2
    with pytest.raises(ValidationError, match="execution schema version 3"):
        ExecutionPlan.model_validate(legacy_value)

    without_build = foreign_plan.model_copy(
        update={"stages": (foreign_plan.stages[0], foreign_plan.stages[-1])}
    )
    with pytest.raises(ValueError, match="does not match the case contract"):
        validate_plan_for_profile(
            without_build,
            foreign_case,
            tool,
            profile,
            image="image",
            wrapper=None,
        )

    ordinary_case = catalog.cases["ch04-nba-rhs-captured"]
    ordinary_plan = VerilatorAdapter().build_plan(
        ordinary_case,
        tool,
        profile,
        image="image",
        wrapper=None,
    )
    with_build = ordinary_plan.model_copy(
        update={
            "stages": (
                ordinary_plan.stages[0],
                foreign_plan.stages[1],
                ordinary_plan.stages[-1],
            )
        }
    )
    with pytest.raises(ValueError, match="does not match the case contract"):
        validate_plan_for_profile(
            with_build,
            ordinary_case,
            tool,
            profile,
            image="image",
            wrapper=None,
        )


def test_vcs_rejects_vpi_until_startup_mechanics_exist(catalog: Catalog) -> None:
    original = catalog.cases["ch35-c-source-import"]
    case = replace(
        original,
        definition=original.definition.model_copy(update={"foreign": ForeignInterface.VPI}),
    )
    with pytest.raises(UnsupportedCapability, match="VPI"):
        VcsAdapter().check_case(case)
    with pytest.raises(UnsupportedCapability, match="VPI"):
        IcarusAdapter().check_case(case)


def test_plan_validation_rejects_materialized_path_collisions(catalog: Catalog) -> None:
    case = catalog.cases["ch32-iopath-rise-annotates-path"]
    tool = catalog.tools.tool("icarus")
    profile = tool.profile("simulator")
    plan = IcarusAdapter().build_plan(case, tool, profile, image="image", wrapper=None)
    plan = plan.model_copy(update={"work_files": (WorkFile(path="test.sdf", content="x"),)})

    with pytest.raises(ValueError, match="work paths collide"):
        validate_plan_for_profile(plan, case, tool, profile, image="image", wrapper=None)


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


def test_locationless_adapter_rule_is_owned_by_tool(catalog: Catalog) -> None:
    from svtorture.adapters.registry import adapter_for

    case: LoadedCase = catalog.cases["ch05-base-format-whitespace-rejected"]
    tool = catalog.tools.tool("vcs")
    adapter = adapter_for("vcs", diagnostic_rules=tool.diagnostic_rules)
    diagnostics, _ = adapter.normalize_diagnostics(
        "",
        "Error-[SE] syntax error while reading based number",
        case,
    )
    assert diagnostics
    assert diagnostics[0].source is None
    assert diagnostics[0].target_case_id == case.definition.id
