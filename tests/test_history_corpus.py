"""Synthetic batch/caching/resume tests, with conservative real extraction logic."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from secstab.history_corpus import run
from secstab.history_inventory import sha


class HistoricalCorpusTests(unittest.TestCase):
    def setup_case(self,root):
        records=[{'document_id':f'0000000123-2{i}-000001','accession':f'0000000123-2{i}-000001','ticker':'TEST','cik':'0000000123',
            'source_url':f'https://www.sec.gov/Archives/edgar/data/123/source{i}.htm'} for i in range(3)]
        args=argparse.Namespace(inventory='synthetic',headers='synthetic',output=str(root/'output'),resume=False,cache_corpus=None,cache_root=str(root),cache_only=False,limit=None)
        raw=('<h2>ITEM 1A. RISK FACTORS</h2>'+'<p>Material operational risks include supplier and currency exposure.</p>'*110+'<h2>ITEM 1B. UNRESOLVED STAFF COMMENTS</h2>').encode()
        proof={'inventory_sha256':'synthetic_inventory','manifest_sha256':'synthetic_manifest'};calls=[]
        def fetch(url,ua):calls.append(url);return raw
        return args,records,proof,fetch,calls,raw

    def environment(self,proof,records):
        return patch('secstab.history_corpus.checked_sources',return_value=(proof,records,'synthetic_headers'))

    def test_full_batch_candidates_immutable_evidence_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,fetch,calls,_=self.setup_case(root)
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':'Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                run(args,fetcher=fetch)
                with self.assertRaises(FileExistsError):run(args,fetcher=fetch)
            m=json.loads((root/'output/manifest.json').read_text())
            self.assertEqual(m['extracted_candidates'],3);self.assertEqual(m['admitted_sections'],0);self.assertEqual(len(calls),3)
            for row in m['outcomes'].values():
                self.assertEqual(row['status'],'extracted_pending_review')
                self.assertEqual(sha(root/'output'/row['text']['path']),row['text']['sha256'])

    def test_network_failure_resumes_without_repeating_completed_download(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,fetch,calls,_=self.setup_case(root);attempts=[]
            def fail_once(url,ua):
                attempts.append(url)
                if len(attempts)==2:raise TimeoutError('synthetic network timeout')
                return fetch(url,ua)
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':'Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):run(args,fetcher=fail_once)
                args.resume=True;run(args,fetcher=fail_once)
            self.assertEqual(len(calls),3);self.assertEqual(attempts.count(attempts[0]),1)
            m=json.loads((root/'output/manifest.json').read_text());self.assertEqual(m['extracted_candidates'],3);self.assertEqual(len(m['failures']),1)

    def test_ambiguous_or_missing_section_is_flagged_and_batch_continues(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,fetch,calls,raw=self.setup_case(root)
            def variant(url,ua):calls.append(url);return b'<p>Risk factors incorporated elsewhere.</p>' if url==records[0]['source_url'] else raw
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':'Research contact@example.invalid'}),redirect_stdout(io.StringIO()):run(args,fetcher=variant)
            m=json.loads((root/'output/manifest.json').read_text())
            self.assertEqual(m['extraction_flags'],1);self.assertEqual(m['extracted_candidates'],2);self.assertEqual(m['sources_saved'],3)
            self.assertEqual(m['status'],'source_batch_finished_review_pending');self.assertEqual(m['admitted_sections'],0)

    def test_cache_only_makes_no_network_request_or_user_agent_requirement(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,_,_,raw=self.setup_case(root)
            cache=root/'cached.html';cache.write_bytes(raw);data={**records[0],'raw_path':'cached.html','raw_sha256':sha(cache)}
            cache_json=root/'cache.json';cache_json.write_text(json.dumps([data]));args.cache_corpus=str(cache_json);args.cache_only=True
            def forbidden(*a):raise AssertionError('Unexpected network request')
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':''}),redirect_stdout(io.StringIO()):run(args,fetcher=forbidden)
            m=json.loads((root/'output/manifest.json').read_text());self.assertEqual(m['extracted_candidates'],1);self.assertEqual(m['not_yet_processed'],2)
            self.assertEqual(next(iter(m['sources'].values()))['origin'],'hash_verified_existing_pilot_source')

    def test_changed_cached_source_fails_before_copy(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,_,_,raw=self.setup_case(root)
            cache=root/'cached.html';cache.write_bytes(raw);entry={**records[0],'raw_path':'cached.html','raw_sha256':sha(cache)}
            cache.write_bytes(raw+b'changed');source=root/'cache.json';source.write_text(json.dumps([entry]));args.cache_corpus=str(source);args.cache_only=True
            with self.environment(proof,records),redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError,'Cached source hash'):run(args,fetcher=lambda *a:None)

    def test_limit_checkpoint_and_saved_text_tampering_rejected_on_resume(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,fetch,calls,_=self.setup_case(root);args.limit=1
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':'Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                run(args,fetcher=fetch)
                m=json.loads((root/'output/manifest.json').read_text());self.assertEqual(m['not_yet_processed'],2)
                row=next(iter(m['outcomes'].values()));path=root/'output'/row['text']['path'];path.write_bytes(path.read_bytes()+b'changed')
                args.resume=True
                with self.assertRaisesRegex(ValueError,'extraction evidence changed'):run(args,fetcher=fetch)
            self.assertEqual(len(calls),1)

    def test_relative_output_path_is_resolved_before_source_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,records,proof,fetch,calls,_=self.setup_case(root)
            args.output=str(root/'nested/../relative_output')
            with self.environment(proof,records),patch.dict('os.environ',{'SEC_USER_AGENT':'Research contact@example.invalid'}),redirect_stdout(io.StringIO()):run(args,fetcher=fetch)
            self.assertTrue((root/'relative_output/manifest.json').is_file());self.assertEqual(len(calls),3)


if __name__=='__main__':unittest.main()
