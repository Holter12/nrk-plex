from __future__ import annotations

from fastapi import FastAPI, HTTPException

from nrk_plex.nrk.client import NrkApiError, NrkClient

app = FastAPI(title="NRK Plex", version="0.1.0")
client = NrkClient()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/nrk/playback/{program_id}")
async def playback(program_id: str, manifest_type: str = "vod") -> dict[str, object]:
    try:
        metadata = await client.playback_metadata(program_id, manifest_type)
        manifest = await client.playback_manifest(program_id, manifest_type)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"program_id": program_id, "metadata": metadata, "manifest": manifest}


@app.get("/api/nrk/epg")
async def epg(channels: str = "nrk1,nrk2,nrk3") -> object:
    channel_ids = [item.strip() for item in channels.split(",") if item.strip()]
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        return await client.epg(channel_ids)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
