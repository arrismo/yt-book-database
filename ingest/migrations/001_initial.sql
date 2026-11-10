PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS videos (
  video_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, title TEXT NOT NULL,
  published_at TEXT, duration_seconds REAL, url TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '', source_url TEXT, source_date TEXT,
  discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER,
  subject TEXT NOT NULL, isbn TEXT, open_library_id TEXT, cover_url TEXT,
  description TEXT NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]', verified_at TEXT
);
CREATE TABLE IF NOT EXISTS transcript_segments (
  id INTEGER PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(video_id),
  start_seconds REAL NOT NULL, duration_seconds REAL NOT NULL, text TEXT NOT NULL,
  language TEXT NOT NULL, source TEXT NOT NULL, is_generated INTEGER,
  UNIQUE(video_id, source, language, start_seconds)
);
CREATE TABLE IF NOT EXISTS transcript_attempts (
  id INTEGER PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(video_id),
  provider TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('available','no_transcript','blocked','unavailable','error')),
  error_code TEXT, attempted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mentions (
  id TEXT PRIMARY KEY, book_id TEXT NOT NULL REFERENCES books(id), video_id TEXT NOT NULL REFERENCES videos(video_id),
  start_seconds REAL, evidence_excerpt TEXT NOT NULL, evidence_type TEXT NOT NULL,
  classification TEXT NOT NULL DEFAULT 'referenced', confidence REAL,
  review_status TEXT NOT NULL CHECK(review_status IN ('confirmed','pending','rejected')),
  extraction_method TEXT NOT NULL, note TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY, run_type TEXT NOT NULL, started_at TEXT NOT NULL,
  finished_at TEXT, status TEXT NOT NULL, stats_json TEXT, error_summary TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS segment_video_time ON transcript_segments(video_id,start_seconds);
CREATE INDEX IF NOT EXISTS mention_book ON mentions(book_id);
CREATE INDEX IF NOT EXISTS attempt_video ON transcript_attempts(video_id,attempted_at);
