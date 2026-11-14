"""Audit saved header bytes/records and compare API clocks under an ET assumption.

Clock agreement is a diagnostic, not approval of public availability or trading.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from secstab.history_audit import audit_inventory,safe_path
from secstab.history_headers import parse_header


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(headers,inventory):
    headers=Path(headers);inventory=Path(inventory)
    inventory_audit,records=audit_inventory(inventory)
    manifest=json.loads((headers/'manifest.json').read_text())
    if manifest['status']!='headers_collected_identity_matched_timing_review_pending':raise ValueError('Incomplete header collection')
    if manifest['inventory_manifest_sha256']!=inventory_audit['manifest_sha256'] or manifest['inventory_sha256']!=inventory_audit['inventory_sha256']:
        raise ValueError('Header and inventory lineage differ')
    if set(manifest['outputs'])!={'headers_inventory.json','inventory_audit.json'}:raise ValueError('Incomplete output receipts')
    for name,digest in manifest['outputs'].items():
        if sha(safe_path(headers,name))!=digest:raise ValueError('Header output hash mismatch: '+name)
    expected={f"headers/{r['cik']}/{r['accession']}.html":r for r in records}
    if set(expected)!=set(manifest['source_files']):raise ValueError('Header source identities differ')
    actual={p.relative_to(headers).as_posix() for p in (headers/'headers').rglob('*') if p.is_file()}
    if actual!=set(expected):raise ValueError('Missing or unreceipted header files')
    replayed=[];differences=[];block_counts={}
    for name,entry in manifest['source_files'].items():
        path=safe_path(headers,name);record=expected[name]
        if sha(path)!=entry['sha256'] or entry['url']!=record['filing_header_url']:raise ValueError('Header source hash/URL mismatch: '+name)
        parsed=parse_header(path.read_bytes(),record)
        replayed.append({**parsed,'header_path':name,'header_sha256':entry['sha256']})
        key=str(parsed['source_header_block_count']);block_counts[key]=block_counts.get(key,0)+1
        local=datetime.strptime(parsed['acceptance_clock_unzoned'],'%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('America/New_York'))
        raw_api=parsed.get('accepted_at_api')
        if raw_api is None:
            differences.append({'document_id':parsed['document_id'],'reason':'missing API value'});continue
        api=datetime.fromisoformat(raw_api.replace('Z','+00:00'))
        if api.tzinfo is None:raise ValueError('API value has no timezone; cannot silently interpret it')
        delta=(api-local).total_seconds()
        if delta:differences.append({'document_id':parsed['document_id'],'ticker':parsed['ticker'],'api_minus_header_ET_seconds':delta})
    saved=json.loads((headers/'headers_inventory.json').read_text())
    if replayed!=saved or len(saved)!=len(records) or manifest['header_count']!=len(records):raise ValueError('Parsed header records do not reproduce')
    return {'status':'header_hashes_identity_and_record_replay_passed_timing_approval_pending',
        'headers_manifest_sha256':sha(headers/'manifest.json'),'inventory_manifest_sha256':inventory_audit['manifest_sha256'],
        'inventory_sha256':inventory_audit['inventory_sha256'],'source_hashes_checked':len(expected),'output_hashes_checked':len(manifest['outputs']),
        'records_reproduced':len(saved),'block_counts':block_counts,
        'clock_comparison_policy':'Diagnostic only: interpret raw header clock as America/New_York; does not establish public dissemination, ingestion or execution time',
        'api_clock_matches_under_ET_interpretation':len(saved)-len(differences),'api_clock_differences':differences,
        'failure_history_entries':len(manifest.get('failures',[])),'resume_attempts':len(manifest.get('resume_attempts',[])),
        'expanded_sections_admitted':0,'expanded_embeddings_run':0,'approved_availability_records':0,
        'audit_code_sha256':sha(__file__),'parser_code_sha256':sha(Path(__file__).resolve().parents[1]/'src/secstab/history_headers.py')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--headers',default='data/history/headers_v1');p.add_argument('--inventory',default='data/history/inventory_v1')
    p.add_argument('--output',default='runs/history_headers_audit_v1.json');a=p.parse_args();output=Path(a.output)
    if output.exists():raise FileExistsError('Preserve existing audit output')
    result=audit(a.headers,a.inventory);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
