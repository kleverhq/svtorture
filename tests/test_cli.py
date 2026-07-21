from __future__ import annotations

import json

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


def test_run_help_exposes_verbose_image_output() -> None:
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    assert "--verbose" in result.stdout
    assert "Stream Docker image" in result.stdout
    assert "preparation output." in result.stdout
