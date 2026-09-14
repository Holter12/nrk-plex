from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from nrk_plex.nrk.client import NrkApiError, NrkClient

app = FastAPI(title="NRK Plex", version="0.2.0")
client = NrkClient()


def _first_hls_asset(manifest: Any) -> str | None:
    playable = manifest.get("playable") if isinstance(manifest, dict) else None
    assets = playable.get("assets") if isinstance(playable, dict) else None
    if not isinstance(assets, list):
        return None

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if asset.get("format") == "HLS" and isinstance(asset.get("url"), str):
            return asset["url"]
    return None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/nrk/playback/{program_id}")
async def playback(program_id: str) -> dict[str, object]:
    try:
        metadata = await client.playback_metadata(program_id)
        manifest = await client.playback_manifest(program_id)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"program_id": program_id, "metadata": metadata, "manifest": manifest}


@app.get("/api/nrk/play/{program_id}")
async def play(program_id: str) -> RedirectResponse:
    try:
        manifest = await client.playback_manifest(program_id)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    asset_url = _first_hls_asset(manifest)
    if not asset_url:
        raise HTTPException(status_code=404, detail="NRK did not return an HLS playback asset")

    return RedirectResponse(asset_url, status_code=307)


@app.get("/api/nrk/epg")
async def epg(channels: str = "nrk1,nrk2,nrk3") -> object:
    channel_ids = [item.strip() for item in channels.split(",") if item.strip()]
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        return await client.epg(channel_ids)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
