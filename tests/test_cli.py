from __future__ import annotations

import json
import re

from typer.testing import CliRunner

from svtorture.cli import app


def test_ci_matrix_is_selected_from_generic_public_policy() -> None:
    result = CliRunner().invoke(app, ["ci-matrix"])
    assert result.exit_code == 0, result.output
    matrix = json.loads(result.stdout)
    ids = {entry["tool"] for entry in matrix["include"]}
    assert ids == {"slang", "icarus", "verilator"}
    assert "fake" not in ids
    assert "vcs" not in ids


def test_run_help_exposes_execution_controls() -> None:
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
    assert "--verbose" in output
    assert "Stream Docker image" in output
    assert "preparation output." in output
    assert "--jobs" in output
    assert "-j" in output
    assert "concurrent" in output


def test_run_rejects_negative_jobs() -> None:
    result = CliRunner().invoke(app, ["run", "--tool", "fake@local", "--jobs", "-1"])
    assert result.exit_code == 2
    assert "not in the range x>=0" in result.output
