"""Tests for HyperEdit Pro CLI interface."""

import json
from pathlib import Path
from click.testing import CliRunner

from hyperedit.cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "HyperEdit Pro" in result.output
    assert "doctor" in result.output
    assert "version" in result.output
    assert "validate" in result.output
    assert "new" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "HyperEdit Pro v0.1.0" in result.output


def test_cli_version_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["version", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["hyperedit"] == "0.1.0"
    assert data["schema_version"] == "2.0.0"


def test_cli_doctor_runs():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    # Exit code is 0 (or 2 with strict if warnings). Without strict it should exit 0
    assert result.exit_code == 0
    assert "HyperEdit Pro System & Environment Diagnostics" in result.output
    assert "Python Runtime" in result.output


def test_cli_doctor_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "overall_status" in data
    assert "python_version" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_cli_new_and_validate(tmp_path: Path):
    runner = CliRunner()
    proj_path = tmp_path / "test_project.json"

    # Create new project
    res_new = runner.invoke(cli, ["new", str(proj_path), "--title", "CLI Created Project", "--preset", "1080p"])
    assert res_new.exit_code == 0
    assert proj_path.exists()

    # Validate project
    res_val = runner.invoke(cli, ["validate", str(proj_path), "--json"])
    assert res_val.exit_code == 0
    data = json.loads(res_val.output)
    assert data["valid"] is True
    assert data["title"] == "CLI Created Project"

