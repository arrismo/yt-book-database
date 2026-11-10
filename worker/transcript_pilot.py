from __future__ import annotations

import time
from typing import Any, Callable

from .db import utc_now

PROVIDER = "youtube-transcript-api"


def select_sample(connection, sample_size: int) -> list[dict[str, Any]]:
    """Select a deterministic, age-spread sample for the transcript pilot."""
    rows = connection.execute(
        "SELECT video_id, title, published_at, duration_seconds FROM videos "
        "ORDER BY published_at ASC, video_id ASC"
    ).fetchall()
    if not rows or sample_size <= 0:
        return []
    if sample_size >= len(rows):
        return [dict(row) for row in rows]
    indexes = {round(i * (len(rows) - 1) / (sample_size - 1)) for i in range(sample_size)} if sample_size > 1 else {len(rows) // 2}
    return [dict(rows[index]) for index in sorted(indexes)]


def _value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item[key]
    return getattr(item, key)


def _error_status(exc: Exception) -> tuple[str, str]:
    name = type(exc).__name__
    if name in {"RequestBlocked", "IpBlocked"}:
        return "blocked", name
    if name in {"NoTranscriptFound", "TranscriptsDisabled"}:
        return "no_transcript", name
    if name in {"VideoUnavailable", "InvalidVideoId", "AgeRestricted"}:
        return "unavailable", name
    return "error", name


def fetch_transcript(api: Any, video_id: str, languages: list[str]) -> tuple[list[Any], str, bool]:
    """Fetch one transcript, preferring requested languages and then any available language."""
    transcript_list = api.list(video_id)
    transcripts = list(transcript_list)
    if not transcripts:
        raise RuntimeError("No transcripts listed")
    selected = next(
        (item for language in languages for item in transcripts if _value(item, "language_code") == language),
        transcripts[0],
    )
    fetched = selected.fetch()
    return list(fetched), _value(selected, "language_code"), bool(_value(selected, "is_generated"))


def store_attempt(connection: Any, video_id: str, status: str, error_code: str | None) -> None:
    connection.execute(
        "INSERT INTO transcript_attempts(video_id, provider, status, error_code, attempted_at) VALUES (?, ?, ?, ?, ?)",
        (video_id, PROVIDER, status, error_code, utc_now()),
    )


def store_segments(connection: Any, video_id: str, segments: list[Any], language: str, is_generated: bool) -> int:
    for segment in segments:
        connection.execute(
            """INSERT INTO transcript_segments
            (video_id, start_seconds, duration_seconds, text, language, source, is_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id, source, language, start_seconds) DO UPDATE SET
              duration_seconds=excluded.duration_seconds, text=excluded.text,
              is_generated=excluded.is_generated""",
            (video_id, float(_value(segment, "start")), float(_value(segment, "duration")),
             str(_value(segment, "text")), language, PROVIDER, int(is_generated)),
        )
    return len(segments)


def run_transcript_pilot(
    connection: Any,
    sample: list[dict[str, Any]],
    *,
    languages: list[str],
    retries: int = 1,
    sleep_seconds: float = 2.0,
    api_factory: Callable[[], Any] | None = None,
) -> dict[str, int]:
    if api_factory is None:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError as exc:
            raise RuntimeError("Install requirements first: pip install -r requirements.txt") from exc
        api_factory = YouTubeTranscriptApi

    api = api_factory()
    stats = {"total": len(sample), "available": 0, "no_transcript": 0, "blocked": 0, "unavailable": 0, "error": 0, "segments": 0}
    for index, video in enumerate(sample):
        video_id = video["video_id"]
        status = "error"
        for attempt in range(retries + 1):
            try:
                segments, language, is_generated = fetch_transcript(api, video_id, languages)
                stats["segments"] += store_segments(connection, video_id, segments, language, is_generated)
                store_attempt(connection, video_id, "available", None)
                stats["available"] += 1
                status = "available"
                break
            except Exception as exc:  # Provider exceptions vary by version; classify by stable class names.
                status, error_code = _error_status(exc)
                transient = status == "error" and attempt < retries
                if transient:
                    time.sleep(sleep_seconds * (attempt + 1))
                    continue
                store_attempt(connection, video_id, status, error_code)
                stats[status] += 1
                break
        connection.commit()
        print(f"[{index + 1}/{len(sample)}] {video_id}: {status}")
    return stats
