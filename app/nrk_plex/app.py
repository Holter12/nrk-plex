from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from nrk_plex.nrk.client import NrkApiError, NrkClient
from nrk_plex.plex import DEFAULT_CHANNELS, build_m3u, build_xmltv, find_current_program

app = FastAPI(title="NRK Plex", version="0.3.2")
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
    # Do not resolve the current EPG program here: a live channel is a
    # continuous stream and must use the channel manifest directly.
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
    # Use text/plain rather than application/x-mpegURL. The latter makes
    # browsers interpret this IPTV playlist as a playable HLS resource,
    # which results in an empty video player instead of showing the M3U text.
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


@app.get("/playlist.m3u", response_class=PlainTextResponse, include_in_schema=False)
async def playlist_alias(request: Request, channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    return await plex_playlist(request, channels)


@app.get("/epg.xml", response_class=PlainTextResponse, include_in_schema=False)
async def epg_alias(channels: str = ",".join(DEFAULT_CHANNELS)) -> PlainTextResponse:
    return await plex_epg(channels)
