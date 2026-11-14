"""Synthetic SEC pagination, provenance and failure-preservation tests only."""
import argparse
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from secstab.history_inventory import archive_overlaps,parse_page,merge_records,coverage_rows,collect


class HistoryInventoryTests(unittest.TestCase):
    def setUp(self):
        self.company={'ticker':'TEST','cik':'123','sector_pair':'synthetic'}
        self.proof={'metadata_path':'raw/0000000123/main.json','metadata_sha256':'synthetic','metadata_url':'https://data.sec.gov/submissions/CIK0000000123.json','source_scope':'main_recent'}
        self.table={'accessionNumber':['0000000123-26-000001','0000000123-26-000002','0000000123-20-000001'],
            'form':['10-K','10-K/A','10-K'],'filingDate':['2026-02-01','2026-03-01','2020-02-01'],
            'reportDate':['2025-12-31','2025-12-31','2019-12-31'],'primaryDocument':['test2026.htm','test2026a.htm','test2020.htm'],
            'acceptanceDateTime':['2026-02-01T21:00:00Z','2026-03-01T21:00:00Z','2020-02-01T21:00:00Z']}
    def parse(self,table=None):
        return parse_page(self.table if table is None else table,self.company,'Synthetic Inc','2015-01-01','2026-11-02',self.proof)

    def fixture(self,root):
        universe=root/'universe.json';universe.write_text(json.dumps({'companies':[self.company]}))
        config=root/'config.json';config.write_text(json.dumps({'universe_path':str(universe),'filing_start_inclusive':'2015-01-01',
            'filing_end_inclusive':'2026-11-02','form':'10-K','scope':'synthetic metadata only','timestamp_policy':'unverified API values'}))
        archive=copy.deepcopy(self.table)
        archive.update(accessionNumber=['0000000123-20-000001','0000000123-15-000001','0000000123-14-000001'],
            form=['10-K']*3,filingDate=['2020-02-01','2015-01-01','2014-01-01'],reportDate=['2019-12-31','2014-12-31','2013-12-31'],
            primaryDocument=['test2020.htm','test2015.htm','test2014.htm'])
        archive.pop('acceptanceDateTime')
        main={'cik':123,'name':'Synthetic Inc','filings':{'recent':self.table,'files':[
            {'name':'CIK0000000123-submissions-001.json','filingFrom':'2014-01-01','filingTo':'2020-02-01'},
            {'name':'CIK0000000123-submissions-002.json','filingFrom':'1994-01-01','filingTo':'2014-12-31'}]}}
        calls=[]
        def fetch(url,ua):
            calls.append((url,ua))
            return json.dumps(archive if url.endswith('-001.json') else main).encode()
        args=argparse.Namespace(config=str(config),output=str(root/'output'))
        return args,fetch,calls,main

    def test_originals_only_and_api_clock_not_promoted(self):
        rows=self.parse();self.assertEqual(len(rows),2)
        self.assertTrue(all(r['review_status']=='inventory_only_not_admitted' for r in rows))
        self.assertNotIn('accepted_at',rows[0]);self.assertIn('accepted_at_api',rows[0])
        self.assertIn('/000000012326000001/test2026.htm',rows[0]['source_url'])

    def test_missing_optional_fields_are_pending_not_invented(self):
        table={k:v for k,v in self.table.items() if k in ['accessionNumber','form','filingDate']}
        row=self.parse(table)[0]
        self.assertIsNone(row['accepted_at_api']);self.assertIsNone(row['source_url'])
        self.assertEqual(row['timestamp_status'],'missing_pending_header_review')

    def test_array_misalignment_rejected(self):
        for key in ['filingDate','acceptanceDateTime']:
            table=copy.deepcopy(self.table);table[key]=table[key][:1]
            with self.assertRaisesRegex(ValueError,'Misaligned'):self.parse(table)

    def test_archive_bounds_include_overlap_and_fetch_unknown(self):
        entry={'name':'CIK0000000123-submissions-001.json','filingFrom':'2010-01-01','filingTo':'2015-01-01'}
        self.assertTrue(archive_overlaps(entry,'0000000123','2015-01-01','2026-11-02'))
        entry['filingTo']='2014-12-31';self.assertFalse(archive_overlaps(entry,'0000000123','2015-01-01','2026-11-02'))
        entry.pop('filingFrom');self.assertTrue(archive_overlaps(entry,'0000000123','2015-01-01','2026-11-02'))

    def test_untrusted_paths_and_cross_cik_links_rejected(self):
        for name in ['../archive.json','CIK0000000999-submissions-001.json','https://example.invalid/file.json']:
            with self.assertRaisesRegex(ValueError,'archive name'):archive_overlaps({'name':name},'0000000123','2015-01-01','2026-11-02')
        table=copy.deepcopy(self.table);table['primaryDocument'][0]='../filing.htm'
        with self.assertRaisesRegex(ValueError,'filename'):self.parse(table)

    def test_dedup_retains_evidence_and_merges_missing_fields(self):
        a=self.parse()[0];b=copy.deepcopy(a);b['metadata_evidence']=[{'source_scope':'archive'}];b['accepted_at_api']=None
        row=merge_records([a,b])[0]
        self.assertEqual(len(row['metadata_evidence']),2);self.assertEqual(row['accepted_at_api'],a['accepted_at_api'])

    def test_conflicting_duplicate_identity_fails_closed(self):
        a=self.parse()[0];b=copy.deepcopy(a);b['filing_date']='2026-02-02'
        with self.assertRaisesRegex(ValueError,'Conflicting duplicate'):merge_records([a,b])

    def test_conflicting_timestamps_stay_flagged_after_further_duplicates(self):
        a=self.parse()[0];b=copy.deepcopy(a);b['accepted_at_api']='2026-02-01T16:00:00Z'
        c=copy.deepcopy(a);c['accepted_at_api']=None
        row=merge_records([a,b,c])[0]
        self.assertIsNone(row['accepted_at_api']);self.assertEqual(len(row['conflicting_api_timestamps']),2)
        self.assertEqual(row['timestamp_status'],'conflict_pending_header_review')

    def test_full_mocked_collection_follows_archives_hashes_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,calls,_=self.fixture(root)
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                collect(args,fetcher=fetch)
                before=(root/'output/manifest.json').read_bytes()
                with self.assertRaises(FileExistsError):collect(args,fetcher=fetch)
            manifest=json.loads(before);rows=json.loads((root/'output/filings_inventory.json').read_text())
            self.assertEqual(manifest['original_10k_records'],3);self.assertEqual(manifest['missing_api_acceptance_values'],1)
            self.assertEqual(len(calls),2);self.assertEqual(len(manifest['skipped_archives']),1)
            self.assertEqual(manifest['zero_filing_calendar_year_cells'],9)
            self.assertEqual((root/'output/manifest.json').read_bytes(),before)
            for name,record in manifest['source_files'].items():
                self.assertEqual(hashlib.sha256((root/'output'/name).read_bytes()).hexdigest(),record['sha256'])
            for name,digest in manifest['outputs'].items():
                self.assertEqual(hashlib.sha256((root/'output'/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(len(next(r for r in rows if r['filing_date']=='2020-02-01')['metadata_evidence']),2)
            self.assertFalse(manifest['text_downloaded']);self.assertFalse(manifest['financial_evaluation_run'])

    def test_network_failure_retains_partial_raw_and_failed_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,_,_=self.fixture(root)
            def failure(url,ua):
                if url.endswith('-001.json'):raise TimeoutError('synthetic failure')
                return fetch(url,ua)
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):collect(args,fetcher=failure)
            manifest=json.loads((root/'output/manifest.json').read_text())
            self.assertEqual(manifest['status'],'failed_partial_collection_preserved')
            self.assertEqual(len(manifest['source_files']),1)
            self.assertTrue((root/'output/raw/0000000123/CIK0000000123.json').exists())

    def test_missing_user_agent_rejected_before_directory_creation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,_,_=self.fixture(root)
            with patch.dict('os.environ',{'SEC_USER_AGENT':''}):
                with self.assertRaisesRegex(ValueError,'SEC_USER_AGENT'):collect(args,fetcher=fetch)
            self.assertFalse((root/'output').exists())

    def test_coverage_multiple_originals_is_review_flag_not_fiscal_claim(self):
        rows=self.parse();extra=copy.deepcopy(rows[0]);extra['accession']='0000000123-26-000003'
        coverage=coverage_rows(rows+[extra],[self.company],'2026-01-01','2026-11-02')
        self.assertEqual(coverage[0]['original_10k_count'],2)
        self.assertEqual(coverage[0]['coverage_flag'],'multiple_originals_review_needed')


if __name__=='__main__':unittest.main()
