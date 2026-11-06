import sqlite3
import tempfile
import unittest
from pathlib import Path

from worker.db import connect, migrate
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


class InventoryTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(parse_duration("PT1H2M3S"), 3723)
        self.assertIsNone(parse_duration("bad"))

    def test_pagination(self):
        videos = FakeYouTubeClient().inventory("uploads")
        self.assertEqual([video["video_id"] for video in videos], ["v1", "v2"])

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
