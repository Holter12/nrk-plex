from httpx import ASGITransport, AsyncClient
import pytest

from nrk_plex.app import app, client as app_module_client


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_hdhr_discovery() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/discover.json")

    assert response.status_code == 200
    data = response.json()
    assert data["FriendlyName"] == "NRK Plex"
    assert data["TunerCount"] == 3
    assert data["LineupURL"] == "http://test/lineup.json"
    assert data["FirmwareVersion"] == "0.4.1"


@pytest.mark.asyncio
async def test_hdhr_lineup() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/lineup.json")

    assert response.status_code == 200
    lineup = response.json()
    assert [channel["GuideName"] for channel in lineup] == ["NRK1", "NRK2", "NRK3"]
    assert lineup[0]["URL"] == "http://test/api/nrk/live/nrk1"


@pytest.mark.asyncio
async def test_live_subtitles(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_manifest(program_id: str, manifest_type: str = "program") -> dict[str, object]:
        assert program_id == "nrk1"
        assert manifest_type == "channel"
        return {
            "playable": {
                "assets": [{"format": "HLS", "url": "https://example.invalid/live.m3u8"}],
                "subtitles": [
                    {
                        "language": "no",
                        "name": "Norsk",
                        "defaultOn": True,
                        "webVtt": "https://example.invalid/subtitles.m3u8",
                    }
                ],
            }
        }

    monkeypatch.setattr(app_module_client, "playback_manifest", fake_manifest)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/nrk/live-subtitles/nrk1")

    assert response.status_code == 200
    assert response.json() == {
        "channel_id": "nrk1",
        "channel_name": "NRK1",
        "hls_available": True,
        "subtitles": [
            {
                "language": "no",
                "name": "Norsk",
                "defaultOn": True,
                "webVtt": "https://example.invalid/subtitles.m3u8",
            }
        ],
    }
