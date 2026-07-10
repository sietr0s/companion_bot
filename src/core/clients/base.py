import logging
from typing import Any

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or settings.INTERNAL_API_BASE_URL
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response | None:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self._base_url}{path}"
                response = await client.request(
                    method,
                    url,
                    timeout=self._timeout,
                    **kwargs,
                )
                response.raise_for_status()
                return response
        except httpx.TimeoutException:
            logger.warning("Таймаут HTTP-запроса: %s %s", method, path)
            return None
        except httpx.ConnectError as e:
            logger.error("Ошибка подключения к %s %s: %s", method, path, e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error("HTTP ошибка %s %s: статус %s", method, path, e.response.status_code)
            return None
        except httpx.RequestError as e:
            logger.error("Ошибка запроса %s %s: %s", method, path, e)
            return None
        return None

    async def get(self, path: str, **kwargs: Any) -> httpx.Response | None:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response | None:
        return await self._request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response | None:
        return await self._request("DELETE", path, **kwargs)
