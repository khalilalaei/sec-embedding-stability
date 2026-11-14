"""Frozen inventory replay and synthetic SEC-header evidence/resume tests."""
import argparse
from contextlib import redirect_stdout
import copy
import html
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_history_inventory as fixtures
from secstab.history_inventory import collect,sha
from secstab.history_audit import audit_inventory
from secstab.history_headers import parse_header,collect_headers


def inventory_fixture(root):
    f=fixtures.HistoryInventoryTests();f.setUp();args,fetch,_,_=f.fixture(root)
    with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):collect(args,fetcher=fetch)
    return Path(args.output),Path(args.config)


def synthetic_header(record,clock='20260201160000'):
    period=(record.get('report_date') or '2025-12-31').replace('-','')
    return (f'<SEC-HEADER>synthetic.hdr.sgml\n<ACCEPTANCE-DATETIME>{clock}\n'
        f'ACCESSION NUMBER: {record["accession"]}\nCONFORMED SUBMISSION TYPE: {record["form"]}\n'
        f'CONFORMED PERIOD OF REPORT: {period}\nFILED AS OF DATE: {record["filing_date"].replace("-", "")}\n'
        f'CENTRAL INDEX KEY: {record["cik"]}\n</SEC-HEADER>').encode()


def tagged_header(record,clock='20260201160000'):
    period=(record.get('report_date') or '2025-12-31').replace('-','')
    return (f'<SEC-HEADER>synthetic.hdr.sgml\n<ACCEPTANCE-DATETIME>{clock}\n'
        f'<ACCESSION-NUMBER>{record["accession"]}\n<TYPE>{record["form"]}\n'
        f'<PERIOD>{period}\n<FILING-DATE>{record["filing_date"].replace("-", "")}\n'
        f'<FILER><COMPANY-DATA><CIK>{record["cik"]}\n</COMPANY-DATA></FILER>\n</SEC-HEADER>').encode()


def dual_header(record,clock='20260201160000',visible_clock='20260201160000'):
    return b'<html><head><!--'+tagged_header(record,clock)+b'--></head><body><pre>'+html.escape(synthetic_header(record,visible_clock).decode()).encode()+b'</pre></body></html>'


