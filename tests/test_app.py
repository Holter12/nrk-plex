from httpx import ASGITransport, AsyncClient
import pytest

from nrk_plex.app import app


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
    assert data["FirmwareVersion"] == "0.4.0"


@pytest.mark.asyncio
async def test_hdhr_lineup() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/lineup.json")

    assert response.status_code == 200
    lineup = response.json()
    assert [channel["GuideName"] for channel in lineup] == ["NRK1", "NRK2", "NRK3"]
    assert lineup[0]["URL"] == "http://test/api/nrk/live/nrk1"
