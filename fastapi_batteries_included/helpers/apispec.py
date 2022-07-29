import importlib.util
from pathlib import Path
from typing import Any, Callable, Optional, Union

import typer
import yaml
from fastapi import FastAPI


def generate_openapi_spec(app: FastAPI, output: Union[Path, str] = None) -> dict:
    spec_dict = app.openapi()

    # Order the spec so that they are consistently laid out.
    spec_dict = _sorted_jsonable(spec_dict)
    top_keys = ["openapi", "info", "servers", "tags", "paths"]
    ordered_spec = dict.fromkeys(key for key in top_keys if key in spec_dict)
    ordered_spec.update(spec_dict)
    yaml_text = yaml.safe_dump(ordered_spec, sort_keys=False)
    if output:
        Path(output).write_text(yaml_text)
    return ordered_spec


def _sorted_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sorted_jsonable(value[k]) for k in sorted(value.keys())}
    elif isinstance(value, list):
        return [_sorted_jsonable(v) for v in value]
    else:
        return value


def _get_app(app_path: Path) -> FastAPI:
    spec: Any = importlib.util.spec_from_file_location(
        f"{app_path.parent.name}.{app_path.with_suffix('').name}", str(app_path)
    )
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    app_obj: Optional[FastAPI] = getattr(app_module, "app", None)
    if not app_obj:
        create_app: Optional[Callable] = getattr(app_module, "create_app", None)
        if create_app:
            app_obj = create_app()
    if not app_obj:
        typer.secho("Cannot create app", fg=typer.colors.RED)
        typer.Exit(1)
        raise RuntimeError("Cannot create app")
    return app_obj


def _script() -> Callable:
    CWD = Path().resolve()
    DEFAULT_APP = [*Path().glob("*/autoapp.py"), *Path().glob("*/app.py"), ...][0]
    DEFAULT_OUTPUT = (
        (DEFAULT_APP / "../openapi/openapi.yaml").resolve().relative_to(CWD)
        if isinstance(DEFAULT_APP, Path)
        else ...
    )

    def main_script(
        output: Path = typer.Option(
            default=DEFAULT_OUTPUT, help="Location of openapi.yaml"
        ),
        app: Path = typer.Argument(
            default=DEFAULT_APP, exists=True, help="Path to autoapp.py or app.py"
        ),
    ) -> None:
        typer.secho(f"Generating OpenAPI spec for {app}", fg=typer.colors.GREEN)
        app_obj = _get_app(app_path=app)
        generate_openapi_spec(app_obj, output=output)
        typer.secho(f"API specification generated in {output}", fg=typer.colors.GREEN)

    return main_script


def create_openapi() -> None:
    main_script = _script()
    typer.run(main_script)
