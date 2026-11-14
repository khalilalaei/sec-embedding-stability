"""Preserve SEC filing-header evidence; extract identity/raw clocks, not eligibility."""
import argparse
from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
from .cli import fetch_url
from .history_inventory import sha,now
from .history_audit import audit_inventory,safe_path


def atomic_json(path,obj):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8');temporary.replace(path)


def parse_header(raw,record):
    text=html.unescape(raw.decode('utf-8-sig',errors='replace'))
    blocks=re.findall(r'<SEC-HEADER>.*?</SEC-HEADER>',text,re.S|re.I)
    if not blocks:raise ValueError('Response has no SEC-HEADER block: '+record['document_id'])
    parsed=[];formats=set()
    for block in blocks:
        def field(patterns,required=True):
            values={value for pattern in patterns for value in re.findall(pattern,block,re.I)}
            if not values and not required:return None
            if len(values)!=1:raise ValueError('Missing/ambiguous filing-header field: '+patterns[0])
            return next(iter(values))
        accession=field([r'ACCESSION NUMBER:\s*([0-9-]+)',r'<ACCESSION-NUMBER>\s*([0-9-]+)'])
        form=field([r'CONFORMED SUBMISSION TYPE:\s*([^\s<]+)',r'<TYPE>\s*([^\s<]+)'])
        clock=field([r'<ACCEPTANCE-DATETIME>\s*(\d{14})(?!\d)'])
        datetime.strptime(clock,'%Y%m%d%H%M%S')
        filed=field([r'FILED AS OF DATE:\s*(\d{8})(?!\d)',r'<FILING-DATE>\s*(\d{8})(?!\d)'])
        filed_date=datetime.strptime(filed,'%Y%m%d').date().isoformat()
        ciks={str(int(x)).zfill(10) for pattern in [r'CENTRAL INDEX KEY:\s*(\d+)',r'<CIK>\s*(\d+)'] for x in re.findall(pattern,block,re.I)}
        if accession!=record['accession'] or form!=record['form'] or str(record['cik']).zfill(10) not in ciks:
            raise ValueError('Header accession/form/CIK differs from inventory')
        if filed_date!=record['filing_date']:raise ValueError('Header filing date differs from inventory')
        period_raw=field([r'CONFORMED PERIOD OF REPORT:\s*(\d{8})(?!\d)',r'<PERIOD>\s*(\d{8})(?!\d)'],required=False)
        period=datetime.strptime(period_raw,'%Y%m%d').date().isoformat() if period_raw else None
        if record.get('report_date') and period!=record['report_date']:raise ValueError('Header report period differs from inventory')
        if re.search(r'<ACCESSION-NUMBER>',block,re.I):formats.add('tag_fields')
        if re.search(r'ACCESSION NUMBER:',block,re.I):formats.add('colon_fields')
        parsed.append({'accession':accession,'form':form,'clock':clock,'filed_date':filed_date,'period':period,'filer_ciks':sorted(ciks)})
    if any(value!=parsed[0] for value in parsed[1:]):
        raise ValueError('Conflicting SEC-HEADER copies; preserve response for review')
    matched=parsed[0]
    return {'document_id':matched['accession'],'ticker':record['ticker'],'cik':record['cik'],'form':matched['form'],'filing_date':matched['filed_date'],
        'report_date':matched['period'],'accepted_at_api':record.get('accepted_at_api'),'acceptance_clock_unzoned':matched['clock'],
        'source_header_block_count':len(blocks),'header_field_formats':sorted(formats),'header_copies_consistent':True,
        'source_url':record['filing_header_url'],'review_status':'header_identity_fields_matched_not_availability_approved',
        'timing_status':'raw_header_clock_preserved_pending_timezone_and_public_availability_review'}


