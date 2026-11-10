import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ingest.__main__ import database, inventory, classify_error, exact_match, pilot, put

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=database(Path(self.tmp.name)/'archive.db')
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def video(self,id='abcdefghijk'):
        put(self.db,'videos',dict(video_id=id,channel_id='channel',title='Title',url='https://www.youtube.com/watch?v='+id),'video_id')
        self.db.commit()
    def test_inventory_pagination_and_idempotent_upserts(self):
        requests=[]
        def get(resource,params,key):
            requests.append((resource,params))
            if resource=='channels':return {'items':[{'id':'channel','contentDetails':{'relatedPlaylists':{'uploads':'uploads'}}}]}
            v='secondvideo' if params.get('pageToken') else 'firstvideo1'
            page={'items':[{'snippet':{'title':v,'publishedAt':'2024-01-01'},'contentDetails':{'videoId':v}}]}
            if not params.get('pageToken'):page['nextPageToken']='next'
            return page
        self.assertEqual(inventory(self.db,'@examplechannel',get,'test-key')['videos'],2)
        inventory(self.db,'@examplechannel',get,'test-key')
        self.assertEqual(self.db.execute('SELECT count(*) FROM videos').fetchone()[0],2)
        self.assertTrue(any(p.get('pageToken')=='next' for _,p in requests))
    def test_inventory_dry_run_does_not_write_videos(self):
        def get(resource,params,key):
            return {'items':[{'id':'ch','contentDetails':{'relatedPlaylists':{'uploads':'pl'}}}]} if resource=='channels' else {'items':[]}
        self.assertEqual(inventory(self.db,'@examplechannel',get,'key',True)['videos'],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM videos').fetchone()[0],0)
    def test_caption_timestamp_and_idempotent_storage(self):
        self.video()
        class Transcript:
            language_code='en';is_generated=True
            def to_raw_data(self):return [{'start':75.96,'duration':2.92,'text':'building the Black Arts Movement'}]
        pilot(self.db,1,fetch=lambda _:Transcript());pilot(self.db,1,fetch=lambda _:Transcript())
        row=self.db.execute('SELECT * FROM transcript_segments').fetchone()
        self.assertEqual(row['start_seconds'],75.96)
        self.assertEqual(row['duration_seconds'],2.92)
        self.assertEqual(self.db.execute('SELECT count(*) FROM transcript_segments').fetchone()[0],1)
    def test_no_transcript_is_recorded_without_segments(self):
        self.video()
        def fetch(_):raise type('NoTranscriptFound',(Exception,),{})()
        stats=pilot(self.db,1,fetch=fetch)
        self.assertEqual(stats['no_transcript'],1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM transcript_segments').fetchone()[0],0)
    def test_block_and_error_classification(self):
        for name,want in [('RequestBlocked','blocked'),('IpBlocked','blocked'),('VideoUnavailable','unavailable'),('TranscriptsDisabled','no_transcript'),('TimeoutError','error')]:
            self.assertEqual(classify_error(type(name,(Exception,),{})()),want)
    def test_exact_matching_respects_boundaries(self):
        self.assertTrue(exact_match('A book called “Stealing Empire.”','Stealing Empire'))
        self.assertFalse(exact_match('Stealing Empires','Stealing Empire'))
        self.assertTrue(exact_match('THE COLOR OF MONEY,','The Color of Money'))
    def test_reproducible_pilot(self):
        for i in range(15):self.video(f'video-{i:05}')
        a=pilot(self.db,10,dry_run=True);b=pilot(self.db,10,dry_run=True)
        self.assertEqual(a,b);self.assertEqual(len(set(a['sample'])),10)

if __name__=='__main__':unittest.main()
