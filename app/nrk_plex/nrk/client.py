from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from nrk_plex.config import settings


class NrkApiError(RuntimeError):
    pass


class NrkClient:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http

    async def _get_json(
        self,
        path: str,
        *,
        accept: str | None = None,
    ) -> Any:
        url = f"{settings.base_url.rstrip('/')}/{path.lstrip('/') }"
        headers = {"Accept": accept} if accept else {}
        if self._http is not None:
            response = await self._http.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
                response = await client.get(url, headers=headers)
        if response.is_error:
            raise NrkApiError(f"NRK API returned {response.status_code} for {path}")
        try:
            return response.json()
        except ValueError as exc:
            raise NrkApiError(f"NRK API returned non-JSON for {path}") from exc

    async def playback_metadata(self, program_id: str, manifest_type: str = "program") -> Any:
        encoded_id = quote(program_id, safe="")
        encoded_type = quote(manifest_type, safe="")
        return await self._get_json(
            f"playback/metadata/{encoded_type}/{encoded_id}",
            accept=settings.playback_accept,
        )

    async def playback_manifest(self, program_id: str, manifest_type: str = "program") -> Any:
        encoded_id = quote(program_id, safe="")
        encoded_type = quote(manifest_type, safe="")
        return await self._get_json(
            f"playback/manifest/{encoded_type}/{encoded_id}",
            accept=settings.playback_accept,
        )

    async def epg(self, channel_ids: list[str]) -> Any:
        encoded = ",".join(quote(channel_id, safe="") for channel_id in channel_ids)
        return await self._get_json(f"tv/epg/{encoded}")
