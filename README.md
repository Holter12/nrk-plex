# NRK Plex

Self-hosted NRK TV bridge for Plex, designed for Unraid and Docker.

> Early development: this repository contains the foundation and NRK API client. Plex integration is being built incrementally.

## Goals

- Use NRK's current PSAPI playback endpoints instead of the obsolete Plex Channel plugin model.
- Provide a small, maintainable HTTP service that can run on Unraid.
- Support NRK on-demand content and live TV/EPG.
- Avoid transcoding where Plex can consume NRK's HLS streams directly.
- Keep persistent application state under `/config` and cache under `/cache`.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
uvicorn nrk_plex.app:app --reload
```

## Docker

```bash
docker compose up --build
```

The service is exposed on port `8080` by default.

## Unraid

The repository includes an Unraid Community Applications template at `templates/nrk-plex.xml`. The template is intentionally conservative during early development; once the container and Plex endpoints are stable, it can be submitted to Community Applications.

## API notes

NRK playback requests use the PSAPI media negotiation header used by current third-party clients:

```http
Accept: application/vnd.nrk.psapi+json; version=9; player=tv-player; device=player-core
```

The implementation keeps endpoint paths configurable so changes to NRK's API do not require a broad rewrite.

## License

MIT
