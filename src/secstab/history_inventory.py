"""Collect paginated SEC annual-filing metadata, without downloading/admitting text."""
import argparse
from datetime import date,datetime,timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import csv
from .cli import fetch_url


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def archive_overlaps(entry,cik,start,end):
    if not isinstance(entry,dict) or not re.fullmatch(r'CIK'+cik+r'-submissions-\d+\.json',str(entry.get('name',''))):
        raise ValueError('Unexpected archive name for requested CIK')
    lo,hi=entry.get('filingFrom'),entry.get('filingTo')
    if not lo or not hi:return True  # Unknown bounds: fetch rather than silently skip.
    if date.fromisoformat(lo)>date.fromisoformat(hi):raise ValueError('Reversed archive coverage')
    return lo<=end and hi>=start


def parse_page(table,company,sec_name,start,end,evidence):
    if not isinstance(table,dict):raise ValueError('Expected columnar filing metadata')
    required=['accessionNumber','filingDate','form']
    if any(not isinstance(table.get(k),list) for k in required):raise ValueError('Missing required columnar arrays')
    n=len(table['form'])
    for key in required:
        if len(table[key])!=n:raise ValueError('Misaligned required metadata column: '+key)
    for key in ['reportDate','primaryDocument','acceptanceDateTime']:
        if key in table and table[key] is not None and (not isinstance(table[key],list) or len(table[key]) not in [0,n]):
            raise ValueError('Misaligned optional metadata column: '+key)
    def value(key,i):return table[key][i] if isinstance(table.get(key),list) and len(table[key])==n else None
    records=[]
    cik=str(company['cik']).zfill(10)
    for i,form in enumerate(table['form']):
        if form!='10-K':continue
        filing_date=table['filingDate'][i]
        date.fromisoformat(filing_date)
        if not start<=filing_date<=end:continue
        accession=table['accessionNumber'][i]
        if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',str(accession)):raise ValueError('Malformed annual accession')
        filename=value('primaryDocument',i) or None
        if filename and (not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',filename) or filename in ['.','..']):
            raise ValueError('Unexpected primary-document filename')
        root=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}'
        accepted=value('acceptanceDateTime',i) or None
        if accepted is not None and not isinstance(accepted,str):raise ValueError('Unexpected acceptance timestamp type')
        report_date=value('reportDate',i) or None
        if report_date:date.fromisoformat(report_date)
        records.append({'ticker':company['ticker'],'cik':cik,'sector_pair_label':company.get('sector_pair'),
            'current_sec_name':sec_name,'document_id':accession,'accession':accession,'form':form,
            'filing_date':filing_date,'report_date':report_date,'primary_document':filename,
            'source_url':root+'/'+filename if filename else None,
            'filing_index_url':root+'/'+accession+'-index.html','filing_header_url':root+'/'+accession+'-index-headers.html',
            'accepted_at_api':accepted,'timestamp_status':'api_value_unverified_against_filing_header' if accepted else 'missing_pending_header_review',
            'review_status':'inventory_only_not_admitted','historical_security_link_status':'pending',
            'metadata_evidence':[{**evidence,'row_index':i}],'conflicting_api_timestamps':[]})
    return records


def merge_records(records):
    merged={}
    for source in records:
        row=dict(source);row['metadata_evidence']=list(source['metadata_evidence'])
        row['conflicting_api_timestamps']=list(source['conflicting_api_timestamps'])
        key=(row['cik'],row['accession'])
        if key not in merged:merged[key]=row;continue
        existing=merged[key]
        for field in ['form','filing_date','report_date','primary_document','source_url']:
            a,b=existing[field],row[field]
            if a and b and a!=b:raise ValueError('Conflicting duplicate accession field: '+field)
            if not a and b:existing[field]=b
        timestamps=set(existing['conflicting_api_timestamps']+row['conflicting_api_timestamps'])
        timestamps.update(x for x in [existing['accepted_at_api'],row['accepted_at_api']] if x)
        if len(timestamps)>1:
            existing['accepted_at_api']=None;existing['conflicting_api_timestamps']=sorted(timestamps)
            existing['timestamp_status']='conflict_pending_header_review'
        elif timestamps:
            existing['accepted_at_api']=next(iter(timestamps));existing['timestamp_status']='api_value_unverified_against_filing_header'
        existing['metadata_evidence'].extend(row['metadata_evidence'])
    return sorted(merged.values(),key=lambda r:(r['ticker'],r['filing_date'],r['accession']))


def coverage_rows(records,companies,start,end):
    output=[]
    for company in companies:
        cik=str(company['cik']).zfill(10)
        for year in range(int(start[:4]),int(end[:4])+1):
            rows=[r for r in records if r['cik']==cik and r['filing_date'].startswith(str(year))]
            output.append({'ticker':company['ticker'],'cik':cik,'filing_calendar_year':year,'original_10k_count':len(rows),
                'coverage_flag':'zero_original_review_needed' if not rows else ('multiple_originals_review_needed' if len(rows)>1 else 'one_original_observed'),
                'note':'Filing-calendar coverage only; not proof of a complete fiscal-year corpus or security history'})
    return output


