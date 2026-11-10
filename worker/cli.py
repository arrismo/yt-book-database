from __future__ import annotations

import argparse
import os
import sqlite3
import sys

from .db import connect, finish_run, migrate, start_run, utc_now
from .transcript_pilot import run_transcript_pilot, select_sample
from .youtube_inventory import YouTubeAPIError, YouTubeClient, upsert_videos


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Jared A. Ball book archive worker")
    root.add_argument("--database", default=os.getenv("DATABASE_PATH", "data/archive.db"), help="SQLite database path")
    sub = root.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("inventory", help="inventory accessible channel uploads")
    inventory.add_argument("--handle", default="@jaredaball")
    inventory.add_argument("--api-key", default=os.getenv("YOUTUBE_API_KEY"))
    inventory.add_argument("--dry-run", action="store_true", help="fetch and report without writing videos")
    inventory.add_argument("--no-hydrate", action="store_true", help="skip videos.list metadata hydration")
    pilot = sub.add_parser("transcript-pilot", help="retrieve transcripts for a deterministic pilot sample")
    pilot.add_argument("--sample-size", type=int, default=20)
    pilot.add_argument("--languages", default="en", help="comma-separated preferred language codes (default: en)")
    pilot.add_argument("--retries", type=int, default=1, help="transient retries per video (default: 1)")
    pilot.add_argument("--backoff", type=float, default=2.0, help="seconds between retries (default: 2)")
    return root


def run_inventory(args: argparse.Namespace) -> int:
    if not args.api_key:
        raise SystemExit("YOUTUBE_API_KEY is required (or pass --api-key)")
    connection = connect(args.database)
    migrate(connection)
    run_id = None if args.dry_run else start_run(connection, "inventory")
    try:
        client = YouTubeClient(args.api_key)
        channel_id, uploads_id = client.resolve_channel(args.handle)
        videos = client.inventory(uploads_id)
        for video in videos:
            video["channel_id"] = channel_id
        if not args.no_hydrate and videos:
            client.hydrate(videos)
        if args.dry_run:
            print(f"Discovered {len(videos)} videos for {args.handle} (dry run; database unchanged)")
        else:
            upsert_videos(connection, videos)
            finish_run(connection, run_id, "success", {"channel_id": channel_id, "videos_discovered": len(videos), "videos_upserted": len(videos)})
            print(f"Discovered and upserted {len(videos)} videos for {args.handle}")
        return 0
    except YouTubeAPIError as exc:
        if run_id is not None:
            finish_run(connection, run_id, "error", {}, str(exc))
        raise SystemExit(str(exc)) from exc
    finally:
        connection.close()


def run_pilot(args: argparse.Namespace) -> int:
    if args.sample_size <= 0 or args.retries < 0:
        raise SystemExit("--sample-size must be positive and --retries cannot be negative")
    connection = connect(args.database)
    migrate(connection)
    run_id = None
    try:
        sample = select_sample(connection, args.sample_size)
        if not sample:
            raise SystemExit("No inventoried videos found; run inventory first")
        selected_at = utc_now()
        for video in sample:
            connection.execute(
                "INSERT INTO transcript_samples(video_id, sample_size, selected_at) VALUES (?, ?, ?) "
                "ON CONFLICT(video_id) DO UPDATE SET sample_size=excluded.sample_size, selected_at=excluded.selected_at",
                (video["video_id"], len(sample), selected_at),
            )
        connection.commit()
        run_id = start_run(connection, "transcript_pilot")
        languages = [language.strip() for language in args.languages.split(",") if language.strip()]
        if not languages:
            raise SystemExit("--languages must contain at least one language code")
        stats = run_transcript_pilot(
            connection, sample, languages=languages, retries=args.retries, sleep_seconds=args.backoff
        )
        finish_run(connection, run_id, "success", stats)
        print("Transcript pilot coverage:")
        print("  " + ", ".join(f"{key}={value}" for key, value in stats.items()))
        return 0
    except RuntimeError as exc:
        if run_id is not None:
            finish_run(connection, run_id, "error", {}, str(exc))
        raise SystemExit(str(exc)) from exc
    finally:
        connection.close()


def main() -> None:
    args = parser().parse_args()
    if args.command == "inventory":
        return_code = run_inventory(args)
    else:
        return_code = run_pilot(args)
    raise SystemExit(return_code)
