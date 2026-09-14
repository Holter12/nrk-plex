from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("NRK_PSAPI_BASE_URL", "https://psapi.nrk.no")
    timeout_seconds: float = float(os.getenv("NRK_HTTP_TIMEOUT", "15"))

    @property
    def playback_accept(self) -> str:
        return os.getenv(
            "NRK_PLAYBACK_ACCEPT",
            "application/vnd.nrk.psapi+json; version=9; player=tv-player; device=player-core",
        )


settings = Settings()
