from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any
from urllib.parse import quote


DEFAULT_CHANNELS = ["nrk1", "nrk2", "nrk3"]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _entry_start(entry: dict[str, Any]) -> datetime | None:
    start = entry.get("start")
    if not isinstance(start, dict):
        return None
    return _parse_time(start.get("actual") or start.get("planned"))


def _entry_end(entry: dict[str, Any]) -> datetime | None:
    end = entry.get("end")
    if not isinstance(end, dict):
        return None
    return _parse_time(end.get("actual") or end.get("planned"))


def _channel_entries(epg: Any) -> list[tuple[str, str, list[dict[str, Any]]]]:
    if not isinstance(epg, list):
        return []

    result: list[tuple[str, str, list[dict[str, Any]]]] = []
    for channel in epg:
        if not isinstance(channel, dict):
            continue
        channel_id = channel.get("channelId")
        title = channel.get("title") or channel_id
        groups = channel.get("transmissionGroups")
        if not isinstance(channel_id, str) or not isinstance(groups, list):
            continue

        entries: list[dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_entries = group.get("entries")
            if isinstance(group_entries, list):
                entries.extend(item for item in group_entries if isinstance(item, dict))
        result.append((channel_id, str(title), entries))
    return result


def find_current_program(epg: Any, channel_id: str) -> str | None:
    now = datetime.now(timezone.utc)
    for current_id, _title, entries in _channel_entries(epg):
        if current_id != channel_id:
            continue
        candidates: list[tuple[datetime, str]] = []
        for entry in entries:
            program_id = entry.get("programId")
            if not isinstance(program_id, str):
                continue
            start = _entry_start(entry)
            end = _entry_end(entry)
            if start is None or end is None:
                continue
            start = start.astimezone(timezone.utc)
            end = end.astimezone(timezone.utc)
            if start <= now < end:
                return program_id
            candidates.append((start, program_id))
        if candidates:
            return None
    return None


def build_m3u(epg: Any, base_url: str, channels: list[str]) -> str:
    channel_map = {channel_id: title for channel_id, title, _ in _channel_entries(epg)}
    lines = ["#EXTM3U"]
    for channel_id in channels:
        title = channel_map.get(channel_id, channel_id.upper())
        stream_url = f"{base_url.rstrip('/')}/api/nrk/live/{quote(channel_id, safe='')}"
        lines.append(
            f'#EXTINF:-1 tvg-id="{escape(channel_id, quote=True)}" '
            f'tvg-name="{escape(title, quote=True)}" group-title="NRK",{escape(title)}'
        )
        lines.append(stream_url)
    return "\n".join(lines) + "\n"


def _xmltv_time(value: datetime) -> str:
    local = value.astimezone()
    offset = local.utcoffset() or timezone.utc.utcoffset(local)
    total_minutes = int(offset.total_seconds() // 60) if offset else 0
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return local.strftime("%Y%m%d%H%M%S") + f" {sign}{total_minutes // 60:02d}{total_minutes % 60:02d}"


def build_xmltv(epg: Any) -> str:
    channels = _channel_entries(epg)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv generator-info-name="nrk-plex">']

    for channel_id, title, _entries in channels:
        lines.append(f'  <channel id="{escape(channel_id, quote=True)}">')
        lines.append(f"    <display-name>{escape(title)}</display-name>")
        lines.append("  </channel>")

    for channel_id, _title, entries in channels:
        for entry in entries:
            program_id = entry.get("programId")
            start = _entry_start(entry)
            end = _entry_end(entry)
            if not isinstance(program_id, str) or start is None or end is None or end <= start:
                continue

            title = entry.get("title") or entry.get("heading") or "NRK"
            description = entry.get("description")
            category = entry.get("category")
            category_name = category.get("displayValue") if isinstance(category, dict) else None

            lines.append(
                f'  <programme channel="{escape(channel_id, quote=True)}" '
                f'start="{_xmltv_time(start)}" stop="{_xmltv_time(end)}">'
            )
            lines.append(f"    <title lang=\"no\">{escape(str(title))}</title>")
            if isinstance(description, str) and description:
                lines.append(f"    <desc lang=\"no\">{escape(description)}</desc>")
            if isinstance(category_name, str) and category_name:
                lines.append(f"    <category lang=\"no\">{escape(category_name)}</category>")
            lines.append(f"    <episode-num system=\"onscreen\">{escape(program_id)}</episode-num>")
            lines.append("  </programme>")

    lines.append("</tv>")
    return "\n".join(lines) + "\n"
