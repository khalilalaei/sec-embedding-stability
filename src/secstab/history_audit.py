"""Offline lineage and pagination audit of a frozen historical SEC inventory."""
import argparse
import csv
import json
from pathlib import Path
from .history_inventory import sha,parse_page,merge_records,coverage_rows,archive_overlaps


def safe_path(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Inventory path leaves collection directory')
    return path


def audit_inventory(root,reference_config=None,reference_universe=None):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text())
    if manifest['status']!='metadata_collection_complete_pending_source_review':raise ValueError('Incomplete inventory collection')
    for name,record in manifest['source_files'].items():
        if sha(safe_path(root,name))!=record['sha256']:raise ValueError('Source hash mismatch: '+name)
    for name,digest in manifest['outputs'].items():
        if sha(safe_path(root,name))!=digest:raise ValueError('Output hash mismatch: '+name)
    if set(manifest['outputs'])!={'filings_inventory.json','coverage.csv','config_snapshot.json','universe_snapshot.json'}:raise ValueError('Missing/extra inventory output receipts')
    config=json.loads((root/'config_snapshot.json').read_text());universe=json.loads((root/'universe_snapshot.json').read_text())
    # Snapshots are reserialized JSON values, not copies of original input bytes.
    # Their own exact hashes were verified through outputs above.
    # Original input byte hashes are preserved as reported; reference choices
    # are verified semantically below to allow formatting and LF/CRLF differences.
    # Git for Windows can change LF/CRLF bytes without changing JSON choices.
    # Uploaded bytes still require their exact recorded hashes above.
    for path,expected in [(reference_config,config),(reference_universe,universe)]:
        if path is not None and json.loads(Path(path).read_text(encoding='utf-8-sig'))!=expected:
            raise ValueError('Reference configuration/universe choices differ')
    start,end=config['filing_start_inclusive'],config['filing_end_inclusive']
    if (start,end)!=(manifest['filing_start_inclusive'],manifest['filing_end_inclusive']):raise ValueError('Manifest date interval differs')
    if config['form']!='10-K':raise ValueError('Unexpected filing-form policy')
    companies=universe['companies'];expected_sources={};expected_skips=[];rebuilt=[];counts=[]
    for company in companies:
        cik=str(company['cik']).zfill(10);main_name=f'raw/{cik}/CIK{cik}.json'
        main_path=safe_path(root,main_name);main=json.loads(main_path.read_text())
        if str(main['cik']).zfill(10)!=cik:raise ValueError('Main-page CIK mismatch')
        main_url=f'https://data.sec.gov/submissions/CIK{cik}.json';expected_sources[main_name]=main_url
        proof={'metadata_path':main_name,'metadata_sha256':sha(main_path),'metadata_url':main_url,'source_scope':'main_recent'}
        records=parse_page(main['filings']['recent'],company,main['name'],start,end,proof)
        linked=set()
        for entry in main['filings'].get('files',[]):
            relevant=archive_overlaps(entry,cik,start,end)
            if entry['name'] in linked:raise ValueError('Duplicate archive link')
            linked.add(entry['name'])
            if not relevant:
                expected_skips.append({'cik':cik,**entry,'reason':'advertised_date_range_outside_request'});continue
            name=f'raw/{cik}/'+entry['name'];url='https://data.sec.gov/submissions/'+entry['name']
            expected_sources[name]=url
            path=safe_path(root,name);page=json.loads(path.read_text())
            records.extend(parse_page(page,company,main['name'],start,end,{'metadata_path':name,'metadata_sha256':sha(path),
                'metadata_url':url,'source_scope':'linked_historical_page','parent_metadata_path':main_name,'parent_metadata_sha256':sha(main_path)}))
        records=merge_records(records);rebuilt.extend(records)
        counts.append({'ticker':company['ticker'],'cik':cik,'original_10k_count':len(records)})
    if set(expected_sources)!=set(manifest['source_files']):raise ValueError('Requested archive coverage differs from saved source set')
    for name,url in expected_sources.items():
        if manifest['source_files'][name]['url']!=url:raise ValueError('Recorded metadata URL differs from parent link')
    if expected_skips!=manifest['skipped_archives']:raise ValueError('Out-of-range archive log differs')
    actual_raw={p.relative_to(root).as_posix() for p in (root/'raw').rglob('*') if p.is_file()}
    if actual_raw!=set(expected_sources):raise ValueError('Unreceipted/missing raw metadata files')
    rebuilt=merge_records(rebuilt);records=json.loads((root/'filings_inventory.json').read_text())
    if rebuilt!=records:raise ValueError('Inventory does not reproduce from source pages and row evidence')
    # Direct accession/date/form checks supplement replay through the collector parser.
    pages={}
    for row in records:
        if row['review_status']!='inventory_only_not_admitted' or row['historical_security_link_status']!='pending':raise ValueError('Unexpected admission/security approval')
        for evidence in row['metadata_evidence']:
            name=evidence['metadata_path']
            if name not in pages:
                obj=json.loads(safe_path(root,name).read_text());pages[name]=obj['filings']['recent'] if evidence['source_scope']=='main_recent' else obj
            table=pages[name];i=evidence['row_index']
            for key,column in [('accession','accessionNumber'),('form','form'),('filing_date','filingDate')]:
                if table[column][i]!=row[key]:raise ValueError('Direct source-row mismatch')
    coverage=coverage_rows(records,companies,start,end)
    with (root/'coverage.csv').open(newline='',encoding='utf-8') as f:saved=list(csv.DictReader(f))
    if saved!=[{k:str(v) for k,v in row.items()} for row in coverage]:raise ValueError('Coverage table does not reproduce')
    counters={'company_count':len(companies),'original_10k_records':len(records),'missing_api_acceptance_values':sum(not r['accepted_at_api'] for r in records),
        'conflicting_api_timestamp_records':sum(bool(r['conflicting_api_timestamps']) for r in records),
        'missing_primary_document_records':sum(not r['primary_document'] for r in records),
        'zero_filing_calendar_year_cells':sum(r['original_10k_count']==0 for r in coverage),
        'multiple_filing_calendar_year_cells':sum(r['original_10k_count']>1 for r in coverage)}
    for key,value in counters.items():
        if manifest[key]!=value:raise ValueError('Manifest count differs: '+key)
    if counts!=manifest['completed_companies']:raise ValueError('Company progress counts differ')
    receipt={'status':'inventory_hashes_pagination_and_row_lineage_passed_not_timing_or_text_approval',
        'manifest_sha256':sha(root/'manifest.json'),'inventory_sha256':sha(root/'filings_inventory.json'),
        'audit_code_sha256':sha(__file__),'replay_code_sha256':sha(Path(__file__).with_name('history_inventory.py')),
        'collection_code_sha256_reported':manifest.get('code_sha256',{}),
        'reported_input_config_sha256':manifest['config_sha256'],'reported_input_universe_sha256':manifest['universe_sha256'],
        'config_snapshot_sha256':sha(root/'config_snapshot.json'),'universe_snapshot_sha256':sha(root/'universe_snapshot.json'),
        'reference_config_values_checked':reference_config is not None,'reference_universe_values_checked':reference_universe is not None,
        'source_files_checked':len(expected_sources),'main_pages':len(companies),'historical_pages':len(expected_sources)-len(companies),
        'skipped_archives_rechecked':len(expected_skips),'output_hashes_checked':len(manifest['outputs']),**counters,
        'company_counts':counts,'flagged_coverage':[r for r in coverage if r['original_10k_count']!=1],
        'main_recent_records':sum(any(e['source_scope']=='main_recent' for e in r['metadata_evidence']) for r in records),
        'historical_page_records':sum(any(e['source_scope']=='linked_historical_page' for e in r['metadata_evidence']) for r in records),
        'scope':'same-assistant offline replay plus direct source-row checks; no independent source authentication, availability or historical security approval'}
    return receipt,records


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',default='data/history/inventory_v1')
    p.add_argument('--reference-config',default='configs/history_inventory_v1.json');p.add_argument('--reference-universe',default='configs/universe.json')
    p.add_argument('--output',default='runs/history_inventory_audit_v1.json');a=p.parse_args()
    output=Path(a.output)
    if output.exists():raise FileExistsError('Preserve prior audit output')
    receipt,_=audit_inventory(a.inventory,a.reference_config,a.reference_universe)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
