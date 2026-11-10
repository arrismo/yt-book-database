# Reading Room repository instructions

- This repository contains the working private book archive for YouTube channels built for Sites.
- Keep the site owner-private. Do not change sharing or publish publicly without the user's explicit approval.
- Keep SQLite and deterministic title/author matching. Do not add Supabase, model-based extraction, embeddings, or generated evidence.
- The frontend uses TypeScript/React and Next-compatible Vinext. `worker/index.ts` is the Sites runtime worker; Python ingestion is in `ingest/`.
- Curated seed and exported catalog data live in `data/seed.json`, `data/catalog.json`, and `public/catalog.json`. Book records need verifiable sources; pending or rejected candidates must not be exported.
- Never infer endorsement from a mention. Distinguish caption excerpts, source show notes, and video titles; do not invent timestamps or bibliographic metadata.
- Keep full transcripts, local SQLite files, real environment values, credentials, caches, and build output out of Git and deployed assets.
- Preserve the project's identity in `.openai/hosting.json`. GitHub pushes alone do not deploy this site; Sites owns its saved versions and deployment.
- The initial catalog is a manually selected 10-video pilot, not a full-channel inventory. Full discovery requires `YOUTUBE_API_KEY` locally. Do not imply exhaustive coverage.
- Before editing, read `README.md`. Run the checks relevant to the change; the initial meaningful checks are:
  - `python -m unittest ingest.test_pipeline -v`
  - `node --experimental-strip-types --test tests/catalog.test.ts`
  - `node node_modules/typescript/bin/tsc --noEmit`
  - `python -m ingest build`
  - `npm run build`

- Keep the product branding channel-neutral. Use each video’s own channel ID for source links. Preserve truthful author, source, and quotation attribution in records. Require an explicit `--handle` for inventory; do not hardcode a creator as the default.
