from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette import status

from fastapi_batteries_included import config

api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

api_key_settings = config.ApiKeySettings()


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> None:
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No API key supplied"
        )
    if api_key != api_key_settings.ACCEPTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key supplied"
        )