def collect(args,fetcher=fetch_url):
    config=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    universe=json.loads(Path(config['universe_path']).read_text(encoding='utf-8-sig'))
    companies=universe['companies'];start=config['filing_start_inclusive'];end=config['filing_end_inclusive']
    if date.fromisoformat(start)>date.fromisoformat(end):raise ValueError('Reversed filing-date interval')
    if config['form']!='10-K':raise ValueError('This inventory supports original Form 10-K only')
    if len({str(c['cik']).zfill(10) for c in companies})!=len(companies) or not companies:raise ValueError('Need unique CIKs')
    for company in companies:
        if not re.fullmatch(r'\d{1,10}',str(company['cik'])) or not re.fullmatch(r'[A-Za-z0-9.-]+',company['ticker']):raise ValueError('Unsafe universe identity')
    output=Path(args.output)
    if output.exists():raise FileExistsError('Preserve existing inventory; choose another output directory')
    ua=os.environ.get('SEC_USER_AGENT','')
    if '@' not in ua or any(ord(c)<32 for c in ua):raise ValueError('Set SEC_USER_AGENT to your real name/organization and contact email')
    output.mkdir(parents=True,exist_ok=False);(output/'raw').mkdir()
    manifest={'status':'started','scope':config['scope'],'started_at':now(),'config_sha256':sha(args.config),
        'universe_sha256':sha(config['universe_path']),'python_version':platform.python_version(),
        'code_sha256':{'history_inventory.py':sha(__file__),'cli.py':sha(Path(__file__).with_name('cli.py'))},
        'filing_start_inclusive':start,'filing_end_inclusive':end,
        'source_files':{},'completed_companies':[],'skipped_archives':[],'outputs':{},
        'request_policy':'Sequential SEC requests via existing fetch_url, 0.25-second delay, declared User-Agent; fail on network/provider errors',
        'timestamp_policy':config['timestamp_policy'],'text_downloaded':False,'financial_evaluation_run':False}
    write(output/'manifest.json',manifest);write(output/'config_snapshot.json',config);write(output/'universe_snapshot.json',universe)
    all_records=[]
    def download(url,path):
        raw=fetcher(url,ua);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        relative=path.relative_to(output).as_posix();digest=sha(path)
        manifest['source_files'][relative]={'url':url,'sha256':digest,'downloaded_at':now()}
        write(output/'manifest.json',manifest)
        return json.loads(raw),{'metadata_path':relative,'metadata_sha256':digest,'metadata_url':url}
    try:
        for company in companies:
            cik=str(company['cik']).zfill(10);name=f'CIK{cik}.json'
            print('Inventory:',company['ticker'],flush=True)
            main,evidence=download('https://data.sec.gov/submissions/'+name,output/'raw'/cik/name)
            if str(main['cik']).zfill(10)!=cik:raise ValueError('SEC parent CIK identity mismatch')
            current=parse_page(main['filings']['recent'],company,main['name'],start,end,{**evidence,'source_scope':'main_recent'})
            files=main['filings'].get('files',[])
            if not isinstance(files,list):raise ValueError('Malformed historical archive list')
            seen=set()
            for entry in files:
                relevant=archive_overlaps(entry,cik,start,end)
                if entry['name'] in seen:raise ValueError('Duplicate historical archive link')
                seen.add(entry['name'])
                if not relevant:
                    manifest['skipped_archives'].append({'cik':cik,**entry,'reason':'advertised_date_range_outside_request'});continue
                page,proof=download('https://data.sec.gov/submissions/'+entry['name'],output/'raw'/cik/entry['name'])
                current.extend(parse_page(page,company,main['name'],start,end,{**proof,'source_scope':'linked_historical_page','parent_metadata_path':evidence['metadata_path'],'parent_metadata_sha256':evidence['metadata_sha256']}))
            current=merge_records(current);all_records=merge_records(all_records+current)
            write(output/'filings_inventory.json',all_records)
            manifest['completed_companies'].append({'ticker':company['ticker'],'cik':cik,'original_10k_count':len(current)})
            write(output/'manifest.json',manifest)
            print('  Original 10-K records:',len(current),flush=True)
        coverage=coverage_rows(all_records,companies,start,end)
        with (output/'coverage.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(coverage[0]));writer.writeheader();writer.writerows(coverage)
        manifest.update(status='metadata_collection_complete_pending_source_review',completed_at=now(),
            original_10k_records=len(all_records),company_count=len(companies),
            missing_api_acceptance_values=sum(not r['accepted_at_api'] for r in all_records),
            conflicting_api_timestamp_records=sum(bool(r['conflicting_api_timestamps']) for r in all_records),
            missing_primary_document_records=sum(not r['primary_document'] for r in all_records),
            zero_filing_calendar_year_cells=sum(r['original_10k_count']==0 for r in coverage),
            multiple_filing_calendar_year_cells=sum(r['original_10k_count']>1 for r in coverage))
        for name in ['filings_inventory.json','coverage.csv','config_snapshot.json','universe_snapshot.json']:manifest['outputs'][name]=sha(output/name)
        manifest['next_gate']='Audit archive coverage, issuer continuity and source timestamp headers before text download/admission and evaluation partitions'
        write(output/'manifest.json',manifest)
    except Exception as error:
        manifest.update(status='failed_partial_collection_preserved',failed_at=now(),error_type=type(error).__name__,error=str(error))
        write(output/'manifest.json',manifest);raise
    print(json.dumps({k:manifest[k] for k in ['status','company_count','original_10k_records','missing_api_acceptance_values','conflicting_api_timestamp_records','zero_filing_calendar_year_cells','multiple_filing_calendar_year_cells']},indent=2))
    print('Saved:',output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='configs/history_inventory_v1.json')
    p.add_argument('--output',default='data/history/inventory_v1');collect(p.parse_args())


if __name__=='__main__':main()
