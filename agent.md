# Agent Instructions — Jared A. Ball Book Archive

## Mission
Build a public, searchable website cataloging books mentioned in publicly available videos on https://www.youtube.com/@jaredaball. Preserve verifiable video evidence and timestamps. A mention does not imply endorsement. The immediate priority is **video inventory and a 10–20-video transcript-access pilot**, not UI polish.

## Stack
- Frontend: Next.js (TypeScript), Tailwind CSS; deploy to Vercel.
- Data: SQLite (local `data/archive.db`) using Python `sqlite3`; versioned SQL migrations checked into source control. No hosted database or database service required.
- Ingestion: Python 3.11+ CLI/worker.
- Video inventory: official YouTube Data API v3.
- Transcript pilot: `youtube-transcript-api` (unofficial; may fail or be blocked). Use only where access is permitted; respect YouTube terms and applicable rights.
- Metadata verification later: Open Library and/or Google Books.
- Scheduled incremental ingestion later: GitHub Actions or equivalent.
- Do not use machine-learning models, embeddings, or generative extraction anywhere in this project. Use deterministic title/author matching, catalog lookups, and manual review.

## Implementation order
### Milestone 1 — Inventory all available uploads
1. Resolve `@jaredaball` to its canonical channel ID using the YouTube Data API (`channels.list` with `forHandle`, where supported).
2. Read the channel's uploads playlist ID from `contentDetails.relatedPlaylists.uploads`.
3. Page through `playlistItems.list` until `nextPageToken` is absent; upsert video IDs, titles, publication dates, descriptions, and source URLs.
4. Optionally hydrate duration, caption flag, and availability with `videos.list` in batches.
5. Record discovered count, scan time, and errors. Make re-runs idempotent and resumable. Do not assume all private, deleted, unlisted, or otherwise inaccessible videos can be inventoried.

### Milestone 2 — Transcript availability pilot
1. Select a reproducible sample of **10–20 videos** spread across old/new uploads and short/long durations. Store the sampled video IDs.
2. For each video, attempt to retrieve accessible transcript segments via `youtube-transcript-api` using a pinned, tested version. Preserve `start`, `duration`, `text`, language, and whether captions are generated when available.
3. Store status: `available`, `no_transcript`, `blocked`, `unavailable`, or `error`; save a concise diagnostic and attempt timestamp.
4. Keep requests modest; apply backoff on transient errors and avoid aggressive retries or circumvention of restrictions. Do not bypass authentication, access controls, CAPTCHAs, or rate limits.
5. Report coverage: total tested, successful, missing, blocked, and errored; compare by video age/duration where useful. Do not promise all transcripts will be accessible.
6. If the pilot is inadequate, evaluate a licensed/authorized hosted transcript provider, its terms, pricing, and batch capabilities **before** adopting it. The official YouTube captions API generally does not permit downloading arbitrary third-party captions without authorization.

### Milestone 3 — Book detection and validation
1. Start with a small known-title/author dictionary and keyword matching against timestamped transcript segments.
2. Resolve candidate books through Open Library/Google Books; cache results and respect API usage limits.
3. Store the exact source video, timestamp, short evidence excerpt, match method, confidence, and review status.
4. Do not infer that a book was recommended merely because it was mentioned. Categories: `recommended`, `criticized`, `discussed`, `referenced`, `unclear`.
5. Flag ambiguous references for manual review; do not fabricate books, authors, quotations, or timestamps.
6. Improve recall with aliases, normalized text, fuzzy matching with strict thresholds, and human review. Do not introduce AI-based extraction or classification.

### Milestone 4 — Public site and ongoing updates
1. Book grid with title, author, cover, subject filters, and search.
2. Book detail pages showing all associated videos, context, and clickable timestamp links (`https://www.youtube.com/watch?v=VIDEO_ID&t=SECONDSs`).
3. Show source coverage/processing status so missing transcripts are not confused with no book mentions.
4. Add scheduled incremental video discovery and retry only eligible failures.

## Database (initial design)
- `videos`: `video_id` (PK), `channel_id`, `title`, `description`, `published_at`, `duration_seconds`, `url`, `discovered_at`, `updated_at`.
- `transcript_segments`: `id`, `video_id` (FK), `start_seconds`, `duration_seconds`, `text`, `language`, `source`, `is_generated` (nullable).
- `transcript_attempts`: `id`, `video_id` (FK), `provider`, `status`, `error_code`, `attempted_at`.
- `books`: `id`, `title`, `author`, `isbn` (nullable), `open_library_id` (nullable), `cover_url` (nullable), `verified_at`.
- `mentions`: `id`, `book_id` (FK), `video_id` (FK), `start_seconds`, `evidence_excerpt`, `classification`, `confidence`, `review_status`, `extraction_method`.
- `ingestion_runs`: `id`, `run_type`, `started_at`, `finished_at`, `status`, `stats_json`, `error_summary`.
Use appropriate unique constraints (e.g. videos by `video_id`, transcript segments by video/source/language/start) and indexes for lookup and deduplication. Use SQLite constraints and indexes. Keep the SQLite file server-side; the public site reads through server components or read-only API routes. For Vercel deployment, generate a static catalog from SQLite during the build or use a persistent SQLite-compatible hosting setup; do not rely on writable ephemeral Vercel storage.

## Repository layout (suggested)
```
web/                     # Next.js website
worker/                  # Python ingestion and detection
  src/
    youtube_inventory.py
    transcript_provider.py
    transcript_pilot.py
    book_matching.py
  tests/
worker/migrations/          # SQLite SQL migrations
.env.example
README.md
agent.md
```

## Configuration
Document required variables in `.env.example`, without values: `YOUTUBE_API_KEY`, `DATABASE_PATH` (default `data/archive.db`); optional provider credentials only if a provider is adopted. Never expose server keys to the browser or commit secrets. Provide a dry-run mode and sample fixture data for local tests.

## CLI acceptance targets
- `python -m worker inventory --handle @jaredaball` discovers and upserts all accessible uploads into SQLite with pagination.
- `python -m worker transcript-pilot --sample-size 20` selects a reproducible sample, saves segments and statuses in SQLite, and prints coverage statistics.
- Both commands are safe to re-run, support useful logs, and fail with actionable errors.
- Unit tests cover pagination, empty/missing captions, timestamp preservation, idempotent upserts, and retry classification; use mocks/fixtures rather than live YouTube requests in CI.

## Working rules for Codex
- Inspect the existing repository before changing code; preserve its conventions and working features.
- Implement milestones sequentially; do not build the entire product in one unreviewed change.
- Prefer simple, testable modules and typed interfaces. Document dependencies and their versions.
- No unauthorized scraping, bypassing access controls, bulk audio downloading, or redistribution of full copyrighted transcripts. Keep public excerpts short and link to the source video.
- At the end of each milestone, report commands run, tests, number of videos/segments processed (if actually measured), limitations, and next steps. Never invent results.

## First task
Implement **Milestone 1** and the schema/CLI scaffolding required for **Milestone 2**. Do not add model-based extraction. After the inventory works, run the 10–20-video pilot and summarize transcript accessibility before proceeding.
