# YouTube Book Archive

Searchable archive of books mentioned in YouTube videos.

## Setup

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `YOUTUBE_API_KEY`, then run:

```sh
python -m worker inventory --handle @channelhandle
python -m worker transcript-pilot --sample-size 20
```
