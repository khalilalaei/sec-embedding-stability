"""Resumable historical source download and conservative candidate extraction.

This stage never admits text, assigns execution eligibility or runs embeddings.
"""
import argparse
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
from .cli import fetch_url
from .extraction import extract,VERSION
from .history_inventory import sha,now
from .history_audit import audit_inventory,safe_path
from .history_headers import parse_header,atomic_json


def checked_sources(inventory,headers):
    proof,records=audit_inventory(inventory)
    headers=Path(headers);manifest=json.loads((headers/'manifest.json').read_text())
    if manifest['status']!='headers_collected_identity_matched_timing_review_pending':raise ValueError('Complete matched header evidence required')
    if manifest['inventory_manifest_sha256']!=proof['manifest_sha256'] or manifest['inventory_sha256']!=proof['inventory_sha256']:
        raise ValueError('Header/inventory lineage differs')
    expected={f"headers/{r['cik']}/{r['accession']}.html":r for r in records}
    if set(manifest['source_files'])!=set(expected):raise ValueError('Header set differs from inventory')
    for name,digest in manifest['outputs'].items():
        if sha(safe_path(headers,name))!=digest:raise ValueError('Header derived bytes changed')
    parsed=[]
    for name,entry in manifest['source_files'].items():
        path=safe_path(headers,name);record=expected[name]
        if entry['url']!=record['filing_header_url'] or sha(path)!=entry['sha256']:raise ValueError('Header bytes/URL changed')
        result=parse_header(path.read_bytes(),record)
        parsed.append({**result,'header_path':name,'header_sha256':entry['sha256']})
        # Cross-check the exact primary filename against the header document list.
        source=html.unescape(path.read_text(encoding='utf-8-sig',errors='replace'))
        filenames=[]
        for block in re.findall(r'<DOCUMENT>.*?</DOCUMENT>',source,re.S|re.I):
            types=re.findall(r'<TYPE>\s*([^\s<]+)',block,re.I)
            names=re.findall(r'<FILENAME>\s*([^\s<]+)',block,re.I)
            if types==['10-K']:filenames.extend(names)
        if record['primary_document'] not in filenames:raise ValueError('Primary filename absent from header 10-K document list: '+record['document_id'])
    if parsed!=json.loads((headers/'headers_inventory.json').read_text()):raise ValueError('Header parsed records differ')
    return proof,records,sha(headers/'manifest.json')


