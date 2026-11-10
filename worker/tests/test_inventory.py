import sqlite3
import tempfile
import unittest
from pathlib import Path

from worker.db import connect, migrate
from worker.transcript_pilot import run_transcript_pilot
from worker.youtube_inventory import YouTubeClient, parse_duration, upsert_videos


class FakeYouTubeClient(YouTubeClient):
    def __init__(self):
        super().__init__("test")
        self.calls = 0

    def request(self, resource, **params):
        self.calls += 1
        if params.get("pageToken"):
            return {"items": [{"snippet": {"title": "Second", "channelId": "c"}, "contentDetails": {"videoId": "v2"}}]}
        return {
            "items": [{"snippet": {"title": "First", "channelId": "c"}, "contentDetails": {"videoId": "v1"}}],
            "nextPageToken": "next",
        }


class FakeTranscript:
    language_code = "en"
    is_generated = True

    def fetch(self):
        return [{"text": "A book", "start": 12.5, "duration": 2.0}]


class FakeTranscriptApi:
    def list(self, video_id):
        return [FakeTranscript()]


class InventoryTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(parse_duration("PT1H2M3S"), 3723)
        self.assertIsNone(parse_duration("bad"))

    def test_pagination(self):
        videos = FakeYouTubeClient().inventory("uploads")
        self.assertEqual([video["video_id"] for video in videos], ["v1", "v2"])

    def test_transcript_segments_are_stored(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "archive.db")
            migrate(connection)
            upsert_videos(connection, [{"video_id": "v1", "channel_id": "c", "title": "Title", "description": "", "url": "https://youtube.com/watch?v=v1"}])
            stats = run_transcript_pilot(connection, [{"video_id": "v1"}], languages=["en"], api_factory=FakeTranscriptApi, retries=0)
            self.assertEqual(stats["available"], 1)
            self.assertEqual(connection.execute("SELECT text FROM transcript_segments").fetchone()[0], "A book")

    def test_idempotent_upsert(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "archive.db")
            migrate(connection)
            video = {"video_id": "v1", "channel_id": "c", "title": "Title", "description": "", "url": "https://youtube.com/watch?v=v1"}
            upsert_videos(connection, [video])
            upsert_videos(connection, [video])
            self.assertEqual(connection.execute("SELECT count(*) FROM videos").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
