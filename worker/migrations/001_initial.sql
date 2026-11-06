PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    duration_seconds INTEGER,
    caption_available INTEGER,
    availability TEXT,
    url TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    start_seconds REAL NOT NULL,
    duration_seconds REAL NOT NULL,
    text TEXT NOT NULL,
    language TEXT NOT NULL,
    source TEXT NOT NULL,
    is_generated INTEGER,
    UNIQUE(video_id, source, language, start_seconds)
);

CREATE TABLE IF NOT EXISTS transcript_samples (
    video_id TEXT PRIMARY KEY REFERENCES videos(video_id) ON DELETE CASCADE,
    sample_size INTEGER NOT NULL,
    selected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('available', 'no_transcript', 'blocked', 'unavailable', 'error')),
    error_code TEXT,
    attempted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    isbn TEXT,
    open_library_id TEXT,
    cover_url TEXT,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    start_seconds REAL NOT NULL,
    evidence_excerpt TEXT NOT NULL,
    classification TEXT,
    confidence REAL,
    review_status TEXT,
    extraction_method TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    stats_json TEXT,
    error_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_segments_video ON transcript_segments(video_id);
CREATE INDEX IF NOT EXISTS idx_attempts_video ON transcript_attempts(video_id);
CREATE INDEX IF NOT EXISTS idx_mentions_book ON mentions(book_id);
CREATE INDEX IF NOT EXISTS idx_mentions_video ON mentions(video_id);
