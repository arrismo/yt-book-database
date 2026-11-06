from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .db import utc_now

API_ROOT = "https://www.googleapis.com/youtube/v3"
_DURATION = re.compile(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?P<seconds>\d+(?:\.\d+)?)S?")


class YouTubeAPIError(RuntimeError):
    pass


def parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = _DURATION.fullmatch(value)
    if not match:
        return None
    return round(
        int(match.group("hours") or 0) * 3600
        + int(match.group("minutes") or 0) * 60
        + float(match.group("seconds") or 0)
    )


class YouTubeClient:
    def __init__(self, api_key: str, *, sleep_seconds: float = 0.0):
        self.api_key = api_key
        self.sleep_seconds = sleep_seconds

    def request(self, resource: str, **params: Any) -> dict[str, Any]:
        params["key"] = self.api_key
        url = f"{API_ROOT}/{resource}?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise YouTubeAPIError(f"YouTube API HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise YouTubeAPIError(f"YouTube API connection failed: {exc.reason}") from exc
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        return result

    def resolve_channel(self, handle: str) -> tuple[str, str]:
        result = self.request("channels", part="id,contentDetails", forHandle=handle.lstrip("@"))
        items = result.get("items", [])
        if not items:
            raise YouTubeAPIError(f"No YouTube channel found for handle {handle}")
        item = items[0]
        return item["id"], item["contentDetails"]["relatedPlaylists"]["uploads"]

    def inventory(self, uploads_playlist_id: str) -> list[dict[str, Any]]:
        videos: list[dict[str, Any]] = []
        token: str | None = None
        while True:
            params: dict[str, Any] = {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": 50,
            }
            if token:
                params["pageToken"] = token
            page = self.request("playlistItems", **params)
            for item in page.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("contentDetails", {}).get("videoId")
                if video_id:
                    videos.append({
                        "video_id": video_id,
                        "channel_id": snippet.get("videoOwnerChannelId") or snippet.get("channelId", ""),
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt"),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })
            token = page.get("nextPageToken")
            if not token:
                break
        return videos

    def hydrate(self, videos: list[dict[str, Any]]) -> None:
        for offset in range(0, len(videos), 50):
            ids = [video["video_id"] for video in videos[offset : offset + 50]]
            result = self.request("videos", part="contentDetails,status", id=",".join(ids))
            details = {item["id"]: item for item in result.get("items", [])}
            for video in videos[offset : offset + 50]:
                item = details.get(video["video_id"], {})
                content = item.get("contentDetails", {})
                video["duration_seconds"] = parse_duration(content.get("duration"))
                video["caption_available"] = content.get("caption") == "true"
                video["availability"] = item.get("status", {}).get("privacyStatus")


def upsert_videos(connection, videos: list[dict[str, Any]]) -> int:
    now = utc_now()
    for video in videos:
        connection.execute(
            """INSERT INTO videos
            (video_id, channel_id, title, description, published_at, duration_seconds,
             caption_available, availability, url, discovered_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
              channel_id=excluded.channel_id, title=excluded.title,
              description=excluded.description, published_at=excluded.published_at,
              duration_seconds=excluded.duration_seconds,
              caption_available=excluded.caption_available, availability=excluded.availability,
              url=excluded.url, updated_at=excluded.updated_at""",
            (video["video_id"], video["channel_id"], video["title"], video["description"],
             video.get("published_at"), video.get("duration_seconds"),
             video.get("caption_available"), video.get("availability"), video["url"], now, now),
        )
    connection.commit()
    return len(videos)