def run(args,fetcher=fetch_url):
    output=Path(args.output).resolve();resume=getattr(args,'resume',False)
    if output.exists() and not resume:raise FileExistsError('Preserve source/extraction batch; use --resume for same inputs')
    if resume and not (output/'manifest.json').is_file():raise ValueError('Missing batch manifest')
    # Check lxml before starting network work.
    importlib.metadata.version('lxml')
    proof,records,header_hash=checked_sources(args.inventory,args.headers)
    cache={};cache_path=Path(args.cache_corpus) if args.cache_corpus else None
    if cache_path and cache_path.is_file():
        entries=json.loads(cache_path.read_text(encoding='utf-8-sig'))
        if len({r['document_id'] for r in entries})!=len(entries):raise ValueError('Duplicate cache accessions')
        cache={r['document_id']:r for r in entries}
    cache_root=Path(args.cache_root) if args.cache_root else Path.cwd()
    ua=os.environ.get('SEC_USER_AGENT','')
    if not args.cache_only and ('@' not in ua or any(ord(c)<32 for c in ua)):raise ValueError('Set SEC_USER_AGENT before source downloads')
    if resume:
        manifest=json.loads((output/'manifest.json').read_text())
        if manifest['inventory_sha256']!=proof['inventory_sha256'] or manifest['headers_manifest_sha256']!=header_hash:
            raise ValueError('Resume inputs changed')
        for entry in manifest['sources'].values():
            if sha(safe_path(output,entry['path']))!=entry['sha256']:raise ValueError('Saved source changed')
        for entry in manifest['outcomes'].values():
            for key in ['text','source_map']:
                if key in entry and sha(safe_path(output,entry[key]['path']))!=entry[key]['sha256']:raise ValueError('Saved extraction evidence changed')
        manifest['attempts'].append({'at':now(),'extractor_version':VERSION,'code_sha256':sha(__file__)})
    else:
        output.mkdir(parents=True,exist_ok=False)
        manifest={'status':'started','started_at':now(),'inventory_sha256':proof['inventory_sha256'],
            'inventory_manifest_sha256':proof['manifest_sha256'],'headers_manifest_sha256':header_hash,
            'sources':{},'outcomes':{},'failures':[],'attempts':[],'extractor_version':VERSION,
            'code_sha256':{'history_corpus.py':sha(__file__),'extraction.py':sha(Path(__file__).with_name('extraction.py'))},
            'scope':'historical source bytes and conservative extraction candidates only; never automatic admission or approved eligibility'}
    manifest['status']='running';atomic_json(output/'manifest.json',manifest)
    processed=0
    try:
        for number,record in enumerate(records,1):
            doc=record['document_id'];key=record['cik']+'/'+doc
            if key in manifest['outcomes']:continue
            if args.limit is not None and processed>=args.limit:break
            cached=cache.get(doc)
            if key not in manifest['sources']:
                cache_file=None
                if cached:
                    if cached['cik']!=record['cik'] or cached['source_url']!=record['source_url']:raise ValueError('Cache identity/URL mismatch')
                    candidate=safe_path(cache_root,cached['raw_path'])
                    if candidate.is_file():
                        if sha(candidate)!=cached['raw_sha256']:raise ValueError('Cached source hash changed')
                        cache_file=candidate
                if args.cache_only and cache_file is None:continue
                path=safe_path(output,'raw/'+key+'/filing.html')
                if path.exists():raise ValueError('Unreceipted source preserved; inspect before continuing')
                path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.html.part')
                print(f"Source {number}/{len(records)}: {record['ticker']} {doc}",flush=True)
                if cache_file is not None:
                    shutil.copyfile(cache_file,temporary);origin='hash_verified_existing_pilot_source'
                else:
                    temporary.write_bytes(fetcher(record['source_url'],ua));origin='SEC_primary_document_download'
                temporary.replace(path)
                manifest['sources'][key]={'path':path.relative_to(output).as_posix(),'sha256':sha(path),'source_url':record['source_url'],'origin':origin,'saved_at':now()}
                atomic_json(output/'manifest.json',manifest)
            source=manifest['sources'][key];raw=safe_path(output,source['path']).read_bytes()
            try:
                text,mapping=extract(raw)
            except ValueError as error:
                manifest['outcomes'][key]={'document_id':doc,'ticker':record['ticker'],'status':'extraction_flagged_pending_review',
                    'reason':str(error),'source_sha256':source['sha256']}
            else:
                text_path=safe_path(output,'text/'+key+'/item1a.txt');text_path.parent.mkdir(parents=True,exist_ok=True)
                map_path=safe_path(output,'maps/'+key+'/source_map.json');map_path.parent.mkdir(parents=True,exist_ok=True)
                if text_path.exists() or map_path.exists():raise ValueError('Unreceipted extraction files preserved; inspect before continuing')
                text_path.write_text(text,encoding='utf-8',newline='\n')
                mapping.update(document_id=doc,ticker=record['ticker'],source_sha256=source['sha256'],text_sha256=sha(text_path))
                atomic_json(map_path,mapping)
                manifest['outcomes'][key]={'document_id':doc,'ticker':record['ticker'],'status':'extracted_pending_review',
                    'source_sha256':source['sha256'],'words':len(text.split()),'characters':len(text),
                    'text':{'path':text_path.relative_to(output).as_posix(),'sha256':sha(text_path)},
                    'source_map':{'path':map_path.relative_to(output).as_posix(),'sha256':sha(map_path)},
                    'review_scope':'conservative machine-selected candidate; not admitted or independently human audited'}
            processed+=1;atomic_json(output/'manifest.json',manifest)
        success=sum(x['status']=='extracted_pending_review' for x in manifest['outcomes'].values())
        flagged=sum(x['status']=='extraction_flagged_pending_review' for x in manifest['outcomes'].values())
        manifest.update(status='source_batch_finished_review_pending' if len(manifest['outcomes'])==len(records) else 'partial_checkpoint',
            last_checkpoint_at=now(),inventory_records=len(records),sources_saved=len(manifest['sources']),extracted_candidates=success,
            extraction_flags=flagged,not_yet_processed=len(records)-len(manifest['outcomes']),admitted_sections=0)
        atomic_json(output/'manifest.json',manifest)
    except Exception as error:
        manifest['failures'].append({'at':now(),'type':type(error).__name__,'error':str(error)})
        manifest['status']='failed_partial_evidence_preserved';atomic_json(output/'manifest.json',manifest);raise
    print(json.dumps({k:manifest[k] for k in ['status','inventory_records','sources_saved','extracted_candidates','extraction_flags','not_yet_processed','admitted_sections']},indent=2))
    print('Saved:',output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',default='data/history/inventory_v1')
    p.add_argument('--headers',default='data/history/headers_v1');p.add_argument('--output',default='data/history/corpus_v1')
    p.add_argument('--cache-corpus',default='data/corpus_extracted_v1.json');p.add_argument('--cache-root')
    p.add_argument('--cache-only',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.limit is not None and a.limit<1:p.error('--limit must be positive')
    run(a)


if __name__=='__main__':main()
