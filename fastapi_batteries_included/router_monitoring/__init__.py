from pathlib import Path

from aiofile import async_open
from fastapi import APIRouter, Depends, FastAPI
from pydantic import Field
from pydantic.main import BaseModel

from fastapi_batteries_included.helpers.metrics import set_no_metrics

router = APIRouter()


class RunningResponse(BaseModel):
    "If we respond, we are running"
    running: bool = True


class VersionResponse(BaseModel):
    "Version numbers"
    circle: str = Field(example="1234")
    hash: str = Field(example="366c204")


@router.get(
    "/running",
    response_model=RunningResponse,
    summary="Verify the service is running",
    tags=["infra"],
    dependencies=[Depends(set_no_metrics)],
)
async def running() -> dict[str, bool]:
    """Verifies that the service is running. Used for monitoring in kubernetes."""
    return {"running": True}


@router.get(
    "/version",
    response_description="Version numbers",
    response_model=VersionResponse,
    tags=["infra"],
    summary="Get version information",
    dependencies=[Depends(set_no_metrics)],
)
async def app_version() -> dict[str, str]:
    """Get the circleci build number, and git hash."""

    file_to_data_map = {
        "circle": "build-circleci.txt",
        "hash": "build-githash.txt",
    }
    version = {}
    for key in file_to_data_map:
        try:
            async with async_open(Path(f"/app/{file_to_data_map[key]}"), "r") as afp:
                version[key] = (await afp.read()).strip()
        except OSError:
            version[key] = "unknown"
    return version


def init_monitoring(app: FastAPI) -> None:
    app.include_router(router)
    if app.openapi_tags is None:
        app.openapi_tags = []

    if not any(tag["name"] == "infra" for tag in app.openapi_tags):
        app.openapi_tags.append(
            {"name": "infra", "description": "Infrastructure and Monitoring"}
        )
