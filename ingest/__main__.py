"""No models, hosted database, scraping workarounds, or credentials in the site.

python -m ingest --help
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NOW = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def database(path=None):
    p = Path(path or os.getenv('DATABASE_PATH', ROOT / 'data/archive.db'))
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p)
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / 'ingest/migrations/001_initial.sql').read_text())
    return db

def put(db, table, record, key):
    cols = list(record)
    update = ','.join(f'{c}=excluded.{c}' for c in cols if c != key)
    db.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT({key}) DO UPDATE SET {update}", list(record.values()))

def seed(db):
    data = json.loads((ROOT / 'data/seed.json').read_text())
    for v in data['videos']: put(db, 'videos', v, 'video_id')
    for b in data['books']:
        b = dict(b)
        b['aliases_json'] = json.dumps(b.pop('aliases', []))
        put(db, 'books', b, 'id')
    for m in data['mentions']: put(db, 'mentions', m, 'id')
    for a in data['attempts']:
        if not db.execute('SELECT 1 FROM transcript_attempts WHERE video_id=? AND attempted_at=?', (a['video_id'], a['attempted_at'])).fetchone():
            db.execute('INSERT INTO transcript_attempts(video_id,provider,status,error_code,attempted_at) VALUES(:video_id,:provider,:status,:error_code,:attempted_at)', a)
    db.execute("INSERT INTO settings VALUES('bootstrap',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(data['coverage']),))
    db.commit()

def api_get(resource, params, key):
    url = 'https://www.googleapis.com/youtube/v3/' + resource + '?' + urllib.parse.urlencode(dict(params, key=key))
    # Never print the URL: it contains the API key.
    with urllib.request.urlopen(url, timeout=25) as r: return json.load(r)

def inventory(db, handle, get=api_get, api_key=None, dry_run=False):
    key = api_key or os.getenv('YOUTUBE_API_KEY')
    if not key: raise RuntimeError('Set YOUTUBE_API_KEY locally to inventory uploads with the official YouTube Data API. No key is needed to browse the deployed catalog.')
    response = get('channels', {'part':'contentDetails','forHandle':handle.lstrip('@')}, key)
    if not response.get('items'): raise RuntimeError('YouTube channel not found for this handle.')
    channel = response['items'][0]
    playlist = channel['contentDetails']['relatedPlaylists']['uploads']
    count, token, pages = 0, None, 0
    while True:
        params = {'part':'snippet,contentDetails','playlistId':playlist,'maxResults':50}
        if token: params['pageToken'] = token
        page = get('playlistItems', params, key)
        for item in page.get('items', []):
            snip = item['snippet']; video_id = item['contentDetails']['videoId']
            if not dry_run:
                put(db, 'videos', {'video_id':video_id,'channel_id':channel['id'],'title':snip['title'],'description':snip.get('description',''),'published_at':item['contentDetails'].get('videoPublishedAt',snip.get('publishedAt')),'url':f'https://www.youtube.com/watch?v={video_id}','updated_at':NOW()}, 'video_id')
            count += 1
        db.commit() # Each completed page is durable; reruns safely upsert.
        pages += 1; token = page.get('nextPageToken')
        if not token: break
    stats = {'videos':count,'pages':pages,'dry_run':dry_run}
    if not dry_run:
        db.execute("INSERT INTO settings VALUES('inventory',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(dict(stats,completed_at=NOW(),handle=handle)),));db.commit()
    return stats

def normalize(text):
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower()).split())

def exact_match(text, alias):
    return (' ' + normalize(alias) + ' ') in (' ' + normalize(text) + ' ')

def classify_error(error):
    name = type(error).__name__
    if name in ('RequestBlocked','IpBlocked','PoTokenRequired','AgeRestricted'): return 'blocked'
    if name in ('TranscriptsDisabled','NoTranscriptFound'): return 'no_transcript'
    if name in ('VideoUnavailable','VideoUnplayable','InvalidVideoId'): return 'unavailable'
    return 'error'

def pilot(db, count=10, fetch=None, dry_run=False):
    # Stable, spread-out sample by upload date (or primary-source date if unknown).
    videos = list(db.execute('SELECT * FROM videos ORDER BY COALESCE(published_at,source_date),video_id'))
    if not videos: raise RuntimeError('No videos. Seed the starter catalog or run inventory first.')
    n = min(count, len(videos))
    selected = [videos[round(i*(len(videos)-1)/max(1,n-1))] for i in range(n)]
    if dry_run: return {'sample':[v['video_id'] for v in selected],'dry_run':True}
    if fetch is None:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetch = YouTubeTranscriptApi().fetch
    stats = {'sample':[v['video_id'] for v in selected], 'available':0,'blocked':0,'no_transcript':0,'unavailable':0,'error':0}
    for i,v in enumerate(selected):
        error_code = None
        try:
            result = fetch(v['video_id'])
            for s in result.to_raw_data():
                db.execute('INSERT INTO transcript_segments(video_id,start_seconds,duration_seconds,text,language,source,is_generated) VALUES(?,?,?,?,?,?,?) ON CONFLICT(video_id,source,language,start_seconds) DO UPDATE SET text=excluded.text,duration_seconds=excluded.duration_seconds', (v['video_id'],s['start'],s['duration'],s['text'],result.language_code,'youtube-transcript-api',result.is_generated))
            status = 'available'
        except Exception as error:
            status = classify_error(error);error_code=type(error).__name__
        stats[status] += 1
        db.execute('INSERT INTO transcript_attempts(video_id,provider,status,error_code,attempted_at) VALUES(?,?,?,?,?)',(v['video_id'],'youtube-transcript-api',status,error_code,NOW()));db.commit()
        print(v['video_id'], status, file=sys.stderr)
        if i+1<n: time.sleep(1) # No automatic bypasses or aggressive retries.
    return stats

def match(db):
    count=0
    for b in db.execute('SELECT * FROM books').fetchall():
        aliases=json.loads(b['aliases_json']) or [b['title']]
        for v in db.execute('SELECT video_id FROM videos').fetchall():
            segs=db.execute('SELECT * FROM transcript_segments WHERE video_id=? ORDER BY start_seconds',(v['video_id'],)).fetchall()
            for i,s in enumerate(segs):
                excerpt=' '.join(x['text'] for x in segs[i:i+4])
                if any(exact_match(excerpt,a) for a in aliases):
                    mid=hashlib.sha256(f"{b['id']}|{v['video_id']}|{s['start_seconds']}".encode()).hexdigest()[:20]
                    # Candidates stay pending; a human must establish book context.
                    db.execute("INSERT OR IGNORE INTO mentions(id,book_id,video_id,start_seconds,evidence_excerpt,evidence_type,classification,confidence,review_status,extraction_method,note) VALUES(?,?,?,?,?,'transcript','unclear',1,'pending','exact_alias','Requires manual context review; exact lexical match is not a recommendation.')",(mid,b['id'],v['video_id'],s['start_seconds'],excerpt[:260]))
                    count+=1;break
    db.commit();return {'candidate_matches':count,'publication':'pending manual review'}

def export(db):
    bootstrap=json.loads(db.execute("SELECT value FROM settings WHERE key='bootstrap'").fetchone()[0])
    inv=db.execute("SELECT value FROM settings WHERE key='inventory'").fetchone()
    bootstrap['inventory'] = json.loads(inv[0]) if inv else None
    books=[]
    for b in db.execute("SELECT * FROM books WHERE id IN (SELECT book_id FROM mentions WHERE review_status='confirmed') ORDER BY title"):
        book=dict(b);book.pop('aliases_json');books.append(book)
    videos=[]
    for v in db.execute('SELECT * FROM videos ORDER BY COALESCE(published_at,source_date) DESC'):
        video=dict(v)
        a=db.execute('SELECT status,provider,error_code,attempted_at FROM transcript_attempts WHERE video_id=? ORDER BY attempted_at DESC,id DESC LIMIT 1',(v['video_id'],)).fetchone()
        video['transcript']=dict(a) if a else {'status':'not_tested'};videos.append(video)
    mentions=[dict(m) for m in db.execute("SELECT * FROM mentions WHERE review_status='confirmed' ORDER BY start_seconds")]
    data={'books':books,'videos':videos,'mentions':mentions,'coverage':bootstrap}
    (ROOT/'data/catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'public/catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return {'books':len(books),'videos':len(videos),'mentions':len(mentions),'transcripts_available':sum(v['transcript']['status']=='available' for v in videos)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('seed','match','export','build'):sub.add_parser(name)
    q=sub.add_parser('inventory');q.add_argument('--handle',required=True,help='YouTube channel handle, for example @yourchannel');q.add_argument('--dry-run',action='store_true')
    q=sub.add_parser('transcript-pilot');q.add_argument('--sample-size',type=int,default=10);q.add_argument('--dry-run',action='store_true')
    args=p.parse_args();db=database(args.database);start=NOW()
    try:
        if args.command=='seed':seed(db);stats={'seeded':True}
        elif args.command=='build':
            if not db.execute('SELECT 1 FROM books LIMIT 1').fetchone():seed(db)
            stats=export(db)
        elif args.command=='export':stats=export(db)
        elif args.command=='match':stats=match(db)
        elif args.command=='inventory':stats=inventory(db,args.handle,dry_run=args.dry_run)
        else:
            if not 1<=args.sample_size<=20:raise RuntimeError('Use a sample size between 1 and 20.')
            stats=pilot(db,args.sample_size,dry_run=args.dry_run)
        db.execute('INSERT INTO ingestion_runs(run_type,started_at,finished_at,status,stats_json) VALUES(?,?,?,?,?)',(args.command,start,NOW(),'completed',json.dumps(stats)));db.commit();print(json.dumps(stats,indent=2))
    except Exception as error:
        # Avoid propagating HTTP error URLs containing a secret API key.
        message=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        db.execute('INSERT INTO ingestion_runs(run_type,started_at,finished_at,status,error_summary) VALUES(?,?,?,?,?)',(args.command,start,NOW(),'failed',message));db.commit()
        print(message,file=sys.stderr);sys.exit(1)

if __name__=='__main__':main()
