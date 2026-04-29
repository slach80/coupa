import httpx

from .config import Config


class CoupaClient:
    def __init__(self, config: Config) -> None:
        self._base_url = config.api_url
        self._headers = {
            "X-COUPA-API-KEY": config.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as http:
            response = await http.get(path, params=params)
            response.raise_for_status()
            return response.json()

    async def put(self, path: str, body: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as http:
            response = await http.put(path, json=body)
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, body: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as http:
            response = await http.post(path, json=body)
            response.raise_for_status()
            return response.json()
