# Reading Room — Jared A. Ball book archive

Private catalog built with Next-compatible TypeScript/React (Vinext on Sites), a Python ingestion CLI, and local SQLite. No Supabase, models, embeddings, or generative extraction.

## First usable version

- 11 real books; 14 manually reviewed references; 10 source videos verified against `@jaredaball` via YouTube oEmbed.
- 10/10 selected transcripts retrieved with `youtube-transcript-api==1.2.4`; 22,828 segments processed during the November 9, 2026 pilot.
- Browse, search across titles/authors/evidence/video titles, filter subjects and evidence types, sort, switch grid/list, open a deep-linked book record, follow timestamped video links, export the catalog, and save books to a browser-local reading shelf.
- Covers and work metadata from Open Library. Ball's own book page corrects the catalog's misspelled “Jared Bell” author for *I Mix What I Like!*. Unverified publication years remain null. ISBN identifies a catalog edition; it may differ from the cover edition.
- Full-channel inventory was **not** run: no `YOUTUBE_API_KEY` was available. This is a transparent, manually selected pilot, not an exhaustive archive or a representative coverage estimate.
- Manual seed sources are Ball's public website, linked YouTube video titles, accessible captions, and Open Library. All seed videos are on `@jaredaball`. Source-page dates are kept distinct from video publication dates, which are unknown for the seed.
- The site does not infer endorsement. Exact lexical matches require context review. Jingle-only references and unrelated short-title matches were excluded.

## Run locally

```bash
npm ci
python -m pip install -r requirements.txt
python -m ingest seed
python -m ingest export
npm run dev
```

Use `sites-preview start <checkout>` for the managed Sites preview. Do not launch a second server there.

## Ingestion workflow

```bash
# Set a local server-side API key; never add it to browser code or Git.
export YOUTUBE_API_KEY='<your key>'
python -m ingest inventory --handle @jaredaball --dry-run
python -m ingest inventory --handle @jaredaball
python -m ingest transcript-pilot --sample-size 10 --dry-run
python -m ingest transcript-pilot --sample-size 10
python -m ingest match
```

`inventory` uses the official YouTube Data API, resolves the handle, traverses the uploads playlist, commits each page, and safely upserts on rerun. A missing API key gives an actionable message. The pilot uses a reproducible date-spread sample and saves all selected IDs and measured statuses to `ingestion_runs`. It makes one modest attempt per video, records blocked/missing/unavailable/error separately, and performs no proxy or authentication workaround. Review eligible transient failures before rerunning; it does not aggressively retry them.

`match` uses normalized exact aliases across adjacent caption segments. It writes **pending** candidates. It never automatically publishes or classifies a recommendation. Review context before marking a candidate `confirmed` in SQLite. Rejected and pending candidates are excluded by `export`. `data/seed.json` contains the initial curated, reviewed records, bibliographic metadata, short excerpts, and measured pilot attempts.

```bash
python -m ingest export  # SQLite -> data/catalog.json and public/catalog.json
python -m ingest build   # Seeds if DB is absent, then exports
```

SQLite (`data/archive.db`) stays local and is ignored by Git. Retrieved full segments and raw transcripts are never shipped in the deployment. Only short reviewed excerpts and metadata are exported. Source-controlled seed and catalog files reproduce this first collection. To retain future manual reviews across environments, update the curated seed/export before synchronizing source.

## Validate and build

```bash
python -m unittest ingest.test_pipeline -v
node --experimental-strip-types --test tests/catalog.test.ts
node node_modules/typescript/bin/tsc --noEmit
python -m ingest build
npm run build
```

Tests cover inventory pagination/idempotence, missing captions, error classification, reproducible samples, preserved timestamps, deterministic title boundaries, search/filter combinations, source relationships, timestamp URLs, sorting, and honest pilot counts. Browser QA covers the live interactions, shelf persistence, modal/deep links, and source coverage.

## Deployment and access

Sites owns source synchronization, saved versions, and deployment. `.openai/hosting.json` retains this project's opaque ID. D1 and R2 are unused. The deployed application serves an exported read-only catalog; no writable hosted database is needed.

Use owner-private deployment only. Do not change sharing or publish publicly without the user's approval. Search-engine metadata also sets noindex, but access privacy is enforced by Sites, not by robots metadata.

The reading shelf uses localStorage; it persists per browser and origin and does not sync across devices. The prototype has no remote editing UI or scheduled ingestion.