def collect_headers(args,fetcher=fetch_url):
    output=Path(args.output);resume=getattr(args,'resume',False)
    if output.exists() and not resume:raise FileExistsError('Preserve header collection; use --resume for the same inputs')
    if resume and not (output/'manifest.json').is_file():raise ValueError('No header manifest to resume')
    ua=os.environ.get('SEC_USER_AGENT','')
    if '@' not in ua or any(ord(c)<32 for c in ua):raise ValueError('Set SEC_USER_AGENT to your real name/organization and contact email')
    audit,records=audit_inventory(args.inventory,getattr(args,'reference_config',None),getattr(args,'reference_universe',None))
    expected={f"headers/{r['cik']}/{r['accession']}.html":r for r in records}
    code={'history_headers.py':sha(__file__),'history_audit.py':sha(Path(__file__).with_name('history_audit.py')),'cli.py':sha(Path(__file__).with_name('cli.py'))}
    if resume:
        manifest=json.loads((output/'manifest.json').read_text())
        if manifest['inventory_manifest_sha256']!=audit['manifest_sha256'] or manifest['inventory_sha256']!=audit['inventory_sha256']:
            raise ValueError('Resume inventory differs; preserve collection and use a new output')
        for name,entry in manifest['source_files'].items():
            if name not in expected or entry['url']!=expected[name]['filing_header_url'] or sha(safe_path(output,name))!=entry['sha256']:
                raise ValueError('Recorded header bytes/identity changed; do not overwrite')
        for name,digest in manifest.get('outputs',{}).items():
            if sha(safe_path(output,name))!=digest:raise ValueError('Recorded header output changed; do not overwrite')
        if manifest['status']=='headers_collected_identity_matched_timing_review_pending':
            if len(manifest['source_files'])!=len(records) or manifest['header_count']!=len(records):raise ValueError('Completed header count differs')
            print(json.dumps({'status':manifest['status'],'header_count':manifest['header_count'],'already_complete':True},indent=2))
            print('Saved:',output);return
        manifest['resume_attempts'].append({'at':now(),'code_sha256':code})
    else:
        output.mkdir(parents=True,exist_ok=False)
        manifest={'status':'started','started_at':now(),'inventory_manifest_sha256':audit['manifest_sha256'],
            'inventory_sha256':audit['inventory_sha256'],'source_files':{},'outputs':{},'completed_records':0,
            'code_sha256':code,'resume_attempts':[],'failures':[],'scope':'header evidence collection only; no filing body/text admission or approved eligibility',
            'request_policy':'Sequential SEC requests with existing 0.25-second delay and contact User-Agent'}
        atomic_json(output/'inventory_audit.json',audit)
    manifest['status']='collecting_headers';atomic_json(output/'manifest.json',manifest)
    extracted=[]
    try:
        for number,(name,record) in enumerate(expected.items(),1):
            path=safe_path(output,name)
            if name not in manifest['source_files']:
                if path.exists():raise ValueError('Unreceipted header preserved; inspect it or use a new output directory')
                print(f"Header {number}/{len(records)}: {record['ticker']} {record['accession']}",flush=True)
                raw=fetcher(record['filing_header_url'],ua);path.parent.mkdir(parents=True,exist_ok=True)
                temporary=path.with_suffix('.html.part');temporary.write_bytes(raw);temporary.replace(path)
                manifest['source_files'][name]={'url':record['filing_header_url'],'sha256':sha(path),'downloaded_at':now()}
                atomic_json(output/'manifest.json',manifest)
            proof=parse_header(path.read_bytes(),record)
            extracted.append({**proof,'header_path':name,'header_sha256':manifest['source_files'][name]['sha256']})
            manifest['completed_records']=len(extracted)
            atomic_json(output/'manifest.json',manifest)
        atomic_json(output/'headers_inventory.json',extracted)
        manifest.update(status='headers_collected_identity_matched_timing_review_pending',completed_at=now(),header_count=len(extracted),
            next_gate='Audit source clocks/timezone/public availability and source-body identities before approving any historical eligibility or admitting text')
        manifest['outputs']={n:sha(output/n) for n in ['headers_inventory.json','inventory_audit.json']}
        atomic_json(output/'manifest.json',manifest)
    except Exception as error:
        manifest.setdefault('failures',[]).append({'at':now(),'error_type':type(error).__name__,'error':str(error)})
        manifest.update(status='failed_partial_headers_preserved',failed_at=now(),error_type=type(error).__name__,error=str(error))
        atomic_json(output/'manifest.json',manifest);raise
    print(json.dumps({'status':manifest['status'],'header_count':len(extracted),'approved_availability_records':0,'filing_bodies_downloaded':0},indent=2))
    print('Saved:',output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',default='data/history/inventory_v1')
    p.add_argument('--output',default='data/history/headers_v1');p.add_argument('--resume',action='store_true')
    p.add_argument('--reference-config',default='configs/history_inventory_v1.json');p.add_argument('--reference-universe',default='configs/universe.json')
    collect_headers(p.parse_args())


if __name__=='__main__':main()
