from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from nrk_plex.nrk.client import NrkApiError, NrkClient
from nrk_plex.plex import DEFAULT_CHANNELS, build_m3u, build_xmltv

app = FastAPI(title="NRK Plex", version="0.3.3")
client = NrkClient()


CHANNEL_NAMES = {
    "nrk1": "NRK1",
    "nrk2": "NRK2",
    "nrk3": "NRK3",
}


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


def _parse_channels(channels: str) -> list[str]:
    return [item.strip() for item in channels.split(",") if item.strip()]


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


@app.get("/api/nrk/live/{channel_id}")
async def live(channel_id: str) -> RedirectResponse:
    # NRK's current live-TV API uses manifest type 'channel'.
    # A live channel is a continuous stream and must use the channel manifest directly.
    try:
        manifest = await client.playback_manifest(channel_id, manifest_type="channel")
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    asset_url = _first_hls_asset(manifest)
    if not asset_url:
        raise HTTPException(status_code=404, detail="NRK did not return an HLS live playback asset")

    return RedirectResponse(asset_url, status_code=307)


@app.get("/api/nrk/epg")
async def epg(channels: str = ",".join(DEFAULT_CHANNELS)) -> object:
    channel_ids = _parse_channels(channels)
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        return await client.epg(channel_ids)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/plex/playlist.m3u", response_class=PlainTextResponse)
async def plex_playlist(request: Request, channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    channel_ids = _parse_channels(channels)
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        epg = await client.epg(channel_ids)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    base_url = str(request.base_url).rstrip("/")
    # Keep the M3U endpoint as text so browsers display the playlist rather than
    # treating it as an HLS resource.
    return PlainTextResponse(build_m3u(epg, base_url, channel_ids), media_type="text/plain")


@app.get("/api/plex/epg.xml", response_class=PlainTextResponse)
async def plex_epg(channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    channel_ids = _parse_channels(channels)
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        epg = await client.epg(channel_ids)
    except NrkApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return PlainTextResponse(build_xmltv(epg), media_type="application/xml")


# HDHomeRun-compatible endpoints let Plex treat this service as a network tuner,
# avoiding a separate xTeVe/Threadfin container for this small NRK lineup.
@app.get("/discover.json")
async def discover(request: Request) -> dict[str, object]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "FriendlyName": "NRK Plex",
        "ModelNumber": "NRK-3TUNER",
        "FirmwareName": "nrk-plex",
        "FirmwareVersion": "0.3.3",
        "DeviceID": "4E524B50",
        "DeviceAuth": "nrk-plex",
        "TunerCount": len(DEFAULT_CHANNELS),
        "BaseURL": base_url,
        "LineupURL": f"{base_url}/lineup.json",
    }


@app.get("/lineup.json")
async def lineup(request: Request) -> list[dict[str, object]]:
    base_url = str(request.base_url).rstrip("/")
    return [
        {
            "GuideNumber": str(index),
            "GuideName": CHANNEL_NAMES.get(channel_id, channel_id.upper()),
            "URL": f"{base_url}/api/nrk/live/{channel_id}",
            "HD": 1,
        }
        for index, channel_id in enumerate(DEFAULT_CHANNELS, start=1)
    ]


@app.get("/lineup_status.json")
async def lineup_status() -> dict[str, object]:
    return {
        "ScanInProgress": 0,
        "ScanPossible": 0,
        "Source": "IPTV",
        "SourceList": ["IPTV"],
    }


@app.get("/playlist.m3u", response_class=PlainTextResponse, include_in_schema=False)
async def playlist_alias(request: Request, channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    return await plex_playlist(request, channels)


@app.get("/epg.xml", response_class=PlainTextResponse, include_in_schema=False)
async def epg_alias(channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    return await plex_epg(channels)