class InventoryAuditTests(unittest.TestCase):
    def test_valid_replay_and_cross_platform_reference_json(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);inventory,config=inventory_fixture(root)
            data=json.loads(config.read_text());reference=root/'reference.json'
            reference.write_bytes(json.dumps(data,indent=4).replace('\n','\r\n').encode())
            receipt,records=audit_inventory(inventory,reference_config=reference)
            self.assertEqual(receipt['original_10k_records'],3);self.assertEqual(receipt['source_files_checked'],2)
            self.assertTrue(all(r['review_status']=='inventory_only_not_admitted' for r in records))
            data['scope']='different choice';reference.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'choices differ'):audit_inventory(inventory,reference_config=reference)

    def test_changed_source_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            inventory,_=inventory_fixture(Path(t));path=next((inventory/'raw').rglob('CIK0000000123.json'))
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'Source hash'):audit_inventory(inventory)

    def test_rehashed_forged_inventory_row_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            inventory,_=inventory_fixture(Path(t));path=inventory/'filings_inventory.json';rows=json.loads(path.read_text())
            rows[0]['filing_date']='2015-01-02';path.write_text(json.dumps(rows))
            manifest=json.loads((inventory/'manifest.json').read_text());manifest['outputs']['filings_inventory.json']=sha(path)
            (inventory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'does not reproduce'):audit_inventory(inventory)

    def test_rehashed_forged_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            inventory,_=inventory_fixture(Path(t));path=inventory/'coverage.csv';path.write_text(path.read_text().replace('one_original_observed','invented_approval'))
            manifest=json.loads((inventory/'manifest.json').read_text());manifest['outputs']['coverage.csv']=sha(path)
            (inventory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Coverage table'):audit_inventory(inventory)

    def test_incomplete_archive_receipt_set_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            inventory,_=inventory_fixture(Path(t));manifest=json.loads((inventory/'manifest.json').read_text())
            del manifest['source_files']['raw/0000000123/CIK0000000123-submissions-001.json']
            (inventory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'archive coverage'):audit_inventory(inventory)


class HistoryHeaderTests(unittest.TestCase):
    def record(self):
        f=fixtures.HistoryInventoryTests();f.setUp();return f.parse()[0]

    def test_raw_and_html_escaped_clock_preserved_without_eligibility(self):
        record=self.record();raw=synthetic_header(record)
        parsed=parse_header(raw,record);escaped=parse_header(html.escape(raw.decode()).encode(),record)
        self.assertEqual(parsed,escaped);self.assertEqual(parsed['acceptance_clock_unzoned'],'20260201160000')
        self.assertNotIn('eligible_from',parsed);self.assertNotIn('accepted_at',parsed)
        self.assertEqual(parsed['review_status'],'header_identity_fields_matched_not_availability_approved')

    def test_tag_style_fields_are_supported(self):
        parsed=parse_header(tagged_header(self.record()),self.record())
        self.assertEqual(parsed['header_field_formats'],['tag_fields'])
        self.assertEqual(parsed['source_header_block_count'],1)
        self.assertEqual(parsed['acceptance_clock_unzoned'],'20260201160000')

    def test_comment_tag_copy_and_visible_colon_copy_must_agree(self):
        parsed=parse_header(dual_header(self.record()),self.record())
        self.assertEqual(parsed['source_header_block_count'],2)
        self.assertEqual(parsed['header_field_formats'],['colon_fields','tag_fields'])
        self.assertTrue(parsed['header_copies_consistent'])
        self.assertEqual(parsed['document_id'],self.record()['accession'])

    def test_conflicting_header_clocks_rejected(self):
        with self.assertRaisesRegex(ValueError,'Conflicting SEC-HEADER copies'):
            parse_header(dual_header(self.record(),visible_clock='20260201170000'),self.record())

    def test_tagged_identity_checks_not_bypassed_by_matching_visible_copy(self):
        record=self.record();changed=copy.deepcopy(record);changed['cik']='0000000999'
        response=b'<!--'+tagged_header(changed)+b'--><pre>'+html.escape(synthetic_header(record).decode()).encode()+b'</pre>'
        with self.assertRaisesRegex(ValueError,'CIK differs'):parse_header(response,record)

    def test_parser_failure_reuses_saved_header_after_repair(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,_,_=self.setup_collection(root)
            _,records=audit_inventory(args.inventory);mapping={r['filing_header_url']:r for r in records};calls=[]
            def fetch(url,ua):calls.append(url);return dual_header(mapping[url])
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                with patch('secstab.history_headers.parse_header',side_effect=ValueError('original colon-only parser failure')):
                    with self.assertRaisesRegex(ValueError,'colon-only'):collect_headers(args,fetcher=fetch)
                manifest=json.loads((root/'headers/manifest.json').read_text())
                self.assertEqual(manifest['completed_records'],0);self.assertEqual(len(manifest['source_files']),1)
                name=next(iter(manifest['source_files']));before=(root/'headers'/name).read_bytes()
                args.resume=True;collect_headers(args,fetcher=fetch)
            self.assertEqual(len(calls),3);self.assertEqual(calls.count(calls[0]),1)
            self.assertEqual((root/'headers'/name).read_bytes(),before)
            final=json.loads((root/'headers/manifest.json').read_text())
            self.assertEqual(final['header_count'],3);self.assertEqual(len(final['failures']),1)

    def test_header_identity_and_period_mismatches_rejected(self):
        record=self.record()
        for key,value in [('accession','0000000999-26-000001'),('cik','0000000999'),('form','10-Q'),('report_date','2024-12-31'),('filing_date','2026-02-02')]:
            changed=copy.deepcopy(record);changed[key]=value
            with self.assertRaises(ValueError):parse_header(synthetic_header(changed),record)

    def test_invalid_clock_or_non_header_response_rejected(self):
        record=self.record()
        with self.assertRaises(ValueError):parse_header(synthetic_header(record,'20261301160000'),record)
        with self.assertRaisesRegex(ValueError,'no SEC-HEADER'):parse_header(b'<html>Access denied</html>',record)

    def setup_collection(self,root):
        inventory,_=inventory_fixture(root);_,records=audit_inventory(inventory)
        args=argparse.Namespace(inventory=str(inventory),output=str(root/'headers'),resume=False,reference_config=None,reference_universe=None)
        mapping={r['filing_header_url']:r for r in records};calls=[]
        def fetch(url,ua):calls.append(url);return synthetic_header(mapping[url])
        return args,fetch,calls

    def test_complete_collection_cached_resume_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,calls=self.setup_collection(root)
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                collect_headers(args,fetcher=fetch)
                self.assertEqual(len(calls),3)
                with self.assertRaises(FileExistsError):collect_headers(args,fetcher=fetch)
                before=(root/'headers/manifest.json').read_bytes()
                args.resume=True;collect_headers(args,fetcher=fetch)
                self.assertEqual((root/'headers/manifest.json').read_bytes(),before)
            self.assertEqual(len(calls),3)
            manifest=json.loads((root/'headers/manifest.json').read_text())
            self.assertEqual(manifest['header_count'],3)
            self.assertEqual(manifest['status'],'headers_collected_identity_matched_timing_review_pending')
            for name,entry in manifest['source_files'].items():self.assertEqual(sha(root/'headers'/name),entry['sha256'])

    def test_partial_network_failure_resumes_without_redownloading_successes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,calls=self.setup_collection(root);attempts=[]
            def fail_once(url,ua):
                attempts.append(url)
                if len(attempts)==2:raise TimeoutError('synthetic connection failure')
                return fetch(url,ua)
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):collect_headers(args,fetcher=fail_once)
                failed=json.loads((root/'headers/manifest.json').read_text())
                self.assertEqual(failed['completed_records'],1)
                self.assertEqual(failed['status'],'failed_partial_headers_preserved')
                args.resume=True;collect_headers(args,fetcher=fail_once)
            self.assertEqual(len(attempts),4);self.assertEqual(len(calls),3)
            self.assertEqual(attempts.count(attempts[0]),1)

    def test_tampered_recorded_header_rejected_before_resume_request(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args,fetch,calls=self.setup_collection(root)
            with patch.dict('os.environ',{'SEC_USER_AGENT':'Synthetic Research contact@example.invalid'}),redirect_stdout(io.StringIO()):
                collect_headers(args,fetcher=fetch)
                path=next((root/'headers/headers').rglob('*.html'));path.write_bytes(path.read_bytes()+b' ')
                args.resume=True
                with self.assertRaisesRegex(ValueError,'changed'):collect_headers(args,fetcher=fetch)
            self.assertEqual(len(calls),3)


if __name__=='__main__':unittest.main()
