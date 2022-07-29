from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
import yaml
from pytest_mock import MockFixture
from typer.testing import CliRunner


class TestCreateOpenapi:
    @pytest.fixture
    def mock_init_metrics(self, mocker: MockFixture) -> MagicMock:
        """Mock out init_metrics() because the script autogenerates an app and we can't set the `testing` flag."""
        import fastapi_batteries_included

        mocked = mocker.patch.object(fastapi_batteries_included, "init_metrics")
        return mocked

    def test_create_openapi(self, mock_init_metrics: MagicMock, tmpdir: Path) -> None:
        from fastapi_batteries_included.helpers.apispec import _script

        main_script = _script()
        app = typer.Typer()
        app.command()(main_script)

        runner = CliRunner()
        outfile = tmpdir / "openapi.yaml"
        result = runner.invoke(app, f"--output={outfile}")
        assert result.exit_code == 0, result.stdout
        assert "API specification generated" in result.stdout

        spec = yaml.safe_load(outfile.read_text(encoding="utf-8"))
        assert spec["paths"].keys() == {"/running", "/version"}
